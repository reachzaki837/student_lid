from fastapi import APIRouter, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated, Optional
from urllib.parse import urlencode
import httpx

from app.services.auth import AuthService
from app.services.email import build_password_reset_preview_html
from app.models.user import UserRole
from app.core.security import create_access_token
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def get_redirect_uri(request: Request) -> str:
    """Build the callback URL based on the current host."""
    base = str(request.base_url).rstrip("/")
    return f"{base}/auth/google/callback"


# ──────────────────────────────────────────────
# Login / Register pages
# ──────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    error: Optional[str] = None,
    message: Optional[str] = None,
):
    return templates.TemplateResponse(request, "auth/login.html", {
        "error": error,
        "message": message,
    })


@router.post("/login")
async def login(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    remember_me: Annotated[Optional[str], Form()] = None,
):
    user = await AuthService.authenticate_user(email=email, password=password)

    if not user:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"error": "Invalid email or password"},
        )

    access_token = create_access_token(subject=user.email)
    max_age = 7 * 24 * 60 * 60 if remember_me == "on" else 1800
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=max_age,
        samesite="lax",
    )
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    google_name: Optional[str] = None,
    google_email: Optional[str] = None,
    google_id: Optional[str] = None,
    google_picture: Optional[str] = None,
):
    return templates.TemplateResponse(
        request,
        "auth/register.html",
        {
            "google_name": google_name or "",
            "google_email": google_email or "",
            "google_id": google_id or "",
            "google_picture": google_picture or "",
        },
    )


@router.post("/register")
async def register(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[Optional[str], Form()] = None,
    role: Annotated[UserRole, Form()] = UserRole.STUDENT,
    name: Annotated[str, Form()] = "",
    google_id: Annotated[Optional[str], Form()] = None,
    google_picture: Annotated[Optional[str], Form()] = None,
):
    ctx = {}

    # ── Google sign-up completion ──
    if google_id:
        user = await AuthService.create_google_user(
            email=email,
            name=name,
            role=role,
            google_id=google_id,
            picture=google_picture or "",
        )
        if not user:
            ctx["error"] = "Email already registered"
            ctx.update({"google_email": email, "google_name": name,
                        "google_id": google_id, "google_picture": google_picture})
            return templates.TemplateResponse(request, "auth/register.html", ctx)

        access_token = create_access_token(subject=user.email)
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            max_age=1800,
            samesite="lax",
        )
        return response

    # ── Normal sign-up ──
    if not password:
        ctx["error"] = "Password is required"
        return templates.TemplateResponse(request, "auth/register.html", ctx)

    user = await AuthService.create_user(
        email=email, password=password, role=role, name=name
    )
    if not user:
        ctx["error"] = "Email already registered"
        return templates.TemplateResponse(request, "auth/register.html", ctx)

    return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request, message: Optional[str] = None):
    return templates.TemplateResponse(
        request,
        "auth/forgot_password.html",
        {"message": message},
    )


@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password_submit(
    request: Request,
    email: Annotated[str, Form()],
):
    base = str(request.base_url).rstrip("/")

    await AuthService.request_password_reset(
        email=email,
        reset_link_builder=lambda token: f"{base}/auth/reset-password?token={token}",
    )

    return templates.TemplateResponse(
        request,
        "auth/forgot_password.html",
        {
            "message": "If an account exists for that email, a password reset link has been sent.",
        },
    )


@router.get("/dev/email-preview/reset-password", response_class=HTMLResponse)
async def preview_reset_password_email(
    request: Request,
    name: str = "Student",
    token: str = "preview-token-123",
):
    env = (settings.ENVIRONMENT or "").strip().lower()
    allowed_envs = {"development", "dev", "local", "test"}
    if env not in allowed_envs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    base = str(request.base_url).rstrip("/")
    reset_link = f"{base}/auth/reset-password?token={token}"
    html = build_password_reset_preview_html(name, reset_link)
    return HTMLResponse(content=html)


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: Optional[str] = None):
    if not token:
        return templates.TemplateResponse(
            request,
            "auth/reset_password.html",
            {
                "error": "Invalid or missing reset token. Please request a new link.",
                "token": "",
            },
        )

    user = await AuthService.validate_reset_token(token)
    if not user:
        return templates.TemplateResponse(
            request,
            "auth/reset_password.html",
            {
                "error": "This reset link is invalid or has expired. Please request a new one.",
                "token": "",
            },
        )

    return templates.TemplateResponse(
        request,
        "auth/reset_password.html",
        {"token": token},
    )


@router.post("/reset-password", response_class=HTMLResponse)
async def reset_password_submit(
    request: Request,
    token: Annotated[str, Form()],
    password: Annotated[str, Form()],
    confirm_password: Annotated[str, Form()],
):
    if password != confirm_password:
        return templates.TemplateResponse(
            request,
            "auth/reset_password.html",
            {
                "error": "Passwords do not match.",
                "token": token,
            },
        )

    if len(password) < 8:
        return templates.TemplateResponse(
            request,
            "auth/reset_password.html",
            {
                "error": "Password must be at least 8 characters long.",
                "token": token,
            },
        )

    success = await AuthService.reset_password_with_token(token=token, new_password=password)
    if not success:
        return templates.TemplateResponse(
            request,
            "auth/reset_password.html",
            {
                "error": "This reset link is invalid or has expired. Please request a new one.",
                "token": "",
            },
        )

    return RedirectResponse(
        url="/auth/login?message=Password+updated.+Please+sign+in.",
        status_code=status.HTTP_302_FOUND,
    )


# ──────────────────────────────────────────────
# Google OAuth — server-side redirect flow
# ──────────────────────────────────────────────

@router.get("/google")
async def google_login(request: Request):
    """Redirect the user to Google's OAuth consent screen."""
    redirect_uri = get_redirect_uri(request)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",   # always show account picker
    }
    google_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=google_url)


@router.get("/google/callback")
async def google_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    """Handle the redirect back from Google after the user selects their account."""

    if error or not code:
        return RedirectResponse(url="/auth/login?error=Google+sign-in+was+cancelled")

    redirect_uri = get_redirect_uri(request)

    # ── Step 1: Exchange the code for tokens ──
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

            if token_response.status_code != 200:
                return RedirectResponse(url="/auth/login?error=Failed+to+connect+with+Google")

            token_data = token_response.json()
            access_token_google = token_data.get("access_token")

            # ── Step 2: Get user info from Google ──
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token_google}"},
            )

            if userinfo_response.status_code != 200:
                return RedirectResponse(url="/auth/login?error=Failed+to+get+user+info+from+Google")

            info = userinfo_response.json()
    except httpx.HTTPError:
        return RedirectResponse(url="/auth/login?error=Google+authentication+service+unavailable")
    email = info.get("email", "")
    name = info.get("name", "")
    picture = info.get("picture", "")
    google_id = info.get("sub", "")

    if not email:
        return RedirectResponse(url="/auth/login?error=Google+did+not+provide+an+email")

    # ── Step 3: Check if user exists ──
    user = await AuthService.find_user_by_email(email)

    if user:
        # Existing user → log in directly
        app_token = create_access_token(subject=user.email)
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {app_token}",
            httponly=True,
            max_age=1800,
            samesite="lax",
        )
        return response
    else:
        # New user → send to registration with pre-filled info
        params = urlencode({
            "google_name": name,
            "google_email": email,
            "google_id": google_id,
            "google_picture": picture,
        })
        return RedirectResponse(
            url=f"/auth/register?{params}",
            status_code=status.HTTP_302_FOUND,
        )


# ──────────────────────────────────────────────
# Logout
# ──────────────────────────────────────────────

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login")
    response.delete_cookie("access_token")
    return response
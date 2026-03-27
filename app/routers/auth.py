from fastapi import APIRouter, Request, Form, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated, Optional
from urllib.parse import urlencode, urljoin
import requests as http_requests

from app.services.auth import AuthService
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
async def login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse(request, "auth/login.html", {
        "error": error,
    })


@router.post("/login")
async def login(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    user = await AuthService.authenticate_user(email=email, password=password)

    if not user:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"error": "Invalid email or password"},
        )

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
    token_response = http_requests.post(
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
    userinfo_response = http_requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token_google}"},
    )

    if userinfo_response.status_code != 200:
        return RedirectResponse(url="/auth/login?error=Failed+to+get+user+info+from+Google")

    info = userinfo_response.json()
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
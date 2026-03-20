from fastapi import APIRouter, Request, Form, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated

from app.services.auth import AuthService
from app.models.user import UserRole
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    email: Annotated[str, Form()], 
    password: Annotated[str, Form()]
):
    user = await AuthService.authenticate_user(email=email, password=password)
    
    if not user:
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Invalid email or password"
        })

    access_token = create_access_token(subject=user.email)

    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=1800,
        samesite="lax"
    )
    return response

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})

@router.post("/register")
async def register(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    role: Annotated[UserRole, Form()],
    name: Annotated[str, Form()]
):
    user = await AuthService.create_user(email=email, password=password, role=role, name=name)
    
    if not user:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": "Email already registered"
        })
    
    return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login")
    response.delete_cookie("access_token")
    return response
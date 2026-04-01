from app.models.user import User, UserRole
from app.core.config import settings
from app.core.security import verify_password, get_password_hash
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from typing import Optional


class AuthService:
    @staticmethod
    async def authenticate_user(email: str, password: str):
        user = await User.find_one(User.email == email)
        if not user:
            return None
        if user.auth_provider == "google" and not user.password:
            # Google-only user trying password login
            return None
        if not verify_password(password, user.password or ""):
            return None

        # Migrate legacy plaintext passwords to PBKDF2 on successful login.
        if user.password and not user.password.startswith("pbkdf2_sha256$"):
            user.password = get_password_hash(password)
            await user.save()

        return user

    @staticmethod
    async def create_user(email: str, password: str, role: UserRole, name: str) -> User:
        existing_user = await User.find_one(User.email == email)
        if existing_user:
            return None

        new_user = User(
            email=email,
            password=get_password_hash(password),
            role=role,
            name=name,
            auth_provider="local",
        )
        await new_user.insert()
        return new_user

    @staticmethod
    def verify_google_token(token: str) -> Optional[dict]:
        """Verify Google ID token and return user info dict or None."""
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
            # Token is valid – extract user info
            return {
                "email": idinfo.get("email"),
                "name": idinfo.get("name", ""),
                "picture": idinfo.get("picture", ""),
                "google_id": idinfo.get("sub"),
            }
        except ValueError:
            return None

    @staticmethod
    async def find_user_by_email(email: str) -> Optional[User]:
        return await User.find_one(User.email == email)

    @staticmethod
    async def create_google_user(
        email: str, name: str, role: UserRole, google_id: str, picture: str = ""
    ) -> User:
        """Create a new user who signed up via Google."""
        existing = await User.find_one(User.email == email)
        if existing:
            return None

        new_user = User(
            email=email,
            name=name,
            role=role,
            auth_provider="google",
            google_id=google_id,
            profile_picture=picture,
        )
        await new_user.insert()
        return new_user
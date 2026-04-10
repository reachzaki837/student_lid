from app.models.user import User, UserRole
from app.core.config import settings
from app.core.security import verify_password, get_password_hash
from app.services.email import send_password_reset_email
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from typing import Optional
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets


class AuthService:
    PASSWORD_RESET_TTL_MINUTES = 60

    @staticmethod
    def _hash_reset_token(token: str) -> str:
        return hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

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
    async def request_password_reset(email: str, reset_link_builder) -> None:
        """
        Request password reset for a local account.
        This method is intentionally silent for unknown emails to prevent user enumeration.
        """
        user = await User.find_one(User.email == email)
        if not user:
            return

        # Google-only accounts do not have local passwords to reset.
        if user.auth_provider == "google" and not user.password:
            return

        raw_token = secrets.token_urlsafe(32)
        user.password_reset_token_hash = AuthService._hash_reset_token(raw_token)
        user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=AuthService.PASSWORD_RESET_TTL_MINUTES
        )
        await user.save()

        reset_link = reset_link_builder(raw_token)
        await send_password_reset_email(
            recipient=user.email,
            reset_link=reset_link,
            recipient_name=user.name,
        )

    @staticmethod
    async def validate_reset_token(token: str) -> Optional[User]:
        if not token:
            return None

        token_hash = AuthService._hash_reset_token(token)
        user = await User.find_one(User.password_reset_token_hash == token_hash)
        if not user:
            return None

        now = datetime.now(timezone.utc)
        expires_at = user.password_reset_expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if not expires_at or expires_at < now:
            user.password_reset_token_hash = None
            user.password_reset_expires_at = None
            await user.save()
            return None

        return user

    @staticmethod
    async def reset_password_with_token(token: str, new_password: str) -> bool:
        user = await AuthService.validate_reset_token(token)
        if not user:
            return False

        user.password = get_password_hash(new_password)
        user.password_reset_token_hash = None
        user.password_reset_expires_at = None
        if not user.auth_provider:
            user.auth_provider = "local"
        await user.save()
        return True

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
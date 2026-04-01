from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Student Learning Style Identification System"
    SECRET_KEY: str = "BfeFGb4osPnvAbW-Ol_ORGQr1njHV2AR4s5lqRGXNKmfVFhr7jlbF2DTMCSUcEUDoXWnJz4YbFA-cXECCDyx9w"
    ENVIRONMENT: str = "development"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "learning_app_db"
    GROQ_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GMAIL_SENDER_EMAIL: Optional[str] = None
    GMAIL_APP_PASSWORD: Optional[str] = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("ALGORITHM", mode="before")
    @classmethod
    def normalize_algorithm(cls, value: str) -> str:
        # Keep app working when env value has common typos (e.g. H256 on Vercel).
        if not value:
            return "HS256"
        normalized = str(value).strip().upper()
        if normalized == "H256":
            return "HS256"

        allowed = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}
        return normalized if normalized in allowed else "HS256"

    def validate_runtime_secrets(self) -> None:
        env = (self.ENVIRONMENT or "").strip().lower()
        is_production_like = env in {"prod", "production", "staging"} or bool(
            os.getenv("VERCEL") or os.getenv("VERCEL_ENV")
        )
        insecure_default = self.SECRET_KEY == "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING"

        if is_production_like and (not self.SECRET_KEY or insecure_default):
            raise RuntimeError(
                "SECRET_KEY must be set to a secure non-default value in production-like environments."
            )

settings = Settings()
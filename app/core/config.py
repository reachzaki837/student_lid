from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Student Learning Style Identification System"
    SECRET_KEY: str = "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "learning_app_db"
    GROQ_API_KEY: Optional[str] = None
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

settings = Settings()
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Student Learning Style Identification System"
    SECRET_KEY: str = "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "learning_app_db"
    GROQ_API_KEY: Optional[str] = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
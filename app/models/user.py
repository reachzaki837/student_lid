from datetime import datetime, timezone
from beanie import Document, Indexed
from pydantic import Field, EmailStr
from enum import Enum
from typing import Optional

class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"

class User(Document):
    email: Indexed(EmailStr, unique=True)
    password: Optional[str] = None
    name: str = Field(default="")
    role: UserRole = UserRole.STUDENT
    auth_provider: str = Field(default="local")  # "local" or "google"
    google_id: Optional[str] = None
    profile_picture: Optional[str] = None
    theme_mode: str = Field(default="light")
    notifications_enabled: bool = Field(default=True)
    weekly_digest: bool = Field(default=True)
    focus_mode: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"

class Class(Document):
    name: str
    code: Indexed(str, unique=True)
    teacher_email: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "classes"

class Enrollment(Document):
    student_email: str
    class_code: str
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "enrollments"

class Assessment(Document):
    user_email: str
    vark_scores: dict
    hm_scores: dict
    dominant_style: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "assessments"

class Material(Document):
    uploader_email: str
    filename: str
    content_text: str = Field(default="")
    graph_knowledge: dict = Field(default_factory=dict) # To store extracted graph concepts/relationships
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "materials"
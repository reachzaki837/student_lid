from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, EmailStr
from enum import Enum

class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"

class User(Document):
    email: Indexed(EmailStr, unique=True)
    password: str
    name: str = Field(default="")
    role: UserRole = UserRole.STUDENT
    theme_mode: str = Field(default="light")
    notifications_enabled: bool = Field(default=True)
    weekly_digest: bool = Field(default=True)
    focus_mode: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"

class Class(Document):
    name: str
    code: Indexed(str, unique=True)
    teacher_email: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "classes"

class Enrollment(Document):
    student_email: str
    class_code: str
    joined_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "enrollments"

class Assessment(Document):
    user_email: str
    vark_scores: dict
    hm_scores: dict
    dominant_style: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "assessments"
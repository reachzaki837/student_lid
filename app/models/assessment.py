from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User

class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    vark_scores: Mapped[Dict[str, int]] = mapped_column(JSON) 
    hm_scores: Mapped[Dict[str, int]] = mapped_column(JSON)
    
    dominant_style: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="assessments")
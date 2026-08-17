from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class Interview(Base):
    __tablename__ = "interviews"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    company: Mapped[str] = mapped_column(String, default="")
    interview_type: Mapped[str] = mapped_column(String)
    difficulty: Mapped[str] = mapped_column(String)
    job_description: Mapped[str] = mapped_column(Text)
    profile_json: Mapped[str] = mapped_column(Text)
    answers_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

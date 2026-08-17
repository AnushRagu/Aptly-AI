from pydantic import BaseModel, Field
from typing import Literal, Optional, List

class CreateInterview(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    company: str = Field(default="", max_length=140)
    job_description: str = Field(min_length=20, max_length=15000)
    interview_type: Literal["HR", "Technical", "Behavioral", "Mixed"] = "Mixed"
    difficulty: Literal["Easy", "Medium", "Hard"] = "Medium"

class AnswerRequest(BaseModel):
    question: str = Field(min_length=2)
    question_type: str
    transcript: str = Field(min_length=1, max_length=10000)
    duration_seconds: float = Field(gt=0, le=1800)
    # Optional[...] keeps the app compatible with the Python 3.9 bundled on many Macs.
    eye_contact: Optional[float] = Field(default=None, ge=0, le=100)
    energy_points: List[float] = []

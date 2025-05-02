from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator
from typing import List, Optional
from datetime import date, datetime
import uuid


class Experience(BaseModel):
    job_title: str
    company: str
    start_date: date
    end_date: Optional[date] = None
    description: Optional[str] = None

    @validator('job_title', 'company')
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v


class Education(BaseModel):
    institution: str
    qualification: str
    field_of_study: str
    start_date: date
    end_date: Optional[date] = None

    @validator('institution', 'qualification', 'field_of_study')
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v


class JobSeekerCV(BaseModel):
    cv_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_uid: str  # FK to User.uid
    professional_title: str
    summary: Optional[str] = None
    skills: List[str]
    experience: List[Experience] = []
    education: List[Education] = []
    certifications: Optional[List[str]] = []
    languages: Optional[List[str]] = []
    website: Optional[HttpUrl] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('professional_title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Professional title cannot be empty")
        return v

    @validator('skills', 'experience', 'education', pre=True, each_item=False)
    def must_not_be_empty(cls, v):
        if not v:
            raise ValueError("This field must contain at least one item")
        return v

from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator
from typing import List, Optional, Union
from datetime import date, datetime
import uuid


# Experience
class Experience(BaseModel):
    job_title: str
    company: str
    start_date: date
    end_date: Optional[date] = None
    location: Optional[str] = None
    description: Optional[str] = None

    @validator('job_title', 'company')
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v


# Education
class Education(BaseModel):
    institution: str
    qualification: str
    field_of_study: str
    start_date: date
    end_date: Optional[date] = None
    description: Optional[str] = None

    @validator('institution', 'qualification', 'field_of_study')
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v


# Certification
class Certification(BaseModel):
    name: str
    issuer: str
    issue_date: date
    expiry_date: Optional[date] = None
    credential_url: Optional[HttpUrl] = None


# Language
class Language(BaseModel):
    name: str
    proficiency: str  # e.g., Beginner, Intermediate, Fluent, Native


# Publication (for academics)
class Publication(BaseModel):
    title: str
    publisher: Optional[str]
    date: Optional[date]
    link: Optional[HttpUrl]


# Project (for technical/creative fields)
class Project(BaseModel):
    title: str
    description: str
    technologies: Optional[List[str]] = []
    link: Optional[HttpUrl] = None


# Award or Honor
class Award(BaseModel):
    title: str
    issuer: Optional[str]
    date: Optional[date]
    description: Optional[str] = None


# Custom Section for extra content
class CustomSection(BaseModel):
    title: str
    content: Union[str, List[str]]  # Supports plain text or bullet lists

class SavedCV(BaseModel):
    id: str
    employer_uid: str
    cv_id: str
    saved_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True


class JobSeekerCV(BaseModel):
    cv_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_uid: str  # FK to User.uid
    professional_title: str
    summary: Optional[str] = None
    location: Optional[str] = None  # New field for location
    phone: Optional[str] = None  # New field for phone
    website: Optional[str] = None  # New field for website
    linkedin: Optional[str] = None  # New field for linkedin
    github: Optional[str] = None  # New field for github
    skills: List[str]
    experience: List[Experience] = []
    education: List[Education] = []
    certifications: Optional[List[Certification]] = []
    languages: Optional[List[Language]] = []
    projects: Optional[List[Project]] = []
    publications: Optional[List[Publication]] = []
    awards: Optional[List[Award]] = []
    custom_sections: Optional[List[CustomSection]] = []

    # Media and links
    portfolio_links: Optional[List[HttpUrl]] = []
    resume_file_url: Optional[HttpUrl] = None  # Link to uploaded original resume
    profile_image_url: Optional[HttpUrl] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('professional_title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Professional title cannot be empty")
        return v

    @validator('skills')
    def skills_must_have_values(cls, v):
        if not v or not all(s.strip() for s in v):
            raise ValueError("At least one valid skill must be provided")
        return v

    class Config:
        # Allow the model to use `datetime` fields as ISO format strings when serialized
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()  # Ensure the datetime fields are serialized in ISO format
        }
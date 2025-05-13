from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Optional, List
from datetime import datetime


class JobSeekerProfile(BaseModel):
    user_uid: str  # FK to User.uid

    first_name: str
    last_name: str
    # Basic info
    bio: Optional[str] = None
    profile_image_url: Optional[HttpUrl] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[HttpUrl] = None
    linkedin: Optional[HttpUrl] = None
    github: Optional[HttpUrl] = None

    # Job preferences
    job_titles_of_interest: Optional[List[str]] = []
    industries_of_interest: Optional[List[str]] = []
    locations_of_interest: Optional[List[str]] = []
    remote_preference: Optional[bool] = False
    availability: Optional[str] = None  # e.g. "Immediate", "30-day notice"

    # Freelance readiness
    is_freelancer: bool = Field(default=False, description="Indicates if user is open to freelance work")
    freelance_skills: Optional[List[str]] = Field(default_factory=list)
    hourly_rate: Optional[float] = Field(default=None, description="Preferred hourly rate for freelance work")
    freelance_experience: Optional[str] = Field(default=None, description="Short summary of freelance experience")
    freelance_availability: Optional[str] = Field(default=None, description="e.g., '10 hrs/week', 'Evenings only'")

    # Settings
    visibility: bool = Field(default=True, description="Visible to employers and clients")
    profile_completion: Optional[int] = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    # --- Validators ---
    @field_validator("job_titles_of_interest", "industries_of_interest", "locations_of_interest", "freelance_skills", mode="before")
    def remove_empty_items(cls, v):
        if isinstance(v, list):
            return [item.strip() for item in v if item.strip()]
        return v

    @field_validator("availability", "freelance_availability")
    def availability_must_not_be_blank(cls, v):
        if v and not v.strip():
            raise ValueError("Availability cannot be blank")
        return v

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        },
        "from_attributes": True  # allows ORM models to be parsed directly
    }

import json
import re
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, HttpUrl, EmailStr


def format_reference(ref: str) -> str:
    """Sample reference formatter - implement your logic"""
    return ref.upper().replace(" ", "-")


class CompanyVerificationStatus(Enum):
    """
    Represents the stages and outcomes of company verification,
    which may involve document checks and CIPC registration.
    """
    NOT_VERIFIED = "not_verified"
    PENDING = "pending"
    DOCUMENTS_UPLOADED = "documents_uploaded"
    DOCUMENTS_REJECTED = "documents_rejected"
    DOCUMENTS_APPROVED = "documents_approved"
    CIPC_PENDING = "cipc_pending"
    CIPC_VERIFIED = "cipc_verified"
    CIPC_FAILED = "cipc_failed"
    VERIFIED = "verified"


class Company(BaseModel):
    """Pydantic model for company data with job statistics"""
    company_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    industry: Optional[str] = Field(default=None, max_length=255)
    website: Optional[HttpUrl] = Field(default=None)
    logo_url: Optional[HttpUrl] = Field(default=None)

    # Location
    city: Optional[str] = Field(default=None, max_length=255)
    province: Optional[str] = Field(default=None, max_length=255)
    country: Optional[str] = Field(default=None, max_length=255)

    # Contact Info
    contact_email: Optional[EmailStr] = Field(default=None)
    phone_number: Optional[str] = Field(default=None, max_length=20)

    # Company Details
    employee_count: Optional[int] = Field(default=None, ge=1)
    founded_year: Optional[int] = Field(default=None, ge=1800, le=datetime.now().year)
    tech_stack: Optional[list[str]] = Field(default=None)

    # Social Media
    linkedin_url: Optional[HttpUrl] = Field(default=None)
    twitter_handle: Optional[str] = Field(default=None, max_length=15)

    # Relationships
    jobs: Optional[list['Job']] = Field(default_factory=list)  # Forward reference
    is_verified: Optional[bool] = Field(default=False)
    time_verification_request_sent: Optional[datetime] = Field(default=None)
    verification_status: str = Field(default=CompanyVerificationStatus.PENDING.value)

    @field_validator('tech_stack', mode='before')
    @classmethod
    def parse_tech_stack(cls, v):
        """Handle different formats of tech_stack input"""
        if v is None:
            return None

        if isinstance(v, list):
            return v

        if isinstance(v, str):
            # Try to parse JSON string
            if v.startswith('[') and v.endswith(']'):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Handle comma-separated values
            return [tech.strip() for tech in v.split(',') if tech.strip()]

        return v

    # Computed job statistics properties
    @property
    def total_jobs(self) -> int:
        """Total jobs posted by this company"""
        return len(self.jobs) if self.jobs else 0

    @property
    def active_jobs(self) -> int:
        """Active jobs (not expired)"""
        if not self.jobs:
            return 0
        now = datetime.utcnow()
        return sum(1 for job in self.jobs
                   if job.status == 'active' and job.expires_at > now)

    @property
    def featured_jobs(self) -> int:
        """Featured jobs"""
        return sum(1 for job in self.jobs if job.is_featured) if self.jobs else 0

    @property
    def total_applications(self) -> int:
        """Total applications across all jobs"""
        if not self.jobs:
            return 0
        return sum(job.application_count for job in self.jobs)

    @property
    def avg_applications_per_job(self) -> float:
        """Average applications per job"""
        return self.total_applications / self.total_jobs if self.total_jobs > 0 else 0

    @property
    def application_response_rate(self) -> float:
        """Percentage of applications with employer response"""
        if not self.jobs or self.total_applications == 0:
            return 0

        responded = 0
        for job in self.jobs:
            if job.applications:
                responded += sum(1 for app in job.applications
                                 if app.employer_response is not None)
        return (responded / self.total_applications) * 100

    @property
    def avg_hiring_time(self) -> float:
        """Average days to fill positions"""
        if not self.jobs:
            return 0

        total_days = 0
        filled_positions = 0

        for job in self.jobs:
            if job.status == 'closed' and job.applications:
                # Find the hired application
                hired_app = next((app for app in job.applications
                                  if app.status == 'hired'), None)
                if hired_app:
                    total_days += (hired_app.applied_at - job.posted_at).days
                    filled_positions += 1

        return total_days / filled_positions if filled_positions > 0 else 0

    @property
    def popular_job_titles(self) -> list[str]:
        """Most common job titles"""
        if not self.jobs:
            return []

        title_count = {}
        for job in self.jobs:
            title_count[job.title] = title_count.get(job.title, 0) + 1

        return sorted(title_count, key=title_count.get, reverse=True)[:3]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    @field_validator("phone_number")
    def validate_phone_number(cls, v):
        if v and not re.match(r"^\+?[\d\s\-()]{7,20}$", v):
            raise ValueError("Invalid phone number format")
        return v

    @field_validator("twitter_handle")
    def validate_twitter_handle(cls, v):
        if v and not re.match(r"^@?(\w){1,15}$", v):
            raise ValueError("Invalid Twitter handle")
        return v

    @property
    def is_valid(self) -> bool:
        """
        Checks whether the company has enough meaningful data to be considered valid.
        :return: True if valid, False otherwise.
        """
        # Validate company name
        if not self.name or len(self.name.strip()) < 2:
            return False

        # At least one form of online/contact presence
        has_contact_info = any([
            self.contact_email,
            self.phone_number,
            self.website,
            self.linkedin_url,
            self.twitter_handle
        ])

        # At least partial location details
        has_location_info = any([
            self.city,
            self.province,
            self.country
        ])

        # Descriptive data
        has_descriptive_info = any([
            self.description,
            self.industry
        ])

        return has_contact_info and has_location_info and has_descriptive_info


class CompanyVerificationDocument(BaseModel):
    document_type: str  # You can use Enum here for safety
    file_url: HttpUrl
    status: Optional[str] = "pending"
    uploaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

class CompanyCIPC(BaseModel):
    company_name: str
    registration_number: str
    registration_date: Optional[datetime]
    registered_address: Optional[str]
    company_type: Optional[str]  # e.g., "Private Company", "Non-Profit"
    director_names: Optional[list[str]] = []
    status: Optional[str] = "pending"  # pending, verified, failed
    verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

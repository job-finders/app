import uuid
from datetime import datetime, date, timezone
from typing import Optional, List

from pydantic import BaseModel, Field, computed_field, field_validator


def format_reference(ref: str) -> str:
    """Sample reference formatter - implement your logic"""
    return ref.upper().replace(" ", "-")


from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Optional, List
from datetime import datetime
import uuid

class Company(BaseModel):
    """Pydantic model for company data"""
    company_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None

    # Location
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None

    # Contact Info
    contact_email: Optional[str] = None
    phone_number: Optional[str] = None

    # Company Details
    employee_count: Optional[int] = None
    founded_year: Optional[int] = None
    tech_stack: Optional[List[str]] = None

    # Social Media
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None

    # Relationships
    jobs: Optional[List['Job']] = None  # Forward reference

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


# Update forward references for Pydantic model
Company.update_forward_refs()


class Job(BaseModel):
    # Core Identification
    job_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    job_ref: str = Field(default_factory=lambda: str(uuid.uuid4()))
    external_source: Optional[str] = None

    # Company Relationships
    company_id: Optional[str] = None
    company_name: Optional[str] = Field(None, min_length=2, max_length=255)

    # Job Details
    title: str = Field(min_length=5, max_length=255)
    description: str
    position_type: str = Field(pattern="FULL_TIME|PART_TIME|CONTRACT")
    remote_policy: str = Field(pattern="ONSITE|HYBRID|REMOTE")
    category: Optional[str] = Field(default=None)

    # Compensation
    salary_min: Optional[float] = Field(ge=0, default=None)
    salary_max: Optional[float] = Field(ge=0, default=None)
    salary_currency: str = Field(default="ZAR", min_length=3, max_length=3)
    salary_confidential: Optional[bool] = False

    # Location
    city: str = Field(min_length=2, max_length=100)
    province: str = Field(min_length=2, max_length=100)
    country: str = Field(min_length=2, max_length=100)
    geo_location: Optional[str] = None

    # Timeline
    posted_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    application_deadline: Optional[datetime] = None

    # Requirements
    experience_level: str = Field(pattern="ENTRY|MID|SENIOR")
    education_requirements: Optional[dict] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)

    required_documents: list[str] = Field(default_factory=list)
    required_questionnaire: list[str] = Field()

    # Application Process
    application_url: Optional[str] = None
    application_instructions: str = Field(min_length=10)

    # Statistics
    view_count: int = Field(ge=0, default=0)
    application_count: int = Field(ge=0, default=0)

    # Status
    status: str = Field(default="active", pattern="pending|active|closed|archived")
    is_featured: Optional[bool] = False

    # Audit
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # --- Computed Fields ---
    @computed_field
    @property
    def is_active(self) -> bool:
        return self.status == "active" and self.expires_at > datetime.utcnow()

    @computed_field
    @property
    def location(self) -> str:
        return f"{self.city}, {self.province}, {self.country}"

    @computed_field
    @property
    def slug(self) -> str:
        return f"{self.title.lower().replace(' ', '-')}-{self.job_ref}"

    @field_validator("job_ref")
    def format_job_ref(cls, value: str) -> str:
        # Replace with your actual format_reference logic
        return value.replace(" ", "").upper()

    @field_validator("salary_max")
    def validate_salary_range(cls, v, values):
        min_salary = values.data.get("salary_min")
        if v is not None and min_salary is not None and v < min_salary:
            raise ValueError("salary_max must be greater than salary_min")
        return v

    @property
    def ats_description(self) -> str:
        skill_text = f"Desired skills include: {', '.join(self.preferred_skills)}." if self.preferred_skills else ""
        summary_parts = [
            f"Job Title: {self.title}",
            f"Company: {self.company_name or ''}",
            f"Location: {self.location}",
            f"Position Type: {self.position_type}",
            f"Salary: {self.salary_currency} {self.salary_min} - {self.salary_max}",
            skill_text,
            f"Job Description: {self.description or ''}"
        ]
        return "\n".join([part for part in summary_parts if part.strip()])

    class Config:
        orm_mode = True


class SavedJob(BaseModel):
    saved_job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class JobApplication(BaseModel):
    application_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    job: Optional[Job] = Field(None)  # Relationship to Job model
    cv_id: Optional[str] = None

    applied_date: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)  # Changed from date to datetime

    cover_letter: Optional[str] = None
    status: str = Field(default='pending')
    method: Optional[str] = Field(default='website')
    notes: Optional[str] = None

    expected_salary: Optional[int] = None
    preferred_start_date: Optional[date] = None
    preferred_location: Optional[str] = None

    required_documents: list[str] = Field(default_factory=list)
    questionnaire_answers: dict[str, list[str]] = Field(default={})
    application_stage: str = Field(default="submitted")
    validation_score: int = Field(default=0)
    missing_requirements: list[str] = Field(default_factory=list)
    review_summary: Optional[str] = Field(default=None)

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }

class ATSReport(BaseModel):
    ats_report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = Field(..., description="ID of the job the report is associated with")
    cv_id: str = Field(..., description="ID of the CV used in the evaluation")
    score: float = Field(..., ge=0, le=100, description="ATS score out of 100")
    matched_keywords: list[str] = Field(default_factory=list, description="List of matched keywords found in CV")
    missing_keywords: list[str] = Field(default_factory=list, description="List of important keywords not found in CV")
    feedback: str = Field(..., description="Feedback based on the ATS evaluation")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the report was generated")



# Pydantic Models
class StatusCounts(BaseModel):
    active: int = Field(..., description="Jobs marked as 'active' in system")
    closed: int = Field(..., description="Jobs manually closed by employers")
    archived: int = Field(..., description="Archived historical jobs")
    current_active: int = Field(..., description="Active and not expired jobs")

class ApplicationMetrics(BaseModel):
    total_applications: int = Field(..., description="Sum of all applications across jobs")
    jobs_with_applications: int = Field(..., description="Number of jobs that have ≥1 application")

class JobStatistics(BaseModel):
    total_jobs: int = Field(..., description="Total jobs in system")
    status_counts: StatusCounts
    application_metrics: ApplicationMetrics
    categories: dict[str, int] = Field(..., description="Job count per category")
    recent_jobs_30d: int = Field(..., description="Jobs posted in last 30 days")
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "total_jobs": 2541,
                "status_counts": {
                    "active": 1200,
                    "closed": 1000,
                    "archived": 341,
                    "current_active": 800
                },
                "application_metrics": {
                    "total_applications": 15423,
                    "jobs_with_applications": 845
                },
                "categories": {
                    "IT & Tech": 650,
                    "Finance": 320,
                    "Healthcare": 280
                },
                "recent_jobs_30d": 342,
                "calculated_at": "2023-07-20T14:30:45+02:00"
            }
        }


from pydantic import BaseModel, Field


class ApplicationFunnelStats(BaseModel):
    """
    Represents metrics related to a job's application funnel, from view to hiring.
    Includes stage counts and conversion efficiency.
    """

    views: int = Field(
        ...,
        description="Total number of times the job listing was viewed by users."
    )
    started: int = Field(
        ...,
        description="Number of applicants who started the application process (i.e., submitted applications)."
    )
    completed: int = Field(
        ...,
        description="Number of applicants who completed the application process. "
                    "For now, assumed to be equal to 'started'."
    )
    qualified: int = Field(
        ...,
        description="Number of applications marked as qualified by the employer or screening system."
    )
    interviewed: int = Field(
        ...,
        description="Number of applicants who reached the interview stage."
    )
    hired: int = Field(
        ...,
        description="Number of applicants who were ultimately hired for the job."
    )
    rejected: int = Field(
        ...,
        description="Number of applicants who were rejected at any stage of the funnel."
    )
    conversion_rate: float = Field(
        ...,
        description="Percentage of submitted applicants who were hired. "
                    "Calculated as (hired / started) * 100."
    )

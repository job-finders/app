import uuid
from datetime import date, timezone, timedelta, datetime
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field, field_validator, computed_field, ConfigDict

from src.database.constants import utc_time
from src.database.models.company_models import Company


def format_reference(ref: str) -> str:
    """Sample reference formatter - implement your logic"""
    return ref.upper().replace(" ", "-")

class JobApprovalStatusEnum(Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    FLAGGED = "Flagged"


class JobApprovalRequest(BaseModel):
    """
    Pydantic model for job approval request data representation.

    Includes utility methods for checking status, token expiry,
    and interpreting approval decisions.
    """
    request_id: str
    job_id: str
    token: str
    token_expires: Optional[datetime]
    requested_at: Optional[datetime]
    requested_by: str
    approvers: list[str]
    status: str = Field(default=JobApprovalStatusEnum.PENDING.value)  # Values: pending, approved, rejected, expired
    decision_at: Optional[datetime] = None
    decision_by: Optional[str] = None
    feedback: Optional[str] = None

    # ----------- Helper Methods -----------

    def is_token_valid(self) -> bool:
        """Check if the approval token is still valid."""
        return bool(self.token_expires and self.token_expires > utc_time())

    def is_approved(self) -> bool:
        """Return True if the job has been approved."""
        return self.status == "approved"

    def is_pending(self) -> bool:
        """Return True if the request is still pending."""
        return self.status == "pending"

    def is_rejected(self) -> bool:
        """Return True if the job has been explicitly rejected."""
        return self.status == "rejected"

    def has_expired(self) -> bool:
        """Return True if the token is expired and not yet approved/rejected."""
        return self.status == "pending" and not self.is_token_valid()

    def decision_summary(self) -> str:
        """Provide a human-readable summary of the decision."""
        if self.is_approved():
            return "Job approved"
        elif self.is_rejected():
            return f"Rejected: {self.feedback or 'No reason given'}"
        elif self.has_expired():
            return "Approval request expired"
        else:
            return "Awaiting approval"
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class JobVersionHistory(BaseModel):
    id: str
    job_id: str
    version: int
    changes: dict[str,Any]  # JSON diff between versions
    modified_by: str
    modified_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

class JobStatusEnum(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PENDING_APPROVAL = "pending"
    ARCHIVED = "archived"
    CLOSED = "closed"

def generate_job_ref() -> str:
    ts = utc_time().strftime('%Y%m%d%H%M%S')  # e.g., 20250529143000
    rand = uuid.uuid4().hex[:6].upper()              # e.g., B6FA9C
    return f"JB-{ts}-{rand}"                         # e.g., JB-20250529143000-B6FA9C

class Job(BaseModel):
    # Core Identification
    job_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    # This new job reference is only used when job reference is not passed during creation of class so the old reference will still work
    job_ref: str = Field(default_factory=generate_job_ref)

    slug: Optional[str] = Field(default=None)
    external_source: Optional[str] = Field(default=None)

    # Company Relationships
    employer_id: Optional[str] = Field(default=None, description="The Employee Rep for Company who made the Job Posting")
    company_id: Optional[str] = Field(default=None)
    company: Optional[Company] = Field(default=None)
    approval_request: Optional[JobApprovalRequest] = Field(default=None)
    version_history: Optional[JobVersionHistory] = Field(default=None)

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
    posted_at: datetime = Field(default_factory=lambda: utc_time())
    expires_at: datetime
    application_deadline: Optional[datetime] = Field(default=None)

    # Requirements
    experience_level: str = Field(pattern="ENTRY|MID|SENIOR")
    education_requirements: Optional[dict] = Field(default=None)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    required_questionnaire: list[str]

    # Application Process
    application_url: Optional[str] = Field(default=None)
    application_instructions: str = Field(min_length=10)

    # Statistics
    view_count: int = Field(ge=0, default=0)
    application_count: int = Field(ge=0, default=0)

    # Status
    status: str = Field(default=JobStatusEnum.DRAFT.value, pattern="draft|pending|active|closed|archived")
    is_featured: Optional[bool] = False

    # Audit
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    # Computed Properties
    @computed_field
    @property
    def is_active(self) -> bool:
        return self.status == "active" and self.expires_at > utc_time()

    @computed_field
    @property
    def location(self) -> str:
        return f"{self.city}, {self.province}, {self.country}"

    @computed_field
    @property
    def posted_by(self) -> str:
        return self.company.name if self.company else "Unknown"

    @property
    def ats_description(self) -> str:
        # Format required skills
        required_skills_text = (
            f"Required skills: {', '.join(self.required_skills)}." if self.required_skills else ""
        )
        # Format preferred skills
        preferred_skills_text = (
            f"Preferred skills: {', '.join(self.preferred_skills)}." if self.preferred_skills else ""
        )
        # Format education requirements
        education_text = ""
        if self.education_requirements:
            edu_list = [f"{k}: {v}" for k, v in self.education_requirements.items()]
            education_text = "Education Requirements: " + "; ".join(edu_list) + "."

        # Compose the full ATS-friendly description
        summary_parts = [
            f"Job Title: {self.title}",
            f"Company: {self.company.name if self.company else ''}",
            f"Location: {self.location}",
            f"Position Type: {self.position_type}",
            f"Remote Policy: {self.remote_policy}",
            f"Experience Level: {self.experience_level}",
            f"Salary: {self.salary_currency} {self.salary_min} - {self.salary_max}" if self.salary_min and self.salary_max else "",
            required_skills_text,
            preferred_skills_text,
            education_text,
            f"Job Description: {self.description or ''}"
        ]
        return "\n".join(part for part in summary_parts if part.strip())

    @classmethod
    def create_from_enhanced_agent_output(
            cls,
            agent_output: 'EnhanceJobPostOutput',
            employer_id: str,
            company_id: str,
            **kwargs
    ) -> 'Job':
        """
        Creates a Job instance from the EnhanceJobPostAgent output

        Args:
            agent_output: Output from the enhancement agent
            employer_id: ID of the employer creating the job
            company_id: ID of the company posting the job
            kwargs: Additional job attributes not provided by the agent

        Returns:
            Job instance ready for database insertion
        """
        # Convert ISO strings to datetime objects
        expires_at = datetime.fromisoformat(agent_output.expires_at) if agent_output.expires_at else None
        application_deadline = datetime.fromisoformat(
            agent_output.application_deadline) if agent_output.application_deadline else None

        # Set default expiration if not provided
        if not expires_at:
            expires_at = utc_time() + timedelta(days=60)

        # Create job data dictionary
        job_data = {
            'job_ref': agent_output.job_ref,
            'title': agent_output.title,
            'description': agent_output.description,
            'position_type': agent_output.position_type,
            'remote_policy': agent_output.remote_policy,
            'category': agent_output.category,
            'salary_min': agent_output.salary_min,
            'salary_max': agent_output.salary_max,
            'salary_currency': agent_output.salary_currency,
            'salary_confidential': agent_output.salary_confidential,
            'city': agent_output.city,
            'province': agent_output.province,
            'country': agent_output.country,
            'geo_location': agent_output.geo_location,
            'expires_at': expires_at,
            'application_deadline': application_deadline,
            'experience_level': agent_output.experience_level,
            'education_requirements': agent_output.education_requirements,
            'required_skills': agent_output.required_skills,
            'preferred_skills': agent_output.preferred_skills,
            'required_documents': agent_output.required_documents,
            'required_questionnaire': agent_output.required_questionnaire,
            'application_url': agent_output.application_url,
            'application_instructions': agent_output.application_instructions,
            'status': agent_output.status,
            'is_featured': agent_output.is_featured,
            'employer_id': employer_id,
            'company_id': company_id,
            'posted_at': utc_time(),
            'created_at': utc_time(),
            'updated_at': utc_time()
        }

        # Add any additional fields passed via kwargs
        job_data.update(kwargs)

        return cls(**job_data)

    # Validators
    @field_validator("job_ref")
    @classmethod
    def format_job_ref(cls, value: str) -> str:
        return value.replace(" ", "").upper()

    @field_validator("salary_max")
    @classmethod
    def validate_salary_range(cls, v: Optional[float], info) -> Optional[float]:
        min_salary = info.data.get("salary_min")
        if v is not None and min_salary is not None and v < min_salary:
            raise ValueError("salary_max must be greater than salary_min")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class SavedJob(BaseModel):
    saved_job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    created_at: datetime = Field(default_factory=lambda: utc_time())

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }



class JobApplicationStatusEnum(Enum):
    """
        statuses for job application life cycles
    """
    APPLIED = "Applied"
    UNDER_REVIEW = "Under Review"
    INTERVIEWING = "Interviewing"
    SHORTLISTED = "Shortlisted"
    OFFER_EXTENDED = "Offer Extended"
    HIRED = "Hired"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"

class JobApplication(BaseModel):
    application_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    job: Optional[Job] = Field(None)  # Relationship to Job model
    cv_id: Optional[str] = None

    applied_date: datetime = Field(default_factory=lambda : utc_time())
    updated_at: Optional[datetime] = Field(default=None)  # Changed from date to datetime

    cover_letter: Optional[str] = None
    method: Optional[str] = Field(default='website')
    notes: Optional[str] = None

    expected_salary: Optional[int] = None
    preferred_start_date: Optional[date] = None
    preferred_location: Optional[str] = None

    required_documents: list[str] = Field(default_factory=list)
    questionnaire_answers: dict[str, list[str]] = Field(default={})
    last_application_stage : str| None = Field(default=None)
    application_stage: str = Field(default=JobApplicationStatusEnum.APPLIED.value)
    validation_score: int = Field(default=0)
    missing_requirements: list[str] = Field(default_factory=list)
    review_summary: Optional[str] = Field(default=None)

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }

class ATSReport(BaseModel):
    ats_report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = Field(..., description="ID of the job the report is associated with")
    cv_id: str = Field(..., description="ID of the CV used in the evaluation")
    score: float = Field(..., ge=0, le=100, description="ATS score out of 100")
    matched_keywords: list[str] = Field(default_factory=list, description="list of matched keywords found in CV")
    missing_keywords: list[str] = Field(default_factory=list, description="list of important keywords not found in CV")
    feedback: str = Field(..., description="Feedback based on the ATS evaluation")
    created_at: datetime = Field(default_factory=lambda: utc_time(), description="Timestamp when the report was generated")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


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
    calculated_at: datetime = Field(default_factory=lambda: utc_time())

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


# Update forward references for Pydantic model
Company.model_rebuild()



class JobApplicationDashboard(BaseModel):
    """"""
    total_applications: int
    applications_by_status: dict[str, int]
    recent_applications: list[dict]
    average_application_score: float
    skills_heatmap: dict[str, int]
    pipeline_metrics: dict[str, float]


class TalentPoolReport(BaseModel):

    skills_gap_analysis: dict[str, int]
    diversity_metrics: dict[str, float]
    source_effectiveness: dict[str, float]
    average_time_to_hire: float
    candidate_comparison: list[dict]


class BulkImportResult(BaseModel):
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    total_processed: int
    successful: int
    failures: int
    error_details: list[dict]



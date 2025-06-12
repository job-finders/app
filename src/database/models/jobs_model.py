import re
import uuid
from collections import Counter
from datetime import date, timedelta
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field, computed_field, ConfigDict, model_validator, AwareDatetime
from textstat.backend.metrics import flesch_reading_ease

from src.agents.employer import EnhanceJobPostOutput
from src.database.constants import utc_time
from src.database.models.company_models import Company

from src.database.models.employer_models import Employer
# NOTE : DO NOT REMOVE EMPLOYER IMPORT
# from textstat import flesch_reading_ease

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
    token_expires: Optional[AwareDatetime]
    requested_at: Optional[AwareDatetime]
    requested_by: str
    approvers: list[str]
    status: str = Field(default=JobApprovalStatusEnum.PENDING.value)  # Values: pending, approved, rejected, expired
    decision_at: Optional[AwareDatetime] = None
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

    model_config = ConfigDict(from_attributes=True)


class JobVersionHistory(BaseModel):
    id: str
    job_id: str
    version: int
    changes: dict[str,Any]  # JSON diff between versions
    modified_by: str
    modified_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)

class JobStatusEnum(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PENDING_APPROVAL = "pending"
    NEEDS_ATTENTION = "needs_attention"
    ARCHIVED = "archived"
    CLOSED = "closed"

def generate_job_ref() -> str:
    ts = utc_time().strftime('%Y%m%d%H%M%S')  # e.g., 20250529143000
    rand = uuid.uuid4().hex[:6].upper()              # e.g., B6FA9C
    return f"JB-{ts}-{rand}"                         # e.g., JB-20250529143000-B6FA9C


class JobCategory(BaseModel):
    category_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=2, max_length=100)
    slug: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    seo_description: Optional[str] = Field(max_length=250, default=None)
    created_at: AwareDatetime = Field(default_factory=lambda: utc_time())
    updated_at: Optional[AwareDatetime] = Field(default=None)

    # Relationship
    jobs: list['Job'] = Field(default_factory=list)

    # Computed statistics properties
    @computed_field
    @property
    def total_jobs(self) -> int:
        """Total jobs in this category"""
        return len(self.jobs)

    @computed_field
    @property
    def active_jobs(self) -> int:
        """Active jobs (not expired)"""
        now = utc_time()
        return sum(
            1 for job in self.jobs
            if job.status == 'active' and job.expires_at > now
        )

    @computed_field
    @property
    def featured_jobs(self) -> int:
        """Featured jobs in this category"""
        return sum(1 for job in self.jobs if job.is_featured)

    @computed_field
    @property
    def avg_salary_min(self) -> Optional[float]:
        """Average minimum salary"""
        min_salaries = [job.salary_min for job in self.jobs if job.salary_min is not None]
        return sum(min_salaries) / len(min_salaries) if min_salaries else None

    @computed_field
    @property
    def avg_salary_max(self) -> Optional[float]:
        """Average maximum salary"""
        max_salaries = [job.salary_max for job in self.jobs if job.salary_max is not None]
        return sum(max_salaries) / len(max_salaries) if max_salaries else None

    @model_validator(mode='after')
    def generate_slug(self) -> 'JobCategory':
        """Generate slug if not provided"""
        if not self.slug and self.name:
            self.slug = self.name.lower().replace(" ", "-")
        return self

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


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

    category_id: Optional[str] = Field(default=None)
    category: Optional[JobCategory] = Field(default=None)  # Updated to JobCategory
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
    posted_at: AwareDatetime = Field(default_factory=lambda: utc_time())
    expires_at: Optional[AwareDatetime] = Field(default=None)
    application_deadline: Optional[AwareDatetime] = Field(default=None)

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
    created_at: Optional[AwareDatetime] = Field(default=None)
    updated_at: Optional[AwareDatetime] = Field(default=None)

    summary: Optional[str] = Field(default=None, description="Short summary for job listing")
    seo_description: Optional[str] = Field(default=None, description="SEO description for job post")

    applications: list['JobApplication'] = Field(default_factory=list)
    saved_jobs: list['SavedJob'] = Field(default_factory=list)
    ats_reports: list['ATSReport'] = Field(default_factory=list, description="List of ATS reports for this job")


    @computed_field(return_type=int)
    @property
    def reviewed_applications_count(self) -> int:
        """
            Will Count the number of applications which have been reviewed already
        :return:
        """
        reviewed_statuses = [JobApplicationStatusEnum.REJECTED.value, JobApplicationStatusEnum.HIRED.value,
        JobApplicationStatusEnum.OFFER_EXTENDED.value, JobApplicationStatusEnum.WITHDRAWN.value]
        return sum(1 for app in self.applications if app.application_stage in reviewed_statuses)

    @computed_field(return_type=int)
    @property
    def in_progress_applications(self) -> int:
        """
            will count the number of applications which are in progress
        :return:
        """
        in_progress_statuses = [JobApplicationStatusEnum.UNDER_REVIEW.value,JobApplicationStatusEnum.INTERVIEWING.value,
                                JobApplicationStatusEnum.SHORTLISTED.value]
        return sum(1 for app in self.applications if app.application_stage in in_progress_statuses)



    @computed_field(return_type=Optional[int])
    @property
    def job_ats_score(self) -> Optional[int]:
        """
        Computes the average ATS match score for this job from all ATS Reports.
        Returns None if there are no reports.
        :return:
        """
        if not self.ats_reports or not self.ats_reports[0].score:
            return None
        total_score = sum(report.score for report in self.ats_reports)
        avg_score = total_score / len(self.ats_reports)
        return int(round(avg_score, 2))

    @computed_field
    @property
    def job_ats_match_rate(self) -> Optional[float]:
        """
        Percentage of ATS reports scoring above 60 (good matches).
        """
        if not self.ats_reports:
            return None

        matches = [r for r in self.ats_reports if r.score >= 60]
        return round((len(matches) / len(self.ats_reports)) * 100, 1)

    @computed_field
    @property
    def job_common_missing_keywords(self) -> list[str]:
        """
        Returns the top 5 most frequently missing keywords across all ATS reports.
        """
        if not self.ats_reports:
            return []

        keyword_counter = Counter()
        for report in self.ats_reports:
            keyword_counter.update(report.missing_keywords)

        most_common = keyword_counter.most_common(5)
        return [kw for kw, _ in most_common]

    @computed_field
    @property
    def job_most_matched_keywords(self) -> list[str]:
        from collections import Counter

        counter = Counter()
        for report in self.ats_reports:
            counter.update(report.matched_keywords)
        return [kw for kw, _ in counter.most_common(5)]

    @computed_field
    @property
    def job_ats_feedback_snippets(self) -> list[str]:
        """
        Returns first 3 snippets of textual feedback from ATS reports.
        """
        return [report.feedback for report in self.ats_reports[:3]]

    @computed_field
    @property
    def job_ats_score_distribution(self) -> dict:
        """
        Bucket ATS scores into ranges like:
        {"0-20": 1, "21-40": 2, "41-60": 5, "61-80": 3, "81-100": 4}
        """
        from collections import defaultdict

        buckets = defaultdict(int)
        for report in self.ats_reports:
            score = report.score
            if score <= 20:
                buckets["0-20"] += 1
            elif score <= 40:
                buckets["21-40"] += 1
            elif score <= 60:
                buckets["41-60"] += 1
            elif score <= 80:
                buckets["61-80"] += 1
            else:
                buckets["81-100"] += 1
        return dict(buckets)

    @computed_field(return_type=bool)
    @property
    def readability_is_ok(self) -> bool:
        """Determines if the readability score of the job is acceptable.
        Uses Flesch Reading Ease score - returns True if score >= 60 (standard readability)
        """
        completeness_threshold = 6
        if self.job_completeness_score < completeness_threshold:
            return False
        # noinspection PyBroadException
        try:
            score = flesch_reading_ease(self.ats_description)
            return score >= 60  # 60+ is considered standard readability
        except Exception as e:
            print(str(e))
            return False

    @computed_field(return_type=int)
    @property
    def job_completeness_score(self) -> int:
        """Calculate job completeness on a score of 1 to 10"""
        score = 0

        # Essential fields (4 points total)
        if self.title and len(self.title.strip()) >= 5: score += 1
        if self.description and len(self.description.strip()) >= 50: score += 1
        if self.application_instructions and len(self.application_instructions.strip()) >= 10: score += 1
        if self.city and self.province and self.country: score += 1

        # Important fields (3 points total)
        if self.required_skills: score += 1
        if self.experience_level: score += 1
        if self.salary_min or self.salary_max: score += 1

        # Nice-to-have fields (3 points total)
        if self.preferred_skills: score += 1
        if self.education_requirements: score += 1
        if self.summary: score += 1

        return min(score, 10)

    @computed_field(return_type=int)
    @property
    def external_link_count(self) -> int:
        """
        Count number of external links in job description.
        Acceptable max = 1. More than 1 may be spammy.
        """
        if not self.description:
            return 0

        # Extract all anchor hrefs
        hrefs = re.findall(r'<a\s+(?:[^>]*?\s+)?href=["\'](.*?)["\']', self.description, flags=re.IGNORECASE)

        # Filter for external links (http/https and not internal/mailto)
        # noinspection HttpUrlsUsage
        external_links = [
            url for url in hrefs
            if url.startswith("http://") or url.startswith("https://")
        ]

        return len(external_links)

    @computed_field(return_type=int)
    @property
    def job_quality_score(self) -> int:
        """
        Calculate overall job quality score (0-100)
        Based on completeness, readability, quality signals, and spam penalty.
        """

        # Base score from completeness (0-70 points)
        completeness_score = (self.job_completeness_score / 10) * 70

        # Readability bonus (0-15 points)
        readability_score = 15 if self.readability_is_ok else 0

        # Quality indicators bonus (up to 15 points)
        quality_bonus = 0
        if self.description and len(self.description.split()) > 100:
            quality_bonus += 3
        if self.company:
            quality_bonus += 3
        if self.salary_min and self.salary_max:
            quality_bonus += 3
        if len(self.required_skills) >= 3:
            quality_bonus += 3
        if self.application_url or "email" in self.application_instructions.lower():
            quality_bonus += 3

        # --- SPAM PENALTY ---
        spam_score = self.spam_severity_score if hasattr(self, "spam_severity_score") else 0
        spam_penalty = spam_score * 3  # Max 30 points off

        total_score = completeness_score + readability_score + quality_bonus - spam_penalty

        return int(round(max(min(total_score, 100), 0), 1))

    @computed_field(return_type=int)
    @property
    def spam_severity_score(self) -> int:
        spam_keywords = [
            "work from home",
            "quick money",
            "no experience needed",
            "earn fast",
            "make money online",
            "click here",
            "limited time offer",
            "guaranteed income",
            "get rich quick",
        ]

        # Combine into single searchable string
        content = " ".join(self.job_keyword_listing)

        # Count number of matches
        spam_count = sum(content.count(keyword) for keyword in spam_keywords)

        # Convert spam_count to severity score (scaled max at 10)
        return min(int(spam_count * 1.5), 10)

    @computed_field(return_type=bool)
    @property
    def is_spammy_job(self) -> bool:
        """
        Returns True if the spam severity score is 6 or higher.
        This is based on the number and repetition of known spam keywords.
        """

        return self.spam_severity_score >= 6

    @computed_field(return_type=list[str])
    @property
    def job_keyword_listing(self) -> list[str]:
        """
        Returns a list of keywords (including duplicates) from important job fields.
        Includes required_skills, preferred_skills, and words from the description.
        """
        keywords = []
        # Add required and preferred skills
        if self.required_skills:
            keywords.extend(self.required_skills)
        if self.preferred_skills:
            keywords.extend(self.preferred_skills)
        # Add words from description (split on non-word chars)
        if self.description:
            keywords.extend(re.findall(r"\w+", self.description.lower()))
        if self.title:
            keywords.extend(re.findall(r"\w+", self.title.lower()))
        return keywords

    @computed_field(return_type=str)
    @property
    def salary(self) -> str:
        """Returns a formatted salary range string."""
        if self.salary_min is not None and self.salary_max is not None:
            return f"{self.salary_currency} {self.salary_min} - {self.salary_max}"
        elif self.salary_min is not None:
            return f"{self.salary_currency} {self.salary_min} and above"
        elif self.salary_max is not None:
            return f"{self.salary_currency} up to {self.salary_max}"
        else:
            return "Salary not specified"

    @computed_field(return_type=int)
    @property
    def total_applications(self) -> int:
        return len(self.applications)

    # Computed Properties
    @computed_field(return_type=bool)
    @property
    def is_active(self) -> bool:
        return self.status == JobStatusEnum.ACTIVE.value and self.expires_at > utc_time()

    @computed_field(return_type=str)
    @property
    def location(self) -> str:
        return f"{self.city}, {self.province}, {self.country}"

    @computed_field(return_type=str)
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
        # Convert ISO strings to AwareDatetime objects
        expires_at = datetime.fromisoformat(agent_output.expires_at) if agent_output.expires_at else None
        application_deadline = AwareDatetime.fromisoformat(
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
            'updated_at': utc_time(),
            'applications': [],
            'saved_hobs': [],


        }

        # Add any additional fields passed via kwargs
        job_data.update(kwargs)

        return cls(**job_data)

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class SavedJob(BaseModel):
    """
        Candidates will follow specific jobs using this Model.
    """
    saved_job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    created_at: AwareDatetime = Field(default_factory=lambda: utc_time())

    model_config = ConfigDict(from_attributes=True)


class ATSReport(BaseModel):
    ats_report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = Field(..., description="ID of the job the report is associated with")
    cv_id: str = Field(..., description="ID of the CV used in the evaluation")
    score: float = Field(..., ge=0, le=100, description="ATS score out of 100")
    matched_keywords: list[str] = Field(default_factory=list, description="list of matched keywords found in CV")
    missing_keywords: list[str] = Field(default_factory=list, description="list of important keywords not found in CV")
    feedback: str = Field(..., description="Feedback based on the ATS evaluation")
    created_at: AwareDatetime = Field(default_factory=lambda: utc_time(),
                                      description="Timestamp when the report was generated")
    job_application: Optional['JobApplication'] = Field(default=None, description="Job Applications related to this ATS Report if Any")
    job: Optional[Job] = Field(default=None, description="Job related to this ATS Report if Any")

    model_config = ConfigDict(from_attributes=True)


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
    ats_report_id: Optional[str]
    job: Optional[Job] = Field(None)  # Relationship to JobModel
    cv_id: Optional[str] = None

    applied_date: AwareDatetime = Field(default_factory=utc_time)
    updated_at: Optional[AwareDatetime] = Field(default=None)  # Changed from date to AwareDatetime

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
    ats_report: Optional[ATSReport] = Field(default=None)

    def is_recent_application(self):
        recent_cut_off_date = utc_time() - timedelta(days=7)
        return self.applied_date > recent_cut_off_date

    model_config = ConfigDict(from_attributes=True)

        

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
    calculated_at: AwareDatetime = Field(default_factory=lambda: utc_time())

    model_config = ConfigDict(from_attributes=True)

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



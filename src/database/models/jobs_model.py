import json
import re
import uuid
from collections import Counter
from datetime import date, timedelta, datetime, timezone
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field, computed_field, ConfigDict, model_validator, AwareDatetime, HttpUrl
from textstat.backend.metrics import flesch_reading_ease

from src.agents.employer import EnhanceJobPostOutput
from src.database.constants import utc_time
from src.database.models.company_models import Company
from src.database.models.jobseeker_profile import JobSeekerProfile
from src.utils import tokenize


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

    @classmethod
    def members_list(cls) -> list[str]:
        """
        Returns a list of all enum member values.
        """
        return [member.value for member in cls]


def generate_job_ref() -> str:
    ts = utc_time().strftime('%Y%m%d%H%M%S')  # e.g., 20250529143000
    rand = uuid.uuid4().hex[:6].upper()              # e.g., B6FA9C
    return f"JB-{ts}-{rand}"                         # e.g., JB-20250529143000-B6FA9C


class JobLike(BaseModel):
    """Pydantic model for job likes"""
    like_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., min_length=1, description="JobSeeker profile user_uid")
    job_id: str = Field(..., min_length=1, description="Job ID being liked")
    created_at: AwareDatetime = Field(default_factory=utc_time)

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    @property
    def is_recent(self) -> bool:
        """Check if this like was created within the last 24 hours"""
        return (utc_time() - self.created_at).total_seconds() < 86400  # 24 hours in seconds


class ShareMethodEnum(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    WHATSAPP = "whatsapp"
    COPY_LINK = "copy_link"


class JobShare(BaseModel):
    """Pydantic model for job shares"""
    share_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = Field(None, description="JobSeeker profile user_uid (optional for anonymous sharing)")
    job_id: str = Field(..., min_length=1, description="Job ID being shared")
    share_method: ShareMethodEnum = Field(..., description="Method used to share the job")
    shared_at: AwareDatetime = Field(default_factory=utc_time)
    referral_code: Optional[str] = Field(None, max_length=20, description="Tracking code for referrals")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    @property
    def is_anonymous(self) -> bool:
        """Check if this is an anonymous share (no user_id)"""
        return self.user_id is None

    @property
    def is_social_media(self) -> bool:
        """Check if this share was via social media"""
        social_methods = {ShareMethodEnum.LINKEDIN, ShareMethodEnum.TWITTER, ShareMethodEnum.FACEBOOK}
        return self.share_method in social_methods

    @classmethod
    def generate_referral_code(cls, user_id: str, job_id: str) -> str:
        """Generate a unique referral code for tracking"""
        import hashlib
        combined = f"{user_id}:{job_id}:{utc_time().timestamp()}"
        return hashlib.md5(combined.encode()).hexdigest()[:8].upper()


class JobActionsState(BaseModel):
    """Pydantic model for job actions UI state"""
    job_id: str = Field(..., min_length=1, description="Job ID")
    user_has_liked: bool = Field(default=False, description="Whether current user has liked this job")
    user_has_saved: bool = Field(default=False, description="Whether current user has saved this job")
    like_count: int = Field(default=0, ge=0, description="Total number of likes for this job")
    share_count: int = Field(default=0, ge=0, description="Total number of shares for this job")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    @property
    def has_engagement(self) -> bool:
        """Check if the job has any user engagement (likes or shares)"""
        return self.like_count > 0 or self.share_count > 0

    @property
    def engagement_score(self) -> float:
        """Calculate a simple engagement score (likes weighted more than shares)"""
        return (self.like_count * 2) + self.share_count

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "job_id": self.job_id,
            "user_has_liked": self.user_has_liked,
            "user_has_saved": self.user_has_saved,
            "like_count": self.like_count,
            "share_count": self.share_count,
            "has_engagement": self.has_engagement,
            "engagement_score": self.engagement_score
        }


class JobActionRequest(BaseModel):
    """Base model for job action requests"""
    job_id: str = Field(..., min_length=1, description="Job ID")
    user_id: str = Field(..., min_length=1, description="JobSeeker profile user_uid")

    model_config = ConfigDict(str_strip_whitespace=True)


class JobLikeRequest(JobActionRequest):
    """Model for job like/unlike requests"""
    pass


class JobSaveRequest(JobActionRequest):
    """Model for job save/unsave requests"""
    pass


class JobShareRequest(BaseModel):
    """Model for job share requests"""
    job_id: str = Field(..., min_length=1, description="Job ID")
    user_id: Optional[str] = Field(None, description="JobSeeker profile user_uid (optional for anonymous sharing)")
    share_method: ShareMethodEnum = Field(..., description="Method used to share the job")

    model_config = ConfigDict(str_strip_whitespace=True)

    def create_job_share(self) -> JobShare:
        """Create a JobShare instance from this request"""
        referral_code = None
        if self.user_id:
            referral_code = JobShare.generate_referral_code(self.user_id, self.job_id)

        return JobShare(
            user_id=self.user_id,
            job_id=self.job_id,
            share_method=self.share_method,
            referral_code=referral_code
        )


class JobActionsResponse(BaseModel):
    """Standard response model for job actions"""
    success: bool = Field(..., description="Whether the action was successful")
    message: str = Field(..., description="Response message")
    data: Optional[dict] = Field(None, description="Additional response data")

    model_config = ConfigDict(from_attributes=True)


class JobCategory(BaseModel):
    category_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=2, max_length=100)
    slug: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    seo_description: Optional[str] = Field(max_length=250, default=None)
    created_at: AwareDatetime = Field(default_factory=lambda: utc_time())
    updated_at: Optional[AwareDatetime] = Field(default=None)

    # NEW: lightweight taxonomy fields
    canonical_skills: list[str] = Field(default_factory=list)  # ["Python", "Django", "PostgreSQL"]
    skill_synonyms: dict[str, list[str]] = Field(default_factory=dict)  # {"Python": ["py", "python3"]}
    
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
    title: str = Field(min_length=2, max_length=255)
    description: str
    position_type: str = Field(pattern="FULL_TIME|PART_TIME|CONTRACT")
    remote_policy: str = Field(pattern="ONSITE|HYBRID|REMOTE")

    category_id: Optional[str] = Field(default=None)
    category: Optional[JobCategory] = Field(default=None)  # Updated to JobCategory
    # Compensation
    salary_min: Optional[float] = Field(ge=0, default=None)
    salary_max: Optional[float] = Field(ge=0, default=None)
    salary_currency: str = Field(default="ZAR", min_length=3, max_length=3)
    salary_confidential: Optional[bool] = Field(default=False)

    # Location
    city: str = Field(min_length=2, max_length=100)
    province: str = Field(min_length=2, max_length=100)
    country: str = Field(min_length=2, max_length=100)
    geo_location: Optional[str] = Field(default=None)

    # Timeline
    posted_at: AwareDatetime = Field(default_factory=lambda: utc_time())
    expires_at: Optional[AwareDatetime] = Field(default=None)
    application_deadline: Optional[AwareDatetime] = Field(default=None)

    # Requirements
    experience_level: str = Field(default="ENTRY", pattern="ENTRY|MID|SENIOR")
    education_requirements: Optional[dict] = Field(default_factory=dict)
    required_skills: Optional[list[str]] = Field(default_factory=list)
    preferred_skills: Optional[list[str]] = Field(default_factory=list)
    required_documents: Optional[list[str]] = Field(default_factory=list)
    required_questionnaire: Optional[list[str]] = Field(default_factory=list)

    # Application Process
    application_url: Optional[str] = Field(default=None)
    application_instructions: Optional[str] = Field(min_length=10)

    # Statistics
    view_count: int = Field(ge=0, default=0)
    application_count: int = Field(ge=0, default=0)

    # Status
    status: str = Field(default=JobStatusEnum.DRAFT.value, pattern="draft|pending|active|closed|archived")
    is_featured: Optional[bool] = Field(default=False)

    # Audit
    created_at: Optional[AwareDatetime] = Field(default=None)
    updated_at: Optional[AwareDatetime] = Field(default=None)

    summary: Optional[str] = Field(default=None, description="Short summary for job listing")
    seo_description: Optional[str] = Field(default=None, description="SEO description for job post")

    applications: list['JobApplication'] = Field(default_factory=list)

    # NOTE: this points to jobseekers interested in this job - through the savedJobs Class
    interested_jobseekers: list['SavedJob'] = Field(default_factory=list)

    ats_reports: list['ATSReport'] = Field(default_factory=list, description="list of ATS reports for this job")

    # Job actions relationships
    likes: list['JobLike'] = Field(default_factory=list, description="list of job likes")
    shares: list['JobShare'] = Field(default_factory=list, description="list of job shares")

    @model_validator(mode="before")
    @classmethod
    def _coerce_raw_form(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Convert the raw form / JSON payload into correct Python types.
        Any un-parseable value becomes None so Pydantic will use the
        field's default instead of raising.
        """
        if not isinstance(data, dict):
            return data

        out = dict(data)

        # 1. dates ---------------------------------------------------------
        for dt_key in ("expires_at", "application_deadline"):
            val = out.get(dt_key)
            if isinstance(val, str) and val.strip() == "":
                out[dt_key] = None
            elif isinstance(val, str):
                from src.routes.utils import to_aware
                out[dt_key] = to_aware(val) or None

        # 2. dict ----------------------------------------------------------
        val = out.get("education_requirements")
        if isinstance(val, str):
            if val.strip() == "" or val == "[object Object]":
                out["education_requirements"] = None
            else:
                import json
                try:
                    out["education_requirements"] = json.loads(val)
                except json.JSONDecodeError:
                    out["education_requirements"] = None

        # 3. lists ---------------------------------------------------------
        for list_key in ("required_skills", "preferred_skills"):
            val = out.get(list_key)
            if isinstance(val, str):
                out[list_key] = [
                                    s.strip()
                                    for s in val.replace("\n", ",").split(",")
                                    if s.strip()
                                ] or None

        return out


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

    @computed_field(return_type=int)
    @property
    def total_applications_count(self) -> int:
        """
            Will Count the total number of applications for this job
        :return:
        """
        return len(self.applications)

    @computed_field(return_type=int)
    @property
    def like_count(self) -> int:
        """Total number of likes for this job"""
        return len(self.likes) if hasattr(self, 'likes') and self.likes else 0

    @computed_field(return_type=int)
    @property
    def share_count(self) -> int:
        """Total number of shares for this job"""
        return len(self.shares) if hasattr(self, 'shares') and self.shares else 0


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
        Uses Flesch Reading Ease score – returns True if score ≥ 50
        (anything 50–100 is considered readable for a general audience).
        """
        completeness_threshold = 6
        if self.job_completeness_score < completeness_threshold:
            return False
        try:
            score = flesch_reading_ease(text=self.ats_description, lang="en")
            return score >= 50
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
        print(f"READABILITY BONUS SCORE: {readability_score}")
        # Quality indicators bonus (up to 15 points)
        quality_bonus = 0
        if self.description and len(self.description.split()) > 100:
            quality_bonus += 3
        if self.company:
            quality_bonus += 3
        if self.salary_min and self.salary_max:
            quality_bonus += 3
        if self.required_skills and (len(self.required_skills) >= 3):
            quality_bonus += 3
        if self.application_instructions and (self.application_url or "email" in self.application_instructions.lower()):
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

    @property
    def job_keyword_listing(self) -> list[str]:
        """
        Returns a list of keywords (including duplicates) from:
        - required_skills
        - preferred_skills
        - description
        - title
        Already tokenized and stop-word–cleaned.
        """
        raw_parts = [
            *self.required_skills,
            *self.preferred_skills,
            self.description or "",
            self.title or "",
        ]
        keywords: list[str] = []
        for part in raw_parts:
            keywords.extend(tokenize(str(part)))
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

    @property
    def ats_description_display(self) -> str:
        """
        Markdown-ready, multi-line summary for ATS / employer display.
        Every line that should stand alone ends with "  \n".
        """
        lines = [
            f"**Job Title:** {self.title}  ",
            f"**Company:** {self.company.name if self.company else 'N/A'}  ",
            f"**Location:** {self.location}  ",
            f"**Type / Remote:** {self.position_type} • {self.remote_policy}  ",
            f"**Salary:** {self.salary}  ",
            f"**Expires:** {self.expires_at if self.expires_at else 'N/A'}  ",
            f"**Experience:** {self.experience_level}  ",
            "",
            "**Required Skills:**",
            "- " + ("\n- ".join(self.required_skills) if self.required_skills else "—"),
            "",
            "**Preferred Skills:**",
            "- " + ("\n- ".join(self.preferred_skills) if self.preferred_skills else "—"),
            "",
            "",
            "**Education Requirements:**",
            *(["—"] if not self.education_requirements else
              [f"- {k}: {v}" for k, v in self.education_requirements.items()]),
            "",
            "**Description:**",
            self.description or "—",
            "",
            "",
            "**Application Instructions:**",
            self.application_instructions or "—",
        ]
        return "\n".join(lines)

    @classmethod
    def create_from_enhanced_agent_output(
            cls,
            agent_output: "EnhanceJobPostOutput",
            employer_id: str,
            company_id: str,
            **kwargs
    ) -> "Job":
        """
        Build a Job instance from the enhancement agent output.

        The agent is allowed to leave fields empty (None / [] / {}); only the
        explicitly provided values are copied to the new Job record.
        """

        # ------------------------------------------------------------------
        # 1.  Core data that must always exist on a brand-new Job row
        # ------------------------------------------------------------------
        core = {
            "employer_id": employer_id,
            "company_id": company_id,
            "created_at": utc_time(),
            "updated_at": utc_time(),
            "posted_at": utc_time(),
        }

        # ------------------------------------------------------------------
        # 2.  Helper – copy only when the agent supplied something meaningful
        # ------------------------------------------------------------------
        
        def copy_if_provided(key: str, value):
            """Return {key: value} if value is truthy, else {}."""
            return {key: value} if value is not None and value != [] and value != {} else {}

        # ------------------------------------------------------------------
        # 3.  Map agent fields → Job fields (only when populated)
        # ------------------------------------------------------------------
        optional_updates = {
            **copy_if_provided("title", agent_output.title),
            **copy_if_provided("description", agent_output.description),
            **copy_if_provided("salary_min", agent_output.salary_min),
            **copy_if_provided("salary_max", agent_output.salary_max),
            **copy_if_provided("salary_currency", agent_output.salary_currency),
            **copy_if_provided("experience_level", agent_output.experience_level),
            **copy_if_provided("education_requirements", agent_output.education_requirements),
            **copy_if_provided("required_skills", agent_output.required_skills),
            **copy_if_provided("preferred_skills", agent_output.preferred_skills),
            **copy_if_provided("required_documents", agent_output.required_documents),
            **copy_if_provided("required_questionnaire", agent_output.required_questionnaire),
        }

        # ------------------------------------------------------------------
        # 4.  Date-time handling (special, because we compute defaults)
        # ------------------------------------------------------------------
        from src.routes.utils import to_aware

        expires_at = to_aware(getattr(agent_output, "expires_at", None))

        if not expires_at:
            expires_at = utc_time() + timedelta(days=60)

        application_deadline = to_aware(getattr(agent_output, "application_deadline", None))

        optional_updates.update(
            {
                "expires_at": expires_at,
                "application_deadline": application_deadline,
            }
        )

        # ------------------------------------------------------------------
        # 5.  Merge everything and let caller overrides win
        # ------------------------------------------------------------------
        job_data = {**core, **optional_updates, **kwargs}
        return cls(**job_data)

    # New computed properties for statistics
    @computed_field(return_type=float)
    @property
    def applications_per_day(self) -> float:
        """Calculate average applications per day since posting"""
        if not self.posted_at:
            return 0.0
        
        days_since_posted = (utc_time() - self.posted_at).days
        days_since_posted = max(1, days_since_posted)  # Avoid division by zero
        
        total_applications = len(self.applications) if self.applications else 0
        return total_applications / days_since_posted

    @computed_field(return_type=str)
    @property
    def application_trend_direction(self) -> str:
        """Determine if applications are increasing/decreasing over recent period"""
        if not self.applications or len(self.applications) < 2:
            return "stable"
        
        # Compare last 7 days vs previous 7 days
        now = utc_time()
        last_7_days = now - timedelta(days=7)
        previous_7_days = now - timedelta(days=14)

        # noinspection PyTypeChecker
        recent_count = sum(1 for app in self.applications if app.applied_date >= last_7_days)
        # noinspection PyTypeChecker
        previous_count = sum(1 for app in self.applications
                           if previous_7_days <= app.applied_date < last_7_days)
        
        if recent_count > previous_count * 1.2:
            return "increasing"
        elif recent_count < previous_count * 0.8:
            return "decreasing"
        else:
            return "stable"

    @computed_field(return_type=str)
    @property
    def application_velocity(self) -> str:
        """Calculate application velocity: accelerating, decelerating, or steady"""
        if not self.applications or len(self.applications) < 3:
            return "steady"
        
        # Get applications from last 7 days
        now = utc_time()
        last_7_days = now - timedelta(days=7)
        # noinspection PyTypeChecker
        recent_apps = [app for app in self.applications if app.applied_date >= last_7_days]
        
        if len(recent_apps) < 2:
            return "steady"
        
        # Sort by date and calculate daily changes
        recent_apps.sort(key=lambda x: x.applied_date)
        
        # Simple trend calculation based on first vs last few days
        first_half = recent_apps[:len(recent_apps)//2]
        second_half = recent_apps[len(recent_apps)//2:]
        
        first_half_rate = len(first_half) / max(1, len(first_half))
        second_half_rate = len(second_half) / max(1, len(second_half))
        
        if second_half_rate > first_half_rate * 1.5:
            return "accelerating"
        elif second_half_rate < first_half_rate * 0.7:
            return "decelerating"
        else:
            return "steady"

    model_config = ConfigDict(
        # automatically str() any HttpUrl, Decimal, datetime, etc.
        json_encoders={
            HttpUrl: str,
        },
        # optional: exclude unset/None fields from the response
        exclude_unset=True,
        extra="allow",
        str_strip_whitespace=True
    )


class JobEditableFields(BaseModel):
    """Model defining fields that can be updated by an employer"""

    # Job Details
    title: Optional[str] = Field(
        default=None, min_length=5, max_length=255, description="Job title"
    )
    description: Optional[str] = Field(default=None, description="Detailed job description")
    position_type: Optional[str] = Field(
        default="FULL_TIME",
        pattern="FULL_TIME|PART_TIME|CONTRACT",
        description="Type of employment",
    )
    remote_policy: Optional[str] = Field(
        default="ONSITE",
        pattern="ONSITE|HYBRID|REMOTE",
        description="Remote work policy",
    )

    # Category
    category_id: Optional[str] = Field(default=None, description="ID of the job category")

    # Compensation
    salary_min: Optional[float] = Field(default=None, ge=0, description="Minimum salary offered")
    salary_max: Optional[float] = Field(default=None, ge=0, description="Maximum salary offered")
    salary_currency: Optional[str] = Field(
        default=None, min_length=3, max_length=3, description="Currency code for salary"
    )
    salary_confidential: Optional[bool] = Field(
        default=False, description="Whether salary is confidential"
    )

    # Location
    city: Optional[str] = Field(
        default=None, min_length=2, max_length=100, description="Job location city"
    )
    province: Optional[str] = Field(
        default=None, min_length=2, max_length=100, description="Job location province/state"
    )
    country: Optional[str] = Field(
        default=None, min_length=2, max_length=100, description="Job location country"
    )

    # Timeline
    expires_at: Optional[datetime] = Field(
        default=None, description="When the job listing expires"
    )
    application_deadline: Optional[datetime] = Field(
        default=None, description="Deadline for applications"
    )

    # Requirements
    experience_level: Optional[str] = Field(
        default="ENTRY",
        pattern="ENTRY|MID|SENIOR",
        description="Required experience level",
    )

    education_requirements: Optional[dict[str, str] | str] = Field(
        default_factory=dict, description="Required education qualifications"
    )
    # ---- lists that may now come in as None ----
    required_skills: Optional[list[str] | str] = Field(
        default_factory=list, description="list of required skills"
    )
    preferred_skills: Optional[list[str] | str] = Field(
        default_factory=list, description="list of preferred skills"
    )
    required_documents: Optional[list[str] | str] = Field(
        default_factory=list, description="Documents required for application"
    )
    required_questionnaire: Optional[list[str] | str] = Field(
        default_factory=list, description="IDs of required questionnaires"
    )
    # Application Process
    application_url: Optional[str] = Field(
        default=None, description="URL for external applications"
    )
    application_instructions: Optional[str] = Field(
        default="We look forward to your application! Please submit your details and documents using the form provided. If you have any questions, feel free to contact us.",
        description="Instructions for applying"
    )
    # Metadata
    summary: Optional[str] = Field(default=None, description="Short summary of the job")
    seo_description: Optional[str] = Field(
        default=None, description="SEO-optimized description"
    )

    # Status Management
    status: Optional[str] = Field(
        default=None,
        pattern="draft|pending|active|closed|archived",
        description="Current status of the job listing",
    )

    # -------------- Validators --------------

    @model_validator(mode="after")
    def validate_dates(self) -> "JobEditableFields":
        """Ensure dates are logical and within acceptable ranges"""
        now = utc_time()
        max_future = now + timedelta(days=365)

        if self.expires_at:
            self.expires_at = self.expires_at.replace(tzinfo=timezone.utc)
            if self.expires_at < now:
                raise ValueError("expires_at must be in the future")
            if self.expires_at > max_future:
                raise ValueError("expires_at cannot be more than 1 year in the future")

        if self.application_deadline:
            self.application_deadline = self.application_deadline.replace(tzinfo=timezone.utc)
            if self.application_deadline < now:
                raise ValueError("application_deadline must be in the future")
            if self.expires_at and self.application_deadline > self.expires_at:
                raise ValueError("application_deadline cannot be after expires_at")
        return self

    @model_validator(mode="after")
    def validate_salary(self) -> "JobEditableFields":
        """Ensure salary range is logical"""
        if (
                self.salary_min is not None
                and self.salary_max is not None
                and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min cannot be greater than salary_max")
        return self

    @model_validator(mode="after")
    def normalize_lists_and_trim(self) -> "JobEditableFields":
        """
        - Treat empty string or comma-separated string as optional list input.
        - Trim application_instructions.
        - Keep `None` when the client explicitly sends `null`.
        """
        for field in (
                "required_skills",
                "preferred_skills",
                "required_documents",
                "required_questionnaire",
        ):
            raw = getattr(self, field)
            if isinstance(raw, str):
                # split on commas, drop empty parts
                setattr(
                    self,
                    field,
                    [part.strip() for part in raw.split(",") if part.strip()] or [],
                )
            elif not raw:
                setattr(self, field, [])
            # None stays None

        if isinstance(self.application_instructions, str):
            default_message: str = ("We look forward to your application! Please submit your details and documents "
                                    "using the form provided. If you have any questions, feel free to contact us.")
            self.application_instructions = self.application_instructions.strip() or default_message

        raw = self.education_requirements
        if isinstance(raw, str):
            # Accept either JSON string (object) or simple key:value pairs
            # 1) Try JSON first
            try:
                parsed: dict[str, str] = json.loads(raw)
                if not isinstance(parsed, dict):
                    raise ValueError
                # Trim keys & values
                parsed = {k.strip(): v.strip() for k, v in parsed.items() if k.strip()}
            except (json.JSONDecodeError, ValueError):
                # 2) Fallback to comma-separated key:value
                items = [part.strip() for part in raw.split(",") if part.strip()]
                parsed = {}
                for item in items:
                    if ":" not in item:
                        continue
                    key, val = item.split(":", 1)
                    key, val = key.strip(), val.strip()
                    if key:
                        parsed[key] = val
            self.education_requirements = parsed or {}
        elif not raw:
            self.education_requirements = {}

        return self

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

class SavedJob(BaseModel):
    """
        Candidates will follow specific jobs using this Model.
    """
    saved_job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    created_at: AwareDatetime = Field(default_factory=lambda: utc_time())

    job : Optional[Job] = Field(default=None, description="Job related to this saved job")
    jobseeker_profile: Optional['JobSeekerProfile'] = Field(default=None, description="Job Seeker related to this saved job")

    model_config = ConfigDict(from_attributes=True)


class ATSReport(BaseModel):
    ats_report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = Field(..., description="ID of the job the report is associated with")
    cv_id: str = Field(..., description="ID of the CV used in the evaluation")
    score: float = Field(..., ge=0, le=100, description="ATS score out of 100")
    matched_keywords: list[str] = Field(default_factory=list, description="list of matched keywords found in CV")
    missing_keywords: list[str] = Field(default_factory=list, description="list of important keywords not found in CV")
    feedback: str = Field(..., description="Feedback based on the ATS evaluation")
    created_at: AwareDatetime = Field(default_factory=lambda: utc_time(), description="Timestamp when the report was generated")
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

    @classmethod
    def success_stages(self) -> list[str]:
        """Return the stages that can be considered a successful outcome."""
        return [
            self.INTERVIEWING.value,
            self.SHORTLISTED.value,
            self.OFFER_EXTENDED.value,
            self.HIRED.value,
        ]

class JobApplication(BaseModel):
    application_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    ats_report_id: Optional[str]

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

    # New workflow fields
    workflow_step: str = Field(default="draft")  # draft, cover_letter, questionnaires, review, submitted
    cover_letter_session_id: Optional[str] = None
    questionnaire_start_time: Optional[AwareDatetime] = None
    questionnaire_completion_time: Optional[AwareDatetime] = None
    time_spent_on_questionnaires: Optional[int] = None  # seconds
    workflow_started_at: Optional[AwareDatetime] = Field(default_factory=utc_time)
    workflow_completed_at: Optional[AwareDatetime] = None

    # relationships
    ats_report: Optional[ATSReport] = Field(default=None)
    job: Optional[Job] = Field(None)  # Relationship to JobModel
    jobseeker_profile: Optional[JobSeekerProfile] = Field(default=None)

    model_config = ConfigDict(from_attributes=True)

    @property
    def applied_date_as_datetime(self) -> datetime:
        """
        :return:
        """
        # noinspection PyTypeChecker
        return self.applied_date

    @property
    def is_recent_application(self):
        recent_cut_off_date = utc_time() - timedelta(days=7)
        return self.applied_date > recent_cut_off_date
        
    @property
    def is_shortlisted(self) -> bool:
        return self.application_stage == JobApplicationStatusEnum.SHORTLISTED.value

    @property
    def is_under_review(self) -> bool:
        return self.application_stage == JobApplicationStatusEnum.UNDER_REVIEW.value

    @property
    def is_successful(self) -> bool:
        return self.application_stage in {
            JobApplicationStatusEnum.HIRED.value,
            JobApplicationStatusEnum.OFFER_EXTENDED.value
        }

    @property
    def is_rejected(self) -> bool:
        return self.application_stage == JobApplicationStatusEnum.REJECTED.value

    @property
    def is_active(self) -> bool:
        return self.application_stage not in {
            JobApplicationStatusEnum.REJECTED.value,
            JobApplicationStatusEnum.WITHDRAWN.value,
            JobApplicationStatusEnum.HIRED.value
        }

    @property
    def needs_action(self) -> bool:
        return bool(
            self.missing_requirements or 
            ('cover_letter' in self.required_documents and not self.cover_letter)
        )

    # ATS Report related flags

    @property
    def has_ats_report(self) -> bool:
        return self.ats_report is not None

    @property
    def ats_score(self) -> Optional[float]:
        return self.ats_report.score if self.ats_report else None

    @property
    def ats_feedback(self) -> Optional[str]:
        return self.ats_report.feedback if self.ats_report else None

    @property
    def missing_keywords(self) -> list[str]:
        return self.ats_report.missing_keywords if self.ats_report else []

    @property
    def matched_keywords(self) -> list[str]:
        return self.ats_report.matched_keywords if self.ats_report else []

    @property
    def is_ats_ready(self) -> bool:
        """
        Consider ATS ready if score >= 75 and there are minimal missing keywords.
        You can tune this logic based on real-world insights.
        """
        if not self.ats_report:
            return False
        return self.ats_report.score >= 75 and len(self.ats_report.missing_keywords) <= 3

    @property
    def ats_risk(self) -> bool:
        """
        Flag applications with low ATS score or many missing keywords.
        """
        if not self.ats_report:
            return False
        return self.ats_report.score < 50 or len(self.ats_report.missing_keywords) > 5

    @property
    def resume_used(self):
        """
        Returns the resume used in the job application.
        Conditions:
        - jobseeker_profile must be present
        - cv_id must be set
        The resume is found in jobseeker_profile.linked_resumes.
        """
        if self.jobseeker_profile and self.cv_id:
            resumes = getattr(self.jobseeker_profile, "linked_resumes", [])
            for resume in resumes:
                if getattr(resume, "cv_id", None) == self.cv_id:
                    return resume
        return None

    # New workflow properties
    @property
    def workflow_completion_percentage(self) -> int:
        """Calculate workflow completion percentage"""
        steps = {
            'draft': 10,
            'cover_letter': 40,
            'questionnaires': 70,
            'review': 90,
            'submitted': 100
        }
        return steps.get(self.workflow_step, 0)
    
    @property
    def is_workflow_complete(self) -> bool:
        """Check if workflow is complete"""
        return self.workflow_step == 'submitted'
    
    @property
    def next_workflow_step(self) -> Optional[str]:
        """Get next step in workflow"""
        steps = ['draft', 'cover_letter', 'questionnaires', 'review', 'submitted']
        try:
            current_index = steps.index(self.workflow_step)
            return steps[current_index + 1] if current_index < len(steps) - 1 else None
        except ValueError:
            return 'cover_letter'
    
    @property
    def workflow_duration_minutes(self) -> Optional[float]:
        """Get total workflow duration in minutes"""
        if self.workflow_started_at and self.workflow_completed_at:
            delta = self.workflow_completed_at - self.workflow_started_at
            return delta.total_seconds() / 60
        return None
    
    @property
    def questionnaire_duration_minutes(self) -> Optional[float]:
        """Get questionnaire completion time in minutes"""
        if self.time_spent_on_questionnaires:
            return self.time_spent_on_questionnaires / 60
        return None
    
    @property
    def has_cover_letter_session(self) -> bool:
        """Check if application has an associated cover letter session"""
        return bool(self.cover_letter_session_id)
    
    @property
    def questionnaires_completed(self) -> bool:
        """Check if questionnaires have been completed"""
        return bool(self.questionnaire_completion_time)
    
    @property
    def workflow_step_display(self) -> str:
        """Get human-readable workflow step"""
        step_names = {
            'draft': 'Draft Created',
            'cover_letter': 'Cover Letter Generated',
            'questionnaires': 'Questionnaires Completed',
            'review': 'Ready for Review',
            'submitted': 'Application Submitted'
        }
        return step_names.get(self.workflow_step, 'Unknown Step')
    
    def update_workflow_step(self, new_step: str) -> None:
        """Update workflow step and set completion time if final step"""
        self.workflow_step = new_step
        self.updated_at = utc_time()
        
        if new_step == 'submitted' and not self.workflow_completed_at:
            self.workflow_completed_at = utc_time()
            if self.application_stage == 'DRAFT':
                self.application_stage = JobApplicationStatusEnum.APPLIED.value
                self.applied_date = utc_time()
    
    def start_questionnaire_timer(self) -> None:
        """Start questionnaire timer"""
        self.questionnaire_start_time = utc_time()
    
    def complete_questionnaires(self, time_spent_seconds: int) -> None:
        """Complete questionnaires and record timing"""
        self.questionnaire_completion_time = utc_time()
        self.time_spent_on_questionnaires = time_spent_seconds
        self.workflow_step = 'review'

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



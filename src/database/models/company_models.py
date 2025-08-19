import re
import uuid
from datetime import timedelta, date, datetime
from difflib import SequenceMatcher
from enum import Enum
from typing import Optional, List, Union

from pydantic import BaseModel, Field, field_validator, HttpUrl, EmailStr, ConfigDict, AwareDatetime

from src.database.constants import utc_time
from src.database.models.jobseeker_profile import JobSeekerProfile
from src.utils.route_helpers import get_service


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
    HUMAN_REVIEW = "human_review"
    DOCUMENTS_UPLOADED = "documents_uploaded"
    DOCUMENTS_REJECTED = "documents_rejected"
    DOCUMENTS_APPROVED = "documents_approved"
    CIPC_PENDING = "cipc_pending"
    CIPC_VERIFIED = "cipc_verified"
    CIPC_FAILED = "cipc_failed"
    VERIFIED = "verified"

# noinspection PyUnresolvedReferences,PyTypeHints
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

    billing_email: Optional[str] = Field(default=None, max_length=20)  # Optional billing email for invoices
    send_invoice_emails: Optional[bool] = Field(default=True)
    send_trial_reminders: Optional[bool] = Field(default=True)

    # Company Details
    employee_count: Optional[int] = Field(default=None, ge=1)
    founded_year: Optional[int] = Field(default=None, ge=1800, le=utc_time().year)
    tech_stack: Optional[list[str]] = Field(default=None)

    # Social Media
    linkedin_url: Optional[HttpUrl] = Field(default=None)
    twitter_handle: Optional[str] = Field(default=None, max_length=15)

    is_verified: Optional[bool] = Field(default=False)
    time_verification_process_started: Optional[AwareDatetime] = Field(default=None)
    verification_status: str = Field(default=CompanyVerificationStatus.NOT_VERIFIED.value)

    created_at: Optional[AwareDatetime] = Field(default_factory=utc_time, description="Company creation timestamp")
    updated_at: Optional[AwareDatetime] = Field(default=None, description="Last update timestamp")

    # Relationships
    jobs: Optional[list['Job']] = Field(default_factory=list)  # Forward reference
    saved_candidates: Optional[list['SavedCandidates']] = Field(default_factory=list)
    employers: Optional[list['Employer']] = Field(default_factory=list)
    ip_address: Optional[str] = Field(default_factory=lambda : get_service("ip_address")())
    model_config = ConfigDict(from_attributes=True)


    @property
    def applications_stats_by_job(self):
        """

        :return:
        """
        if self.total_jobs == 0:
            return 0, 0
        _job_stat: dict[str, int] = {

        }
        application_stats_by_job = {
            "job_title": {
                "reviewed_applications":0,
                "in_progress":0,
            }
        }
        for job in self.jobs:
            _job_stat['reviewed_applications'] = job.reviewed_applications_count
            _job_stat['in_progress'] = job.in_progress_applications_count
            application_stats_by_job[job.title] = _job_stat

        return application_stats_by_job

    @property
    def company_is_recent(self):
        """sumary_line
            returns true if the company was created within the last 30 days
        Keyword arguments:
        argument -- description
        Return: return_description
        """
        if not self.time_verification_process_started:
            return False
        return (utc_time() - self.created_at).days <= 30

    @property
    def total_reviewed_count(self):
        return sum(job.reviewed_applications_count for job in self.jobs) if self.jobs else 0

    @property
    def total_in_progress_count(self):
        return sum(job.in_progress_applications for job in self.jobs) if self.jobs else 0

    @property
    def location(self) -> str:
        """Formatted location string"""
        parts = [self.city, self.province, self.country]
        return ', '.join(part for part in parts if part)


    @property
    def total_saved_candidates(self) -> int:
        """Total saved candidates"""
        return len(self.saved_candidates) if self.saved_candidates else 0
    
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
        now = utc_time()
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
        return sum(job.total_applications for job in self.jobs)

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

    # noinspection PyTypeHints
    @property
    def recent_applications(self) -> list['JobApplication']:
        if not self.jobs:  # No need to check total_applications separately
            return []
        recent_apps = []
        for job in self.jobs:
            # Only process jobs that actually have applications
            if not job.applications:
                continue
            for application in job.applications:
                # Directly compare datetime instead of relying on is_recent_application
                if application.is_recent_application:
                    recent_apps.append(application)

        return recent_apps

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
    # Security Rules
    @property
    def has_duplicate_job_descriptions(self):
        """

        :return:
        """
        descriptions = [job.description for job in self.jobs if job.description]
        for i in range(len(descriptions)):
            for j in range(i + 1, len(descriptions)):
                similarity = SequenceMatcher(None, descriptions[i], descriptions[j]).ratio()
                if similarity > 0.9:
                    return True
        return False

    @property
    def has_multiple_edits_in_last_hour(self):
        """Detect if Multiple edits were made to jobs in the last hour"""
        if not self.jobs:
            return False

        recent_posts = sorted(self.jobs, key=lambda j: j.updated_at, reverse=True)
        for i in range(1, len(recent_posts)):
            delta = recent_posts[i - 1].updated_at - recent_posts[i].updated_at
            if delta < timedelta(minutes=5):  # multiple edits within 5 mins
                return True
        return False

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

    # New computed properties for statistics
    @property
    def jobs_posted_last_12_months(self) -> int:
        """Count jobs posted in the last 12 months"""
        if not self.jobs:
            return 0
        
        cutoff_date = utc_time() - timedelta(days=365)
        return sum(1 for job in self.jobs if job.posted_at and job.posted_at >= cutoff_date)

    @property
    def average_applications_per_job_last_12_months(self) -> float:
        """Calculate average applications per job for jobs posted in last 12 months"""
        recent_jobs = [job for job in (self.jobs or []) 
                      if job.posted_at and job.posted_at >= (utc_time() - timedelta(days=365))]
        
        if not recent_jobs:
            return 0.0
        
        total_applications = sum(len(job.applications or []) for job in recent_jobs)
        return total_applications / len(recent_jobs)

    @property
    def hiring_activity_level(self) -> str:
        """Determine company hiring activity level based on recent job postings"""
        jobs_12_months = self.jobs_posted_last_12_months
        active_jobs = self.active_jobs
        
        if jobs_12_months >= 20 or active_jobs >= 10:
            return "high"
        elif jobs_12_months >= 5 or active_jobs >= 3:
            return "medium"
        else:
            return "low"

    @property
    def average_time_to_fill_positions(self) -> Optional[float]:
        """Calculate average time to fill positions in days"""
        if not self.jobs:
            return None
        
        filled_positions = []
        for job in self.jobs:
            if job.status == 'closed' and job.applications:
                # Find the hired application
                hired_app = next((app for app in job.applications
                                if hasattr(app, 'application_stage') and 
                                app.application_stage == 'Hired'), None)
                if hired_app and job.posted_at:
                    days_to_fill = (hired_app.applied_date - job.posted_at).days
                    if days_to_fill > 0:  # Sanity check
                        filled_positions.append(days_to_fill)
        
        return sum(filled_positions) / len(filled_positions) if filled_positions else None

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

class CompanyUpdate(BaseModel):
    """Model for partial company updates"""
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[HttpUrl] = None
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    employee_count: Optional[Union[int, str]] = None
    founded_year: Optional[int] = None
    tech_stack: Optional[list[str]] = None
    linkedin_url: Optional[HttpUrl] = None
    twitter_handle: Optional[str] = None
    logo_url: Optional[HttpUrl] = None
    is_public: Optional[bool] = None
    ip_address: Optional[None] = None

    # # Reuse validators from main Company model
    # _validate_phone = field_validator("phone_number", mode="before")(Company.__fields__["phone_number"].validate)
    # _validate_twitter = field_validator("twitter_handle", mode="before")(Company.__fields__["twitter_handle"].validate)
    model_config = ConfigDict(from_attributes=True, extra="ignore")

class AllowableCompanyVerificationDocumentsEnum(Enum):
    """Allowable documents for company verification in South Africa"""
    CIPC_CERTIFICATE_OF_INCORPORATION = "CIPC_CERT"
    CIPC_DIRECTORS_REPORT = "CIPC Directors Report (CoR39.1)"
    SARS_TAX_COMPLIANCE_PIN = "SARS Tax Compliance Status PIN"
    SARS_VAT_REGISTRATION = "SARS VAT Registration Certificate"
    CIPC_ANNUAL_RETURN = "CIPC Annual Return (CoR30.1)"
    TAX_CLEARANCE = "TAX_CLEARANCE"
    CK1_FOUNDING_STATEMENT = "CK1 Founding Statement (Close Corporations)"
    BUSINESS_BANK_STATEMENT = "Business Bank Statement (SA Bank, recent)"
    MUNICIPAL_ACCOUNT = "Municipal Account (Business premises)"
    LEASE_AGREEMENT = "Lease Agreement (Business premises)"
    BEE_CERTIFICATE = "BEE_CERT"
    BUSINESS_LICENSE = "Sector-Specific Business License"
    FINANCIAL_STATEMENTS = "Audited Financial Statements"
    CERTIFIED_ID_COPIES = "Certified ID Copies of Directors"
    DIRECTOR_ID_CARD_FRONT = "DIRECTOR_ID"

    @classmethod
    def sa_company_documents_list(cls) -> list[str]:
        """Get all allowable SA document names as strings"""
        return [doc.value for doc in cls]

class AIBasedDocumentReviewResult(BaseModel):
    """
    Pydantic model for AI-Based Document Review Result
    """

    review_id: str = Field(default_factory=lambda : str(uuid.uuid4()),
                           description="Unique ID of the review process")

    document_id: str = Field(..., description="ID of the document reviewed")
    is_document_valid: bool = Field(..., description="Indicates if the document is valid")
    reason: Optional[str] = Field(None, description="Reason for invalidity, if any")

    match_director_name: Optional[bool] = Field(None, description="Whether director name matches expected")
    match_id_number: Optional[bool] = Field(None, description="Whether ID number matches expected")
    match_cipc_data: bool = Field(False, description="Whether document data matches CIPC records")
    match_company_profile_data: bool = Field(False, description="Whether document matches internal company profile")
    cipc_number_verified_online: bool = Field(False, description="Whether CIPC number was verified online")
    cipc_number_verification_notes: Optional[str] = Field(None, description="Notes on CIPC number verification")

    is_suspicious: bool = Field(False, description="Whether the document appears suspicious")
    suspicious_notes: Optional[str] = Field(None, description="Details of suspicious elements if any")

    requires_human_review: bool = Field(False, description="Whether the document needs human review")
    document_type: str = Field(..., description="Type of the document reviewed")
    score: Optional[float] = Field(None, description="AI confidence score or overall score of review")
    reviewer_notes: Optional[str] = Field(None, description="Notes or comments from the AI reviewer")

    created_at: AwareDatetime = Field(..., description="Timestamp when the review was completed")

    model_config = ConfigDict(from_attributes=True)

class CompanyVerificationDocument(BaseModel):
    document_id: str = Field(default_factory=lambda : str(uuid.uuid4()))
    company_id: str
    ai_review_id: Optional[str] = Field(default=None)
    document_type: str  # You can use Enum here for safety
    file_url: HttpUrl
    uploaded_at: AwareDatetime = Field(default_factory=utc_time)

    status: Optional[str] = Field(default="pending")
    reviewed_by: Optional[str] = Field(default=None)
    reviewed_at: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    ai_review: Optional[list[AIBasedDocumentReviewResult]] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class DirectorDetails(BaseModel):
    director_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cipc_id: str
    full_names: str
    id_number: str

class CompanyCIPC(BaseModel):
    cipc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    company_name: str
    registration_number: str
    registration_date: Optional[date]
    registered_address: Optional[str]
    company_type: Optional[str]  # e.g., "Private Company", "Non-Profit"


    tax_pin: Optional[str]
    bee_status: Optional[str]
    status: Optional[str] = Field(default="pending")  # pending, verified, failed
    verified_at: Optional[AwareDatetime] = Field(default=None)
    # Relationship
    director_details: list[Optional[DirectorDetails]] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

class InterestLevel(str, Enum):
    LOW = "low"
    INTERESTED = "interested"
    HIGHLY_INTERESTED = "highly_interested"
    TOP_PRIORITY = "top_priority"
    ON_HOLD = "on_hold"

class CompanyFollowing(BaseModel):
   """This Model captures the details of the Follow
   by the Jobseeker to a company
   """
   follow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
   followed_at: AwareDatetime = Field(default_factory=utc_time)
   user_id: str
   company_id: str
   last_notified_at: Optional[AwareDatetime] = Field(default=None)

   interest_level: str = Field(default=InterestLevel.INTERESTED.value)

   jobseeker_follower: Optional[JobSeekerProfile] = Field(default=None)
   followed_company: Optional[Company] = Field(default=None)
   model_config = ConfigDict(from_attributes=True)

   @property
   def recent_follow(self) -> bool:
       """Check if this follow happened within the last 7 days"""
       return (utc_time() - self.followed_at).days <= 7

   @property
   def days_following(self) -> int:
       """Number of days since following this company"""
       return (utc_time() - self.followed_at).days

   @property
   def weeks_following(self) -> int:
       """Number of weeks since following this company"""
       return self.days_following // 7

   @property
   def is_highly_interested(self) -> bool:
       """Check if interest level is high"""
       return self.interest_level == InterestLevel.HIGHLY_INTERESTED.value

   @property
   def follow_age_category(self) -> str:
       """Categorize follow by age"""
       days = self.days_following
       if days <= 7:
           return "new"
       elif days <= 30:
           return "recent"
       elif days <= 90:
           return "active"
       else:
           return "old"

   @property
   def needs_notification(self) -> bool:
       """Check if user needs notification about company updates"""
       if not self.last_notified_at:
           return True
       return (utc_time() - self.last_notified_at).days >= 7

   @property
   def company_name(self) -> Optional[str]:
       """Get company name if company data is loaded"""
       return self.followed_company.name if self.followed_company else None

   @property
   def follower_name(self) -> Optional[str]:
       """Get follower name if jobseeker data is loaded"""
       return self.jobseeker_follower.full_name if self.jobseeker_follower else None

class CandidateStatus(str, Enum):
    SAVED = "saved"
    REVIEWED = "reviewed"
    CONTACTED = "contacted"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    OFFER_EXTENDED = "offer_extended"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

class SavedCandidates(BaseModel):
    """Pydantic model for SavedCandidates"""
    model_config = ConfigDict(from_attributes=True)

    saved_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    candidate_uid: str
    company_id: str
    saved_by: str
    interest_level: InterestLevel = InterestLevel.INTERESTED
    status: CandidateStatus = CandidateStatus.SAVED
    notes: Optional[str] = Field(default=None)
    internal_notes: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    last_contacted_at: Optional[AwareDatetime] = Field(default=None)
    contact_count: int = Field(default=0)
    saved_at: Optional[AwareDatetime] = Field(default=None)
    updated_at: Optional[AwareDatetime] = Field(default=None)


########################################################
###3 COMPANY SETTINGS
########################################################

class CompanySettings(BaseModel):
    company_id: str  # FK or UUID

    # General
    default_job_duration_days: int = Field(default=30)
    auto_publish_jobs: bool = Field(default=False)
    job_visibility: str = "public"  # Enum in production
    allow_featured_jobs: bool = Field(default=True)
    max_open_jobs: int = Field(default=10)

    # Application
    auto_response_enabled: bool = Field(default=False)
    default_response_message: Optional[str] = "Thank you for your application."
    require_cover_letter: bool = Field(default=False)
    required_documents: list[str] = Field(default_factory=lambda: ["resume"])
    questionnaire_enabled: bool = Field(default=False)
    allow_withdrawals: bool = Field(default=True)

    # Branding
    email_sender_name: Optional[str] = Field(default=None)
    email_signature: Optional[str] = Field(default=None)
    custom_email_template_enabled: bool = Field(default=False)
    custom_application_success_page_url: Optional[str] = Field(default=None)

    # Team Access
    team_invites_enabled: bool = Field(default=True)
    max_recruiters: int = Field(default=5)
    recruiter_roles: Optional[dict] = Field(default_factory=dict)

    # Notifications
    weekly_digest_enabled: bool = Field(default=True)
    slack_notifications_enabled: bool = Field(default=False)
    slack_webhook_url: Optional[str] = Field(default=None)
    notify_on_new_application: bool = Field(default=True)

    model_config = ConfigDict(from_attributes=True)

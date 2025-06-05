from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Optional, List
from datetime import datetime

from src.utils.route_helpers import get_controller


class JobSeekerProfile(BaseModel):
    user_uid: str  # FK to User.uid

    first_name: str
    last_name: str
    # Basic info
    bio: Optional[str] = None
    email: str

    alerts_enabled: bool = Field(default=True)
    receive_deadline_reminders: bool = Field(default=True)
    reminder_days_before: int = Field(default=7)
    last_reminded_at: datetime| None = Field(default=None)
    receive_company_updates: bool = Field(default=True)

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

    # List of job applications submitted by the Job Seeker
    applications: Optional[list['JobApplication']] = Field(default_factory=list, description="List of JobApplications for Jobseeker")
    # List of records showing records where companies saved the candidate for further onsideration
    interested_companies: Optional[List['SavedCandidates']] = Field(default_factory=list, description="List of companies the job seeker is interested in")
    # Companies the Job Seeker is following
    following_companies: Optional[List['CompanyFollowing']] = Field(default_factory=list, description="List of records showing companies the job seeker is following")
    resumes_list: Optional[list['JobSeekerCV']] = Field(default_factory=list)

    ip_address: Optional[str] = Field(default=None, description="Last known IP address of the job) seeker")
    device_finger_print: Optional[str] = Field(default=None, description="Device fingerprint for security checks")

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
    @property
    def can_send_job_recommendations(self) -> bool:
        """
            Determines if the job seeker can receive job recommendations based on their profile settings.
        """
        return self.alerts_enabled and self.receive_company_updates

    @property
    def detect_burst_applications(self) -> bool:
        """
        Detects unusually fast application bursts (e.g. more than 10 within 60 seconds).
        """
        applications = self.applications or []
        timestamps = sorted([app.applied_date for app in applications])

        if len(timestamps) < 10:
            return False

        # Check if 10 applications happened within a 1-minute window
        for i in range(len(timestamps) - 9):
            delta = (timestamps[i + 9] - timestamps[i]).total_seconds()
            if delta <= 60:
                return True

        return False

    def detect_multiple_accounts(self) -> bool:
        """
        Checks if multiple accounts are associated with the same IP address or device fingerprint.
        for the job seeker
        """
        if not self.ip_address and not self.device_finger_print:
            return False
        jobseekers_controller = get_controller('job_seeker_profile')
        # Query other accounts sharing the same IP or device

        job_seekers_list = jobseekers_controller.get_jobseekers_by_ip_address(self.ip_address)

        for job_seeker in job_seekers_list:
            if job_seeker.device_finger_print == self.device_finger_print and job_seeker.user_uid != self.user_uid:
                return True
        return False

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        },
        "from_attributes": True  # allows ORM models to be parsed directly
    }

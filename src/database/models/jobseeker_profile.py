from typing import Optional, List

from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict, AwareDatetime

from src.database.constants import utc_time
from src.utils.route_helpers import get_controller


# noinspection PyUnresolvedReferences
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
    last_reminded_at: AwareDatetime | None = Field(default=None)
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
    last_updated: AwareDatetime = Field(default_factory=lambda: utc_time())

    # List of job applications submitted by the Job Seeker
    # noinspection PyTypeHints
    applications: Optional[list['JobApplication']] = Field(default_factory=list, description="List of JobApplications for Jobseeker")
    # List of records showing records where companies saved the candidate for further consideration
    interested_companies: Optional[List['SavedCandidates']] = Field(default_factory=list, description="List of companies the job seeker is interested in")
    # Companies the Job Seeker is following
    following_companies: Optional[List['CompanyFollowing']] = Field(default_factory=list, description="List of records showing companies the job seeker is following")
    # noinspection PyTypeHints
    resumes_list: Optional[list['JobSeekerCV']] = Field(default_factory=list)

    ip_address: Optional[str] = Field(default=None, description="Last known IP address of the job) seeker")
    device_finger_print: Optional[str] = Field(default=None, description="Device fingerprint for security checks")

    # TODO SavedJobs should be linked here.
    saved_jobs: Optional[List['SavedJob']] = Field(default_factory=list, description="List of jobs saved by the job seeker")

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
    def total_saved_jobs(self) -> int:
        """
        Returns the total number of jobs saved by the job seeker.
        """
        return len(self.saved_jobs) if self.saved_jobs else 0

    @property
    def total_applications(self) -> int:
        """
        Returns the total number of job applications submitted by the job seeker.
        """
        return len(self.applications) if self.applications else 0

    @property
    def profile_completion_percentage(self) -> int:
        score = 0
        max_score = 0

        def add_score(condition: bool, weight: float):
            nonlocal score, max_score
            max_score += weight
            if condition:
                score += weight

        # Basic Info
        add_score(bool(self.first_name), 1.66)
        add_score(bool(self.last_name), 1.66)
        add_score(bool(self.email), 1.66)
        add_score(bool(self.bio), 5)
        add_score(bool(self.profile_image_url), 3)

        # Contact / Social
        add_score(bool(self.phone), 2)
        add_score(bool(self.location), 2)
        add_score(bool(self.linkedin or self.github or self.website), 3)

        # Preferences
        add_score(bool(self.job_titles_of_interest), 3)
        add_score(bool(self.industries_of_interest), 3)
        add_score(bool(self.locations_of_interest), 3)

        # Resume
        add_score(bool(self.resumes_list), 5)

        # Freelance (optional)
        if self.is_freelancer:
            add_score(bool(self.freelance_skills), 2)
            add_score(bool(self.hourly_rate), 1.5)
            add_score(bool(self.freelance_availability or self.freelance_experience), 1.5)

        percent = int((score / max_score) * 100) if max_score else 0
        return min(percent, 100)

    @property
    def profile_completion_hints(self) -> List[str]:
        hints = []

        if not self.bio:
            hints.append("Add a short bio to help employers understand your background.")
        if not self.profile_image_url:
            hints.append("Upload a profile picture to increase trust.")
        if not self.phone:
            hints.append("Add your phone number so employers can contact you easily.")
        if not self.location:
            hints.append("Specify your current location or preferred location.")
        if not (self.linkedin or self.github or self.website):
            hints.append("Add at least one social link (LinkedIn, GitHub, or personal website).")
        if not self.job_titles_of_interest:
            hints.append("Add at least one job title you're interested in.")
        if not self.industries_of_interest:
            hints.append("Specify your industries of interest.")
        if not self.locations_of_interest:
            hints.append("Add preferred job locations.")
        if not self.resumes_list:
            hints.append("Upload your resume to attract more employers.")

        if self.is_freelancer:
            if not self.freelance_skills:
                hints.append("List your freelance skills.")
            if not self.hourly_rate:
                hints.append("Set your hourly rate for freelance work.")
            if not (self.freelance_availability or self.freelance_experience):
                hints.append("Add freelance availability or a short summary of your experience.")

        return hints


    @property
    def is_profile_complete(self) -> bool:
        """
            Determines if the job seeker's profile is complete based on profile completion percentage.
            complete profiles can be used to apply for jobs and receive recommendations.
        """
        return self.profile_completion_percentage >= 80


    @property
    def can_send_job_recommendations(self) -> bool:
        """
            Determines if the job seeker can receive job recommendations based on their profile settings.
        """
        return self.alerts_enabled and self.receive_company_updates and self.is_profile_complete

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

    model_config = ConfigDict(from_attributes=True)

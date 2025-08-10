from typing import Optional, List

from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict, AwareDatetime

from src.database.constants import utc_time
from src.utils.route_helpers import get_controller

from enum import Enum

class HintPriority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class Hint(BaseModel):
    message: str
    priority: HintPriority = HintPriority.MEDIUM
    context: Optional[str] = None  # e.g. "Profile", "ATS", "Application: Job Title"


# noinspection PyUnresolvedReferences

class JobSeekerProfile(BaseModel):
    user_uid: str  # FK to User.uid

    # --- Referral Info ---
    referrer_id: Optional[str] = Field(default=None)
    referral_count: int = Field(default=0)
    referral_bonus_earned: float = Field(default=0.0)

    # --- Personal Info ---
    first_name: str
    last_name: str
    email: str
    bio: Optional[str] = Field(default=None)
    profile_image_url: Optional[HttpUrl] = Field(default=None)

    has_disability: bool = Field(default=False)

    # --- Settings ---
    alerts_enabled: bool = Field(default=True)
    receive_deadline_reminders: bool = Field(default=True)
    reminder_days_before: int = Field(default=7)
    last_reminded_at: Optional[AwareDatetime] = Field(default=None)
    receive_company_updates: bool = Field(default=True)
    visibility: bool = Field(default=True)
    last_updated: AwareDatetime = Field(default_factory=utc_time)


    # --- Verification ---
    verified_email: bool = Field(default=False)
    verified_phone: bool = Field(default=False)
    verified_linkedin: bool = Field(default=False)
    verified_github: bool = Field(default=False)

    # --- Contact & Location ---
    location: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    website: Optional[HttpUrl] = Field(default=None)
    linkedin: Optional[HttpUrl] = Field(default=None)
    github: Optional[HttpUrl] = Field(default=None)

    # --- Preferences ---
    job_titles_of_interest: Optional[List[str]] = Field(default_factory=list)
    industries_of_interest: Optional[List[str]] = Field(default_factory=list)
    locations_of_interest: Optional[List[str]] = Field(default_factory=list)
    remote_preference: Optional[bool] = Field(default=False)
    availability: Optional[str] = Field(default=None)
    expected_salary: Optional[int] = Field(default=None)

    # --- Freelance ---
    is_freelancer: bool = Field(default=False)
    freelance_skills: Optional[List[str]] = Field(default_factory=list)
    hourly_rate: Optional[float] = Field(default=None)  # Ensure this can be None
    freelance_experience: Optional[str] = Field(default=None)
    freelance_availability: Optional[str] = Field(default=None)


    # --- Meta ---
    ip_address: Optional[str] = Field(default=None)
    device_finger_print: Optional[str] = Field(default=None)

    # --- Related Models ---
    applications: Optional[List['JobApplication']] = Field(default_factory=list)
    interested_companies: Optional[List['SavedCandidates']] = Field(default_factory=list)
    following_companies: Optional[List['CompanyFollowing']] = Field(default_factory=list)
    resumes_list: Optional[List['JobSeekerCV']] = Field(default_factory=list)
    saved_jobs: Optional[List['SavedJob']] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    # --- Validators ---
    @field_validator("job_titles_of_interest", "industries_of_interest", "locations_of_interest", "freelance_skills", mode="before")
    def strip_empty_list_items(cls, v):
        if isinstance(v, list):
            return [item.strip() for item in v if item.strip()]
        return v

    @field_validator("availability", "freelance_availability")
    def validate_availability(cls, v):
        if v and not v.strip():
            raise ValueError("Availability cannot be blank")
        return v

    @property
    def full_names(self) -> str:
        """full names"""
        return f"{self.first_name.lower()} {self.last_name.lower()}"
    # --- Profile Metrics ---
    @property
    def profile_completion_percentage(self) -> int:
        score, max_score = 0, 0

        def add(condition: bool, weight: float):
            nonlocal score, max_score
            max_score += weight
            if condition:
                score += weight

        # Referral Info (only if referred)
        if self.referrer_id:
            add(True, 2)  # Bonus for being referred

        # Personal Info
        add(bool(self.first_name), 1.5)
        add(bool(self.last_name), 1.5)
        add(bool(self.email), 1.5)
        add(bool(self.bio), 5)
        add(bool(self.profile_image_url), 3)

        # Contact & Location
        add(bool(self.phone), 2)
        add(bool(self.location), 2)
        add(bool(self.linkedin or self.github or self.website), 3)

        # Preferences
        add(bool(self.job_titles_of_interest), 3)
        add(bool(self.industries_of_interest), 3)
        add(bool(self.locations_of_interest), 3)

        # Resume
        add(bool(self.resumes_list), 5)

        # Freelancing
        if self.is_freelancer:
            add(bool(self.freelance_skills), 2)
            add(bool(self.hourly_rate), 1.5)
            add(bool(self.freelance_availability or self.freelance_experience), 1.5)

        percent = int((score / max_score) * 100) if max_score else 0
        return min(percent, 100)

    @property
    def is_profile_complete(self) -> bool:
        return self.profile_completion_percentage >= 80

    @property
    def can_send_job_recommendations(self) -> bool:
        return self.alerts_enabled and self.receive_company_updates and self.is_profile_complete

    # --- Application Helpers ---
    @property
    def total_saved_jobs(self) -> int:
        return len(self.saved_jobs or [])

    @property
    def total_applications(self) -> int:
        return len(self.applications or [])

    def _filter_apps(self, attr: str) -> List['JobApplication']:
        return [app for app in self.applications or [] if getattr(app, attr, False)]

    @property
    def shortlisted_applications(self): return self._filter_apps("is_shortlisted")
    @property
    def under_review_applications(self): return self._filter_apps("is_under_review")
    @property
    def recent_applications(self): return self._filter_apps("is_recent_application")
    @property
    def applications_needing_action(self): return self._filter_apps("needs_action")
    @property
    def successful_applications(self): return self._filter_apps("is_successful")
    @property
    def rejected_applications(self): return self._filter_apps("is_rejected")
    @property
    def active_applications(self): return self._filter_apps("is_active")
    @property
    def ats_optimized_applications(self): return self._filter_apps("is_ats_ready")
    @property
    def ats_risky_applications(self): return self._filter_apps("ats_risk")

    @property
    def applications_with_missing_keywords(self) -> dict[str, list[str]]:
        result = {}
        for app in self.applications or []:
            if app.has_ats_report and app.missing_keywords:
                title = app.job.title if app.job else f"Job {app.job_id}"
                result[title] = app.missing_keywords
        return result

    @property
    def application_stats(self) -> dict:
        stats = {
            "total": len(self.applications or []),
            "applied": 0,
            "under_review": 0,
            "interviewing": 0,
            "shortlisted": 0,
            "offer_extended": 0,
            "hired": 0,
            "rejected": 0,
            "withdrawn": 0
        }
        for app in self.applications or []:
            stage = app.application_stage.lower().replace(" ", "_")
            if stage in stats:
                stats[stage] += 1
        return stats

    @property
    def detect_burst_applications(self) -> bool:
        timestamps = sorted([app.applied_date for app in self.applications or []])
        if len(timestamps) < 10:
            return False
        for i in range(len(timestamps) - 9):
            if (timestamps[i + 9] - timestamps[i]).total_seconds() <= 60:
                return True
        return False

    def detect_multiple_accounts(self) -> bool:
        if not self.ip_address and not self.device_finger_print:
            return False
        controller = get_controller('job_seeker_profile')
        peers = controller.get_jobseekers_by_ip_address(self.ip_address)
        for seeker in peers:
            if seeker.device_finger_print == self.device_finger_print and seeker.user_uid != self.user_uid:
                return True
        return False

    # --- Hints ---
    @property
    def all_hints(self) -> List[Hint]:
        hints: List[Hint] = []

        def hint(msg: str, context: str = "Profile", pri: HintPriority = HintPriority.MEDIUM):
            hints.append(Hint(message=msg, context=context, priority=pri))

        # Profile fields
        if not self.bio: hint(msg="Add a short bio to help employers understand your background.")
        if not self.profile_image_url: hint(msg="Upload a profile picture to increase trust.", pri=HintPriority.LOW)
        if not self.phone: hint(msg="Add your phone number so employers can contact you easily.")
        if not self.location: hint(msg="Specify your current or preferred location.")
        if not (self.linkedin or self.github or self.website):
            hint(msg="Add at least one social link (LinkedIn, GitHub, or personal website).")

        # Job prefs
        if not self.job_titles_of_interest: hint(msg="Add at least one job title you're interested in.",
                                                 pri=HintPriority.HIGH)
        if not self.industries_of_interest: hint(msg="Specify your industries of interest.")
        if not self.locations_of_interest: hint(msg="Add preferred job locations.")
        if not self.resumes_list: hint(msg="Upload your resume to attract more employers.", pri=HintPriority.HIGH)

        # Freelancing
        if self.is_freelancer:
            if not self.freelance_skills: hint(msg="List your freelance skills.", context="Freelancing")
            if not self.hourly_rate: hint(msg="Set your hourly rate.", context="Freelancing")
            if not (self.freelance_availability or self.freelance_experience):
                hint(msg="Add freelance availability or a short summary of your experience.", context="Freelancing")

        # Applications
        for app in self.applications or []:
            job_title = app.job.title if app.job else "Unnamed Job"
            ctx = f"Application: {job_title}"
            if app.ats_risk:
                hint(msg=f"The application to '{job_title}' has a low ATS score.", context=ctx, pri=HintPriority.HIGH)
            if app.missing_keywords:
                keywords = ', '.join(app.missing_keywords[:5]) + ("..." if len(app.missing_keywords) > 5 else "")
                hint(msg=f"Missing important keywords for '{job_title}': {keywords}", context=ctx,
                     pri=HintPriority.HIGH)
            if app.needs_action:
                hint(msg=f"'{job_title}' application is incomplete. Add missing documents.", context=ctx,
                     pri=HintPriority.HIGH)
            if app.is_under_review and app.ats_score and app.ats_score < 70:
                hint(msg=f"'{job_title}' is under review but ATS score is low.", context=ctx, pri=HintPriority.MEDIUM)

        # Engagement
        if not self.saved_jobs: hint(msg="Save jobs you're interested in.", context="Engagement", pri=HintPriority.LOW)
        if not self.applications: hint(msg="You haven’t applied to any jobs yet. Start applying!", context="Engagement",
                                       pri=HintPriority.HIGH)

        return sorted(hints, key=lambda h: h.priority.value)

    @property
    def high_priority_hints(self) -> List[Hint]:
        return [h for h in self.all_hints if h.priority == HintPriority.HIGH]

    @property
    def profile_hints(self) -> List[Hint]:
        return [h for h in self.all_hints if h.context == "Profile"]

    @property
    def job_application_hints(self) -> List[Hint]:
        return [h for h in self.all_hints if h.context.startswith("Application:")]

    # --- Referral Methods ---
    @property
    def active_referrals(self) -> List['JobSeekerReferral']:
        """Get active referrals made by this user."""
        controller = get_controller('job_seeker_profile')
        return controller.get_referrals_by_referrer(self.user_uid, active_only=True)

    @property
    def successful_referrals(self) -> List['JobSeekerReferral']:
        """Get successful referrals made by this user."""
        controller = get_controller('job_seeker_profile')
        return controller.get_referrals_by_referrer(
            self.user_uid,
            status=ReferralStatus.COMPLETED
        )

    @property
    def referral_stats(self) -> dict:
        """Get statistics about referrals."""
        return {
            'total': self.referral_count,
            'active': len(self.active_referrals),
            'successful': len(self.successful_referrals),
            'bonus_earned': self.referral_bonus_earned
        }

    @property
    def trust_score(self) -> float:
        score, max_score = 0, 0

        def add(condition: bool, weight: float):
            nonlocal score, max_score
            max_score += weight
            if condition:
                score += weight

        # Email/Phone Verification
        add(self.verified_email, 2)
        add(self.verified_phone, 1)

        # Socials
        add(bool(self.linkedin), 1)
        add(self.verified_linkedin, 1)

        # GitHub
        add(bool(self.github), 1)
        add(self.verified_github, 1)

        # GitHub trust from AI (scaled 0–1)
        if self.github_verification_score is not None:
            score += self.github_verification_score * 3
            max_score += 3
        else:
            max_score += 3

        # Resume as a trust signal
        add(bool(self.resumes_list), 1)

        return round((score / max_score) * 100, 2) if max_score else 0.0

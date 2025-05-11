import uuid
from datetime import datetime, timedelta, date
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from src.utils import format_reference


class Job(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    search_term: str| None = Field(default=None, alias="category")
    logo_link: str | None = Field(default=None)
    job_link: str
    title: str
    company_name: str
    salary: str
    position: str
    location: str
    updated_time: str
    expires: str
    job_ref: str
    description: str | None = Field(default=None)
    desired_skills: list[str] | None = Field(default=None)


    @field_validator("job_ref", mode="before")
    def format_job_ref(cls, value: str) -> str:
        return format_reference(ref=value)

    @property
    def ats_description(self) -> str:
        """
        A derived field that combines relevant attributes to help power keyword extraction and
        scoring logic for ATS evaluations.
        """
        skill_text = f"Desired skills include: {', '.join(self.desired_skills)}." if self.desired_skills else ""
        summary_parts = [
            f"Job Title: {self.title}",
            f"Company: {self.company_name}",
            f"Location: {self.location}",
            f"Position Type: {self.position}",
            f"Salary: {self.salary}",
            skill_text,
            f"Job Description: {self.description or ''}"
        ]
        return "\n".join([part for part in summary_parts if part.strip()])

    @property
    def apply_url(self) -> str:
        return f"/apply/{self.job_ref}"

    @property
    def slug(self) -> str:
        special_chars = r'[!@#$%^&*()+=\[\]{}|;:",<>/`~]-'
        _title = "".join(char for char in self.title if char not in special_chars)
        _title = f"{_title}_{self.job_ref.replace('-', '_')}"
        return _title.replace(" ", "_").lower().strip()

    @property
    def internal_image_link(self) -> str:
        return f"/media/logos/{self.job_ref}.png"

    @property
    def posted_date(self) -> date:
        try:
            posted_date_str = self.updated_time.split("by")[0].strip()[len("Posted "):]
            return datetime.strptime(posted_date_str, "%d %b %Y").date()
        except ValueError:
            raise ValueError("Invalid posted_date format")

    @property
    def date_expires(self) -> date:
        days_left = int(self.expires.split()[2])
        return self.posted_date + timedelta(days=days_left)

    def disp_dict(self) -> dict[str, str | date | None]:
        return {
            "job_id": self.job_id,
            "search_term": self.search_term,
            "logo_link": self.logo_link,
            "job_link": self.job_link,
            "title": self.title,
            "slug": self.slug,
            "company_name": self.company_name,
            "salary": self.salary,
            "position": self.position,
            "location": self.location,
            "updated_time": self.updated_time,
            "posted_date": self.posted_date,
            "expires": self.expires,
            "job_ref": self.job_ref,
            "description": self.description,
            "desired_skills": self.desired_skills,
            "expiration_date": self.date_expires
        }

class SavedJob(BaseModel):
    user_id: str
    job_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True



class JobApplication(BaseModel):
    application_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    cv_id: Optional[str] = None

    applied_date: datetime = Field(default_factory=datetime.utcnow)

    cover_letter: Optional[str] = None
    status: str = Field(default='pending')
    method: Optional[str] = Field(default='website')
    notes: Optional[str] = None

    expected_salary: Optional[int] = None
    preferred_start_date: Optional[date] = None
    preferred_location: Optional[str] = None
    ats_score: float = Field(default=0)

    class Config:
        orm_mode = True


class ATSReport(BaseModel):
    ats_report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = Field(..., description="ID of the job the report is associated with")
    cv_id: str = Field(..., description="ID of the CV used in the evaluation")
    score: float = Field(..., ge=0, le=100, description="ATS score out of 100")
    matched_keywords: list[str] = Field(default_factory=list, description="List of matched keywords found in CV")
    missing_keywords: list[str] = Field(default_factory=list, description="List of important keywords not found in CV")
    feedback: str = Field(..., description="Feedback based on the ATS evaluation")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the report was generated")




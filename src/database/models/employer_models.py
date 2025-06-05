from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from pydantic import BaseModel, Field, EmailStr, HttpUrl

from src.database.models.company_models import SavedCandidates, Company
from src.database.constants import utc_time


class Employer(BaseModel):
    """
    Complete employer profile for job portal
    All additional fields are optional to allow progressive profile completion
    """
    # Core identification fields
    employer_id: str = Field(default_factory=lambda: str(uuid4()))
    user_uid: str = Field(..., min_length=10, max_length=128, description="Linked Auth0/Firebase UID")
    company_id: str = Field(..., min_length=10, max_length=128, description="The Company ID the Employer represents")

    # Verification & timestamps
    is_verified: bool = Field(default=False, description="Admin-approved status")
    is_admin: bool = Field(default=False, description="Admin-approved status")
    verification_token: Optional[str] = Field(default=None, max_length=255)
    verification_token_expires_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_time)
    updated_at: datetime = Field(default_factory=utc_time)

    # Personal information (all optional)
    full_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Employer's full name"
    )
    job_title: Optional[str] = Field(
        default="Human Resource",
        max_length=100,
        description="Employer's position at the company"
    )
    profile_picture_url: Optional[HttpUrl] = Field(
        default=None,
        description="URL to employer's profile picture"
    )
    bio: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Short professional bio"
    )

    # Contact information (all optional)
    company_email: Optional[EmailStr] = Field(
        default=None,
        description="Professional email address"
    )
    personal_email: Optional[EmailStr] = Field(
        default=None,
        description="Personal email address (optional)"
    )
    phone_number: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Phone number in E.164 format")
    alternate_phone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Alternate phone number"
    )

    # Social profiles (all optional)
    linkedin_url: Optional[HttpUrl] = Field(
        default=None,
        description="LinkedIn profile URL"
    )
    twitter_handle: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Twitter username"
    )

    # Professional details (all optional)
    department: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Department within the company"
    )
    hire_date: Optional[datetime] = Field(
        default=None,
        description="Date joined the company"
    )
    responsibilities: Optional[List[str]] = Field(
        default=None,
        description="List of job responsibilities"
    )
    hiring_authority: Optional[bool] = Field(
        default=False,
        description="Has authority to make hiring decisions"
    )
    signature: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Email signature block"
    )

    company: Optional[Company] = None
    saved_candidates: Optional[List[SavedCandidates]] = Field(default_factory=list)

    @property
    def account_age(self):
        """Calculate the age of the account in days"""
        if self.created_at:
            return (utc_time() - self.created_at).days
        return 0

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    @property
    def is_valid(self) -> bool:
        """Check if employer has minimum required valid fields"""
        return bool(
            self.user_uid.strip() and len(self.user_uid.strip()) >= 10 and
            self.company_id.strip() and len(self.company_id.strip()) >= 10
        )

    def is_token_valid(self, token: str) -> bool:
        """Check if verification token is valid and not expired"""
        return (
                self.verification_token == token and
                self.verification_token_expires_at is not None and
                self.verification_token_expires_at > utc_time()
        )

    def update_timestamp(self):
        """Update the 'updated_at' timestamp"""
        self.updated_at = utc_time()


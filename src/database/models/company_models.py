import re
import uuid
from datetime import date, timezone
from pydantic import BaseModel, Field, field_validator, computed_field, ConfigDict, HttpUrl, EmailStr
from typing import Optional, Any
from datetime import datetime
from enum import Enum

from sqlalchemy.orm import relationship


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
    DOCUMENTS_UPLOADED = "documents_uploaded"
    DOCUMENTS_REJECTED = "documents_rejected"
    DOCUMENTS_APPROVED = "documents_approved"
    CIPC_PENDING = "cipc_pending"
    CIPC_VERIFIED = "cipc_verified"
    CIPC_FAILED = "cipc_failed"
    VERIFIED = "verified"


class Company(BaseModel):
    """Pydantic model for company data"""
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

    # Company Details
    employee_count: Optional[int] = Field(default=None, ge=1)
    founded_year: Optional[int] = Field(default=None, ge=1800, le=datetime.now().year)
    tech_stack: Optional[list[str]] = Field(default=None)

    # Social Media
    linkedin_url: Optional[HttpUrl] = Field(default=None)
    twitter_handle: Optional[str] = Field(default=None, max_length=15)

    # Relationships
    jobs: Optional[list['Job']] = None  # Forward reference
    is_verified: Optional[bool] = Field(default=False)
    time_verification_request_sent : Optional[datetime] = Field(default=None)
    verification_status : str = Field(default=CompanyVerificationStatus.PENDING.value)

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

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

class CompanyVerificationDocument(BaseModel):
    document_type: str  # You can use Enum here for safety
    file_url: HttpUrl
    status: Optional[str] = "pending"
    uploaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

class CompanyCIPC(BaseModel):
    company_name: str
    registration_number: str
    registration_date: Optional[datetime]
    registered_address: Optional[str]
    company_type: Optional[str]  # e.g., "Private Company", "Non-Profit"
    director_names: Optional[list[str]] = []
    status: Optional[str] = "pending"  # pending, verified, failed
    verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

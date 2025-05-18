from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator
from typing import List, Optional
import uuid
import re

class Employer(BaseModel):
    employer_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_uid: str = Field(..., min_length=10, max_length=128, description="Linked Auth0/Firebase UID")
    company_id: str = Field(..., min_length=10, max_length=128, description="The Company ID the Employer represents")

    industry: str = Field("General", min_length=2, max_length=255, description="Primary industry sector")
    website: Optional[HttpUrl] = Field(default=None)
    contact_email: EmailStr
    phone: Optional[str] = Field(None, max_length=20, description="Phone number in international format")

    location: str = Field(..., min_length=2, max_length=255, description="City/Province")
    is_verified: bool = Field(default=False, description="Admin-approved status")
    verification_token: Optional[str] = Field(default=None, max_length=255)
    verification_token_expires_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    @validator("phone")
    def validate_south_african_phone(cls, v):
        if v and not re.match(r"^\+27\d{9}$", v):
            raise ValueError("Phone number must be in valid South African format: +27XXXXXXXXX")
        return v

    @property
    def is_valid(self) -> bool:
        """
        Returns True if the employer instance has the minimum required valid fields.
        """
        has_basic_info = bool(
            self.user_uid and len(self.user_uid.strip()) >= 10 and
            self.company_id and len(self.company_id.strip()) >= 10
        )
        has_contact_info = bool(self.contact_email or self.phone)
        has_location = bool(self.location and len(self.location.strip()) >= 2)

        return has_basic_info and has_contact_info and has_location

    def is_token_valid(self, token: str) -> bool:
        """Checks if a token is valid and not expired."""
        return (
            self.verification_token == token and
            self.verification_token_expires_at is not None and
            self.verification_token_expires_at > datetime.utcnow())

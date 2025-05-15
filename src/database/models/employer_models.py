from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator
from typing import List, Optional
import uuid

class Employer(BaseModel):
    employer_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_uid: str = Field(..., description="Linked Auth0/Firebase UID")
    company_id: str= Field(..., description="The Company ID the Employer represents")
    industry: str = Field("General", description="Primary industry sector")
    website: Optional[HttpUrl] = None
    contact_email: EmailStr
    phone: Optional[str] = Field(None, regex=r"^\+27\d{9}$")  # South Africa format
    location: str = Field(..., description="City/Province")
    is_verified: bool = Field(False, description="Admin-approved status")
    verification_token: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True

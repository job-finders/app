"""
Referral Tracking Models
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ReferralStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    INTERVIEWED = "interviewed"
    HIRED = "hired"
    REJECTED = "rejected"
    COMPLETED = "completed"


class JobReferral(BaseModel):
    """Pydantic model for job referrals"""
    referral_id: str = Field(default_factory=str(uuid.uuid4()))
    job_id: str
    referrer_id: str
    referred_email: str
    referral_code: str
    shared_at: datetime
    application_id: Optional[str] = None
    application_date: Optional[datetime] = None
    status: ReferralStatus = Field(default=ReferralStatus.PENDING)
    bonus_awarded: float = Field(default=0.0)
    bonus_paid: bool = Field(default=False)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True

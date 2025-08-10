"""
Referral Tracking Models
"""

from enum import Enum
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.database import Base
from src.database.models import JobSeekerProfile, JobApplication, Jobs


class ReferralStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    INTERVIEWED = "interviewed"
    HIRED = "hired"
    REJECTED = "rejected"
    COMPLETED = "completed"


class JobReferralORM(Base):
    """Database model for job referrals"""
    __tablename__ = "job_referrals"

    referral_id = Column(PG_UUID(as_uuid=True), primary_key=True)
    job_id = Column(String(36), ForeignKey("jobs.job_id"), nullable=False)
    referrer_id = Column(String(36), ForeignKey("jobseeker_profiles.user_uid"), nullable=False)
    referred_email = Column(String(255), nullable=False)
    referral_code = Column(String(64), unique=True, nullable=False)
    shared_at = Column(DateTime(timezone=True), nullable=False)
    application_id = Column(String(36), ForeignKey("job_applications.application_id"), nullable=True)
    application_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default=ReferralStatus.PENDING)
    bonus_awarded = Column(Float, nullable=False, default=0.0)
    bonus_paid = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship("JobsORM", back_populates="referrals")
    referrer = relationship("JobSeekerProfileORM", back_populates="referrals_made")
    application = relationship("JobApplicationORM", back_populates="referral")


class JobReferral(BaseModel):
    """Pydantic model for job referrals"""
    referral_id: UUID
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

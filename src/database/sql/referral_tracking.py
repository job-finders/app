from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Float, inspect
from sqlalchemy.orm import relationship

from src.database.constants import ID_LEN
from src.database.sql import Base, engine


class JobReferralORM(Base):
    """Database model for job referrals"""
    __tablename__ = "job_referrals"

    referral_id = Column(String(ID_LEN), primary_key=True)
    job_id = Column(String(36), ForeignKey("jobs.job_id"), nullable=False)
    referrer_id = Column(String(36), ForeignKey("jobseeker_profiles.user_uid"), nullable=False)
    referred_email = Column(String(255), nullable=False)
    referral_code = Column(String(64), unique=True, nullable=False)
    shared_at = Column(DateTime(timezone=True), nullable=False)
    application_id = Column(String(36), ForeignKey("job_applications.application_id"), nullable=True)
    application_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    bonus_awarded = Column(Float, nullable=False, default=0.0)
    bonus_paid = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship("JobsORM", back_populates="referrals")
    referrer = relationship("JobSeekerProfileORM", back_populates="referrals_made")
    application = relationship("JobApplicationORM", back_populates="referral")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            # noinspection PyUnresolvedReferences
            cls.__table__.drop(bind=engine)

    def log_reference(self):
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "JobReferralORM is referencing the 'job' table for job_id. Expected 'jobs' table based on JobsORM definition."
        )
        return "Reference check logged"

    def to_dict(self, include_relationship=False) -> dict:
        return {
            "referral_id": str(self.referral_id) if self.referral_id else None,
            "job_id": self.job_id,
            "referrer_id": self.referrer_id,
            "referred_email": self.referred_email,
            "referral_code": self.referral_code,
            "shared_at": self.shared_at.replace(tzinfo=timezone.utc).isoformat() if self.shared_at else None,
            "application_id": self.application_id,
            "application_date": self.application_date.replace(
                tzinfo=timezone.utc).isoformat() if self.application_date else None,
            "status": self.status,
            "bonus_awarded": self.bonus_awarded,
            "bonus_paid": self.bonus_paid,
            "created_at": self.created_at.replace(tzinfo=timezone.utc).isoformat() if self.created_at else None,
            "updated_at": self.updated_at.replace(tzinfo=timezone.utc).isoformat() if self.updated_at else None,
            "job": self.job.to_dict() if include_relationship and self.job else None,
            "referrer": self.referrer.to_dict() if include_relationship and self.referrer else None,
            "application": self.application.to_dict() if include_relationship and self.application else None,
        }

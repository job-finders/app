import uuid
from datetime import timezone

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship

from src.database.constants import NAME_LEN
from src.database.constants import utc_time
from src.database.sql import Base  # Assuming your Base declarative is here


class EmployerORM(Base):
    __tablename__ = "employers"

    # Core identification fields
    employer_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_uid = Column(String(128), nullable=False, unique=True, index=True)
    company_id = Column(String(128), ForeignKey('companies.company_id'), nullable=False, index=True)

    # Verification & timestamps
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    verification_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_time)
    updated_at = Column(DateTime(timezone=True), default=utc_time, onupdate=utc_time)

    # Personal information
    full_name = Column(String(100), nullable=True)
    job_title = Column(String(100), nullable=True, default="Human Resource")
    profile_picture_url = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)  # Using Text for longer content

    # Contact information
    company_email = Column(String(255), nullable=True)
    personal_email = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    alternate_phone = Column(String(20), nullable=True)

    # Social profiles
    linkedin_url = Column(Text, nullable=True)
    twitter_handle = Column(String(50), nullable=True)

    # Professional details
    department = Column(String(100), nullable=True)
    hire_date = Column(DateTime(timezone=True), nullable=True)
    responsibilities = Column(JSON, nullable=True)  # Store as JSON array
    hiring_authority = Column(Boolean, default=False)
    signature = Column(Text, nullable=True)
    ip_address = Column(String(NAME_LEN))



    # Relationship to Company
    company = relationship("CompanyORM", back_populates="employers")
    saved_candidates = relationship("SavedCandidatesORM", back_populates="saved_by_employer")


    def to_dict(self, include_relationships: bool =False) -> dict:
        return {
            # Core identification
            "employer_id": self.employer_id,
            "user_uid": self.user_uid,
            "company_id": self.company_id,

            # Verification & timestamps
            "is_verified": self.is_verified,
            "verification_token": self.verification_token,
            "verification_token_expires_at": self.verification_token_expires_at,
            "created_at": self.created_at.replace(tzinfo=timezone.utc),
            "updated_at": self.updated_at.replace(tzinfo=timezone.utc),

            # Personal information
            "full_name": self.full_name,
            "job_title": self.job_title,
            "profile_picture_url": self.profile_picture_url,
            "bio": self.bio,

            # Contact information
            "company_email": self.company_email,
            "personal_email": self.personal_email,
            "phone_number": self.phone_number,
            "alternate_phone": self.alternate_phone,

            # Social profiles
            "linkedin_url": self.linkedin_url,
            "twitter_handle": self.twitter_handle,

            # Professional details
            "department": self.department,
            "hire_date": self.hire_date.replace(tzinfo=timezone.utc),
            "responsibilities": self.responsibilities,
            "hiring_authority": self.hiring_authority,
            "signature": self.signature,
            "ip_address": self.ip_address,

            # Include nested company data & saved_candidates if loaded
            "company": self.company.to_dict(include_relationships=False) if self.company and include_relationships else None,
            "saved_candidates": [candidate.to_dict(include_relationships=False) for candidate in self.saved_candidates] if include_relationships else []
        }
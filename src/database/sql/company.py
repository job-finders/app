import uuid
from datetime import timezone
from enum import Enum

from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, JSON, DateTime, inspect, Index, Float, Date
from sqlalchemy.orm import relationship

from src.database.constants import ID_LEN, NAME_LEN, utc_time
from src.database.sql import Base, engine


class CompanyORM(Base):
    """Represents an employer/company in the system"""
    __tablename__ = 'companies'

    company_id = Column(String(ID_LEN), primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True)
    description = Column(Text)
    industry = Column(String(100))
    website = Column(String(255))
    logo_url = Column(String(255))

    # Location
    city = Column(String(100))
    province = Column(String(100))
    country = Column(String(100))

    # Contact Info
    contact_email = Column(String(255))
    phone_number = Column(String(20))

    billing_email = Column(String(255), nullable=True)  # Optional billing email for invoices
    send_invoice_emails = Column(Boolean, default=True)
    send_trial_reminders = Column(Boolean, default=True)

    # Company Details
    employee_count = Column(Integer)
    founded_year = Column(Integer)
    tech_stack = Column(JSON)  # ["Python", "AWS", "React"]

    # Social Media
    linkedin_url = Column(String(255), nullable=True)
    twitter_handle = Column(String(50), nullable=True)

    # Audit Fields
    created_at = Column(DateTime(timezone=True), default=utc_time)
    updated_at = Column(DateTime(timezone=True), default=utc_time, onupdate=utc_time)

    # Relationships
    jobs = relationship("JobsORM", back_populates="company")
    employers = relationship("EmployerORM", back_populates="company")
    saved_candidates = relationship("SavedCandidatesORM", back_populates="company")
    # A list of Company Following ORM
    followers = relationship("CompanyFollowingORM", back_populates="followed_company")

    # Verifications
    is_verified = Column(Boolean, default=False)
    time_verification_process_started = Column(DateTime(timezone=True), nullable=True)
    verification_status = Column(String(16), default="pending")
    ip_address = Column(String(NAME_LEN))

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)


    def to_dict(self, include_relationships: bool = False) -> dict:
        """
            time_verification_request_sent = Column(DateTime, nullable=True)
            verification_status = Column(String(16), default="pending")

        :return:
        """
        return {
            "company_id": self.company_id,
            "name": self.name,
            "description": self.description,
            "industry": self.industry,
            "website": self.website,
            "logo_url": self.logo_url,
            "city": self.city,
            "province": self.province,
            "country": self.country,
            "contact_email": self.contact_email,
            "phone_number": self.phone_number,
            "employee_count": self.employee_count,
            "founded_year": self.founded_year,
            "tech_stack": self.tech_stack,
            "linkedin_url": self.linkedin_url,
            "twitter_handle": self.twitter_handle,
            "created_at": self.created_at.replace(tzinfo=timezone.utc).isoformat() if self.created_at else None,
            "updated_at": self.updated_at.replace(tzinfo=timezone.utc).isoformat() if self.updated_at else None,
            "is_verified": self.is_verified,
            "time_verification_process_started": self.time_verification_process_started.replace(
                tzinfo=timezone.utc).isoformat() if self.time_verification_process_started else None,
            "verification_status": self.verification_status,
            "ip_address": self.ip_address,

            "jobs": [job.to_dict(include_relationships=False) for job in self.jobs] if self.jobs and include_relationships else [],
            "saved_candidates": [candidate.to_dict(include_relationships=False) for candidate in self.saved_candidates] if include_relationships else [],
            "employers": [employer.to_dict(include_relationships=False) for employer in self.employers] if include_relationships else [],
            "followers": [follower.to_dict(include_relationships=False) for follower in self.followers] if include_relationships and self.followers else [],

        }


class AIBasedDocumentReviewResultORM(Base):
    """ORM Model to restore the outcome of the AI Based Document Review Process"""
    __tablename__ = "ai_document_review_result"
    review_id = Column(String(ID_LEN) , primary_key=True, index=True, default=lambda : str(uuid.uuid4()))
    document_id = Column(String(ID_LEN), nullable=False, index=True)
    is_document_valid = Column(Boolean, nullable=False)
    reason = Column(Text, nullable=True)
    match_director_name = Column(Boolean, nullable=True)
    match_id_number = Column(Boolean, nullable=True)
    match_cipc_data = Column(Boolean, default=False)
    match_company_profile_data = Column(Boolean, default=False)
    cipc_number_verified_online = Column(Boolean, default=False)
    cipc_number_verification_notes = Column(Text, nullable=True)
    is_suspicious = Column(Boolean, default=False)
    suspicious_notes = Column(Text, nullable=True)

    requires_human_review = Column(Boolean, default=False)
    document_type = Column(String(NAME_LEN), index=True)
    score = Column(Float)
    reviewer_notes = Column(Text, default=None)

    created_at = Column(DateTime(timezone=True), default=utc_time)

    # Relationship back to the document
    document = relationship("CompanyVerificationDocumentORM", back_populates="ai_review")


class CompanyVerificationDocumentORM(Base):
    """
        Company Documents for the Purposes of Verification
    """
    __tablename__ = "company_verification_documents"

    document_id = Column(String(ID_LEN), primary_key=True, index=True)
    company_id = Column(String(ID_LEN), ForeignKey("companies.company_id"), nullable=False)
    ai_review_id = Column(ForeignKey('ai_document_review_result.review_id'), nullable=True)
    document_type = Column(String(36), nullable=False)  # e.g. "CIPC_CERT", "TAX_CLEARANCE", "BEE_CERT"
    file_url = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=utc_time)

    status = Column(String(36), default="pending")  # pending, approved, rejected, human_review
    reviewed_by = Column(String(ID_LEN), ForeignKey("users.uid"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    ai_review = relationship("AIBasedDocumentReviewResultORM", back_populates="document")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self, include_relationships=False):
        return {
            "document_id": self.document_id,
            "company_id": str(self.company_id) if self.company_id else None,
            "ai_review_id": self.ai_review_id,
            "document_type": self.document_type,
            "file_url": self.file_url,
            "uploaded_at": self.uploaded_at.replace(tzinfo=timezone.utc).isoformat() if self.uploaded_at else None,
            "status": self.status,
            "reviewed_by": str(self.reviewed_by) if self.reviewed_by else None,
            "reviewed_at": self.reviewed_at.replace(tzinfo=timezone.utc).isoformat() if self.reviewed_at else None,
            "notes": self.notes,
            "ai_review": self.ai_review.to_dict() if self.ai_review and include_relationships else None
        }


class DirectorDetailsORM(Base):
    """
        used for cipc company registration validation only.
        details of the company director
    """
    __tablename__ = "company_directors"
    cipc_id = Column(String(ID_LEN), ForeignKey("cipc_companies.cipc_id"))
    director_id = Column(String(ID_LEN), primary_key=True, index=True)
    full_names = Column(String(NAME_LEN), index=True)
    id_number = Column(String(ID_LEN), index=True)

    def to_dict(self) -> dict[str, str]:
        """
            :return:
        """
        return dict(
            cipc_id=self.cipc_id,
            director_id=self.director_id,
            full_names=self.full_names,
            id_number=self.id_number
        )

class CompanyCIPCORM(Base):
    """
        Companies with this Information will be indicated by a Blue Tick - Verified Companies
        this class holds company registration details as created by the CIPC
    """
    __tablename__ = "cipc_companies"

    cipc_id = Column(String(ID_LEN), primary_key=True, index=True)
    company_id = Column(String(ID_LEN), ForeignKey('companies.company_id'), index=True)

    company_name = Column(String(NAME_LEN), nullable=False)
    registration_number = Column(String(36), nullable=True)
    registration_date = Column(Date, nullable=True)
    registered_address = Column(String(NAME_LEN))
    company_type = Column(String(36), index=True)


    tax_pin = Column(String(36), nullable=True)
    status = Column(String(36), index=True)
    bee_status = Column(String(36), nullable=True)
    verified_at = Column(DateTime(timezone=True), default=False)

    director_details = relationship("DirectorDetailsORM", uselist=True)

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self, include_relationships=False):
        return {
            "cipc_id": self.cipc_id,
            "company_id": self.company_id,
            "company_name": self.company_name,
            "registration_number": self.registration_number,
            "registration_date": self.registration_date.isoformat() if self.registration_date else None,
            "registered_address": self.registered_address,
            "company_type": self.company_type,
            "status": self.status,
            "tax_pin": self.tax_pin,
            "bee_status": self.bee_status,
            "verified_at": self.verified_at.replace(tzinfo=timezone.utc).isoformat() if self.verified_at else None,
            "director_details": [director.to_dict() for director in
                                 self.director_details] if self.director_details else []
        }
# Add new ORM model for tracking followed companies

# Candidates of Interest
class InterestLevel(Enum):
    LOW = "low"
    INTERESTED = "interested"
    HIGHLY_INTERESTED = "highly_interested"
    TOP_PRIORITY = "top_priority"
    ON_HOLD = "on_hold"

class CompanyFollowingORM(Base):
    """
        Candidates / JobSeekers can follow companies their intent to Effect a
        follow will be recorded in this Model.
        Should be used to send Notifications to relevant people.

    """
    __tablename__ = 'company_following'
    follow_id = Column(String(ID_LEN), primary_key=True, index=True)
    user_id = Column(String(ID_LEN), ForeignKey('jobseeker_profiles.user_uid'), primary_key=True)
    company_id = Column(String(ID_LEN), ForeignKey('companies.company_id'), primary_key=True)
    followed_at = Column(DateTime(timezone=True), default=utc_time)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)

    interest_level = Column(String(36), default=InterestLevel.INTERESTED.value)
    jobseeker_follower = relationship("JobSeekerProfileORM", back_populates="following_companies")
    followed_company = relationship("CompanyORM", back_populates="followers")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self, include_relationships: bool = False) -> dict:
        return {
            "follow_id": self.follow_id,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "followed_at": self.followed_at.replace(tzinfo=timezone.utc).isoformat() if self.followed_at else None,
            "last_notified_at": self.last_notified_at.replace(
                tzinfo=timezone.utc).isoformat() if self.last_notified_at else None,
            "interest_level": self.interest_level,
            "jobseeker_follower": self.jobseeker_follower.to_dict() if include_relationships and self.jobseeker_follower else None,
            "followed_company": self.followed_company.to_dict() if include_relationships else None,
        }


class CandidateStatus(Enum):
    SAVED = "saved"
    REVIEWED = "reviewed"
    CONTACTED = "contacted"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    OFFER_EXTENDED = "offer_extended"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class SavedCandidatesORM(Base):
    """
    Tracks company interest in job seekers with enhanced functionality
    """
    __tablename__ = "saved_candidates"

    saved_id = Column(String(ID_LEN), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    candidate_uid = Column(String(ID_LEN), ForeignKey("jobseeker_profiles.user_uid"), nullable=False, index=True)
    company_id = Column(String(ID_LEN), ForeignKey("companies.company_id"), nullable=False, index=True)
    saved_by = Column(String(ID_LEN), ForeignKey("employers.employer_id"), nullable=False)  # Who saved the candidate

    # Interest tracking
    interest_level = Column(String(20), default=InterestLevel.INTERESTED.value)
    status = Column(String(20), default=CandidateStatus.SAVED.value)

    # Enhanced notes
    notes = Column(Text)
    internal_notes = Column(Text)  # Private company notes
    tags = Column(JSON)  # ["frontend", "senior", "remote-ready"]

    # Contact tracking
    last_contacted_at = Column(DateTime(timezone=True))
    contact_count = Column(Integer, default=0)

    # Timestamps
    saved_at = Column(DateTime(timezone=True), default=utc_time)
    updated_at = Column(DateTime(timezone=True), default=utc_time, onupdate=utc_time)

    # Relationships
    candidate = relationship("JobSeekerProfileORM", back_populates="interested_companies")
    company = relationship("CompanyORM", back_populates="saved_candidates")
    saved_by_employer = relationship("EmployerORM", back_populates="saved_candidates")

    # Constraints
    __table_args__ = (
        Index('ix_company_candidate', 'company_id', 'candidate_uid', unique=True),
        Index('ix_status_updated', 'status', 'updated_at'),
    )

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self, include_internal=False, include_relationships=False):
        data = {
            "saved_id": self.saved_id,
            "candidate_uid": self.candidate_uid,
            "company_id": self.company_id,
            "saved_by": self.saved_by,
            "interest_level": self.interest_level,
            "status": self.status,
            "notes": self.notes,
            "tags": self.tags,
            "last_contacted_at": self.last_contacted_at.replace(
                tzinfo=timezone.utc).isoformat() if self.last_contacted_at else None,
            "contact_count": self.contact_count,
            "saved_at": self.saved_at.replace(tzinfo=timezone.utc).isoformat() if self.saved_at else None,
            "updated_at": self.updated_at.replace(tzinfo=timezone.utc).isoformat() if self.updated_at else None,

            "candidate": self.candidate.to_dict(include_relationships=False) if self.candidate and include_relationships else None,
            "company": self.company.to_dict(include_relationships=False) if self.company and include_relationships else None,
            "saved_by_employer": self.saved_by_employer.to_dict(include_relationships=False) if self.saved_by_employer and include_relationships else None,
        }

        if include_internal:
            data["internal_notes"] = self.internal_notes

        return data

    def update_contact(self):
        """Update contact tracking when company contacts candidate"""
        self.last_contacted_at = utc_time()
        self.contact_count = (self.contact_count or 0) + 1
        self.updated_at = utc_time()

    def update_status(self, new_status: CandidateStatus, notes=None):
        """Update candidate status with optional notes"""
        self.status = new_status.value
        if notes:
            self.internal_notes = f"{self.internal_notes or ''}\n[{utc_time().isoformat()}] Status changed to {new_status.value}: {notes}".strip()
        self.updated_at = utc_time()

    def set_interest_level(self, level: InterestLevel):
        """Update interest level"""
        self.interest_level = level.value
        self.updated_at = utc_time()

    @property
    def interest_level_enum(self) -> InterestLevel:
        """Get interest level as enum"""
        return InterestLevel(self.interest_level)

    @property
    def status_enum(self) -> CandidateStatus:
        """Get status as enum"""
        return CandidateStatus(self.status)

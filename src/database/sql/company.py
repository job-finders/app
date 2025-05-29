import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Date, Float, Integer, Boolean, ForeignKey, JSON, Index, DateTime, inspect, \
    ARRAY, UUID, event
from sqlalchemy.orm import relationship, deferred
from sqlalchemy.ext.hybrid import hybrid_property


from src.database.models.jobs_model import JobApprovalStatusEnum
from src.database.constants import ID_LEN, NAME_LEN
from src.database.sql import Base, engine


class CompanyORM(Base):
    """Represents an employer/company in the system"""
    __tablename__ = 'companies'

    company_id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
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

    # Company Details
    employee_count = Column(Integer)
    founded_year = Column(Integer)
    tech_stack = Column(JSON)  # ["Python", "AWS", "React"]

    # Social Media
    linkedin_url = Column(String(255), nullable=True)
    twitter_handle = Column(String(50), nullable=True)

    # Audit Fields
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    jobs = relationship("JobsORM", back_populates="company", lazy="dynamic")
    employers = relationship("EmployerORM", lazy="dynamic")
    is_verified = Column(Boolean, default=False)
    time_verification_request_sent = Column(DateTime, nullable=True)
    verification_status = Column(String(16), default="pending")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)


    def to_dict(self) -> dict:
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
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_verified": self.is_verified,
            "jobs": [job.to_dict() for job in self.jobs] if hasattr(self, 'jobs') else None,
            "time_verification_request_sent": self.time_verification_request_sent.isoformat(),
            "verification_status": self.verification_status
        }

class CompanyVerificationDocumentORM(Base):
    """
        Company Documents for the Purposes of Verification
    """
    __tablename__ = "company_verification_documents"

    document_id = Column(String(ID_LEN), primary_key=True, index=True)
    company_id = Column(String(ID_LEN), ForeignKey("companies.company_id"), nullable=False)
    document_type = Column(String(36), nullable=False)  # e.g. "CIPC_CERT", "TAX_CLEARANCE", "BEE_CERT"
    file_url = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(36), default="pending")  # pending, approved, rejected
    reviewed_by = Column(String(ID_LEN), ForeignKey("users.uid"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self):
        return {
            "document_id": self.document_id,
            "company_id": str(self.company_id) if self.company_id else None,
            "document_type": self.document_type,
            "file_url": self.file_url,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "status": self.status,
            "reviewed_by": str(self.reviewed_by) if self.reviewed_by else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "notes": self.notes
        }

class CompanyCIPCORM(Base):
    """
        Companies with this Information will be indicated by a Blue Tick - Verified Companies
        this class holds company registration details as created by the CIPC
    """
    __tablename__ = "cipc_companies"

    cipc_id = Column(String(ID_LEN), primary_key=True, index=True)
    company_id = Column(String(ID_LEN), ForeignKey('companies.company_id'), index=True)
    name = Column(String(NAME_LEN), nullable=False)
    registration_number = Column(String(36), nullable=True)
    tax_pin = Column(String(36), nullable=True)
    bee_status = Column(String(36), nullable=True)
    is_verified = Column(Boolean, default=False)

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self):
        return {
            "cipc_id": self.cipc_id,
            "company_id": self.company_id,
            "name": self.name,
            "registration_number": self.registration_number,
            "tax_pin": self.tax_pin,
            "bee_status": self.bee_status,
            "is_verified": self.is_verified
        }
# Add new ORM model for tracking followed companies
class CompanyFollowingORM(Base):
    __tablename__ = 'company_following'
    follow_id = Column(String(ID_LEN), primary_key=True, index=True)
    user_id = Column(String(ID_LEN), ForeignKey('jobseeker_profiles.user_uid'), primary_key=True)
    company_id = Column(String(ID_LEN), ForeignKey('companies.company_id'), primary_key=True)
    followed_at = Column(DateTime, default=datetime.utcnow)
    last_notified_at = Column(DateTime)
    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)


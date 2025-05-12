import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Date, Float, Integer, Boolean, ForeignKey, JSON, Index, DateTime, inspect, \
    ARRAY
from sqlalchemy.orm import relationship, deferred
from sqlalchemy.ext.hybrid import hybrid_property

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
    jobs = relationship("JobsORM", back_populates="company")

    def to_dict(self) -> dict:
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
            "jobs": [job.to_dict() for job in self.jobs] if hasattr(self, 'jobs') else None
        }




class JobsORM(Base):
    """
    JobsORM represents a job posting in the system and contains comprehensive metadata
    about the job, its employer, location, requirements, application process, and internal tracking.

    Fields:

    - job_id: Unique UUID identifier for the job (primary key).
    - job_ref: A human-readable job reference code or ID used for external or internal tracking.
    - external_source: Indicates where the job originated (e.g., 'LinkedIn', 'CompanyWebsite').

    Company Relationships:
    - company_id: Foreign key linking to the associated company.
    - company: SQLAlchemy relationship to the CompanyORM object.

    Job Details:
    - title: Job title.
    - description: Full job description (deferred for performance).
    - position_type: Type of employment (e.g., FULL_TIME, PART_TIME, CONTRACT).
    - remote_policy: Work arrangement policy (e.g., ONSITE, HYBRID, REMOTE).

    Compensation:
    - salary_min / salary_max: Salary range.
    - salary_currency: Currency code (default: "ZAR").
    - salary_confidential: Whether salary details should be hidden from public view.

    Location:
    - city / province / country: Geographical job location.
    - geo_location: Latitude and longitude string (e.g., "−26.2041,28.0473").

    Timeline:
    - posted_at: Date/time the job was published.
    - expires_at: Date/time the job listing will expire.
    - application_deadline: Cutoff date for accepting applications.

    Requirements:
    - experience_level: Desired experience level (ENTRY, MID, SENIOR).
    - education_requirements: JSON structure detailing educational qualifications.
    - required_skills / preferred_skills: Lists of must-have and nice-to-have skills.

    Application Process:
    - application_url: Link to an external application form (if applicable).
    - application_instructions: Additional text-based instructions for applicants.

    Statistics:
    - view_count: Number of times the job has been viewed.
    - application_count: Number of submitted applications.

    Status & Moderation:
    - status: Current state of the job (e.g., active, closed, archived).
    - is_featured: Marks job for prioritized display or promotion.

    Audit Fields:
    - created_at / updated_at: Timestamps for creation and last update.

    Relationships:
    - applications: Related JobApplicationORM entries.
    - saved_jobs: Related SavedJobORM entries (e.g., user bookmarks/favorites).

    Hybrid Properties:
    - is_active: Boolean indicating if the job is currently visible and not expired.
    - location: Readable string combining city, province, and country.

    Indexes:
    - Multi-field indexes improve performance for search, filtering, and sorting operations.

    Utility Methods:
    - generate_slug(): Generates a URL-friendly slug using job title and job_ref.
    - to_dict(): Serializes the job record and related fields to a dictionary.
    """

    __tablename__ = 'jobs'

    # Core Identification
    job_id = Column(String(ID_LEN), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    job_ref = Column(String(NAME_LEN), unique=True, index=True)
    external_source = Column(String(NAME_LEN))  # e.g., "LinkedIn", "CompanyWebsite"

    # Company Relationships
    company_id = Column(String(ID_LEN), ForeignKey('companies.company_id'), index=True)
    company = relationship("CompanyORM", back_populates="jobs")

    # Job Details
    title = Column(String(255), index=True)
    description = deferred(Column(Text))  # Large text, loaded only when needed
    position_type = Column(String(50), index=True)  # FULL_TIME, PART_TIME, CONTRACT
    remote_policy = Column(String(50), index=True)  # ONSITE, HYBRID, REMOTE
    # In Job Details section of JobsORM
    category = Column(String(100), index=True)  # Add this below position_type/remote_policy

    # Compensation
    salary_min = Column(Float)
    salary_max = Column(Float)
    salary_currency = Column(String(3), default="ZAR")
    salary_confidential = Column(Boolean, default=False)

    # Location
    city = Column(String(NAME_LEN), index=True)
    province = Column(String(NAME_LEN), index=True)
    country = Column(String(NAME_LEN), index=True)
    geo_location = Column(String(100))  # "lat,lng" for mapping

    # Timeline
    posted_at = Column(DateTime, default=datetime.now(timezone.utc), index=True)
    expires_at = Column(DateTime, index=True)
    application_deadline = Column(DateTime)

    # Requirements
    experience_level = Column(String(50), index=True)  # ENTRY, MID, SENIOR
    education_requirements = Column(JSON)  # {"degree": "BSc", "field": "Computer Science"}
    required_skills = Column(JSON)  # ["Python", "AWS"]
    preferred_skills = Column(JSON)  # ["Docker", "Kubernetes"]

    # REQUIRED DOCUMENTATIONS AND QUESTIONAIRE
    required_documents = Column(JSON, default=[])
    required_questionnaire = Column(JSON)

    # Application Process
    application_url = Column(String(255))
    application_instructions = Column(Text)

    # Statistics
    view_count = Column(Integer, default=0)
    application_count = Column(Integer, default=0)

    # Status & Moderation
    status = Column(String(20), default='active', index=True)  # active/closed/archived
    is_featured = Column(Boolean, default=False)

    # Audit Fields
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


    # Relationships
    applications = relationship("JobApplicationORM", back_populates="job")
    saved_jobs = relationship("SavedJobORM", back_populates="job")

    # Indexes
    __table_args__ = (
        Index('ix_job_search', 'title', 'city', 'position_type', 'experience_level'),
        Index('ix_salary_range', 'salary_min', 'salary_max'),
        Index('ix_recent_jobs', 'posted_at', 'is_featured'),
    )
    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    @hybrid_property
    def is_active(self):
        return self.status == 'active' and self.expires_at > datetime.now(timezone.utc)

    @hybrid_property
    def location(self):
        return f"{self.city}, {self.province}, {self.country}"

    def generate_slug(self):
        return f"{self.title.lower().replace(' ', '-')}-{self.job_ref}"

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "job_ref": self.job_ref,
            "external_source": self.external_source,
            "company_id": self.company_id,
            "company": self.company.to_dict() if self.company else None,  # assumes CompanyORM has to_dict
            "title": self.title,
            "description": self.description,
            "position_type": self.position_type,
            "category": self.category,
            "remote_policy": self.remote_policy,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_currency": self.salary_currency,
            "salary_confidential": self.salary_confidential,
            "city": self.city,
            "province": self.province,
            "country": self.country,
            "geo_location": self.geo_location,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "application_deadline": self.application_deadline.isoformat() if self.application_deadline else None,
            "experience_level": self.experience_level,
            "education_requirements": self.education_requirements,
            "required_skills": self.required_skills,
            "preferred_skills": self.preferred_skills,
            "required_documents": self.required_documents,
            "required_questionnaire": self.required_questionnaire,
            "application_url": self.application_url,
            "application_instructions": self.application_instructions,
            "view_count": self.view_count,
            "application_count": self.application_count,
            "status": self.status,
            "is_featured": self.is_featured,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "location": self.location,
            "is_active": self.is_active,
            "slug": self.generate_slug()
        }

class SavedJobORM(Base):
    __tablename__ = 'saved_jobs'
    saved_job_id = Column(String(ID_LEN), primary_key=True)
    user_id = Column(String(ID_LEN), index=True)
    job_id = Column(String(ID_LEN), ForeignKey('jobs.job_id'), index=True)

    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    job = relationship("JobsORM", back_populates="saved_jobs")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self) -> dict[str, str]:
        return {
            "saved_job_id" : self.saved_job_id,
            "user_id": self.user_id,
            "job_id": self.job_id,
            "job": self.job.to_dict() if self.job else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class JobApplicationORM(Base):
    __tablename__ = 'job_applications'

    application_id = Column(String(ID_LEN), primary_key=True, index=True)
    user_id = Column(String(ID_LEN), index=True)
    job_id = Column(String(ID_LEN), ForeignKey('jobs.job_id'), index=True)  # Added ForeignKey
    cv_id = Column(String(ID_LEN), index=True)

    # Relationship to Job
    job = relationship("JobsORM", back_populates="applications")  # New relationship
    approval_requests = relationship("JobApprovalRequestORM", back_populates="job")

    # Rest of the existing columns...
    applied_date = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    cover_letter = Column(Text, nullable=True)
    status = Column(String(50), default='pending')
    method = Column(String(50), default='website')
    notes = Column(String(255), nullable=True)

    expected_salary = Column(Integer, nullable=True)
    preferred_start_date = Column(Date, nullable=True)
    preferred_location = Column(String(255), nullable=True)

    required_documents = Column(JSON, default=[])  # ["CV", "ID Copy", "Certificates"]
    questionnaire_answers = Column(JSON)  # {"questions": ["Why this role?", "Availability dat

    application_stage = Column(String(50), default='submitted')  # submitted → qualified → interviewed → hired
    validation_score = Column(Integer)
    missing_requirements = Column(JSON)
    review_summary = Column(Text)

    def to_dict(self) -> dict:
        return {
            "application_id": self.application_id,
            "user_id": self.user_id,
            "job_id": self.job_id,
            "job": self.job.to_dict() if self.job else None,  # Include job details
            "cv_id": self.cv_id,
            "applied_date": self.applied_date.isoformat() if self.applied_date else None,
            "cover_letter": self.cover_letter,
            "status": self.status,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "method": self.method,
            "notes": self.notes,
            "required_documents": self.required_documents,
            "questionnaire_answers": self.questionnaire_answers,
            "expected_salary": self.expected_salary,
            "preferred_start_date": self.preferred_start_date.isoformat() if self.preferred_start_date else None,
            "preferred_location": self.preferred_location,
            "application_stage": self.application_stage,
            "validation_score": self.validation_score,
            "missing_requirements": self.missing_requirements,
            "review_summary": self.review_summary
        }

    # Rest of the existing methods...

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)



class ATSReportORM(Base):
    __tablename__ = "ats_reports"

    ats_report_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, nullable=False)
    cv_id = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    matched_keywords = Column(JSON, nullable=False, default=list)
    missing_keywords = Column(JSON, nullable=False, default=list)
    feedback = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self) -> dict:
        return {
            "ats_report_id": self.ats_report_id,
            "job_id": self.job_id,
            "cv_id": self.cv_id,
            "score": self.score,
            "matched_keywords": self.matched_keywords,
            "missing_keywords": self.missing_keywords,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class JobApprovalRequestORM(Base):
    __tablename__ = 'job_approval_requests'

    request_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey('jobs.job_id'), unique=True)
    token = Column(String(36), unique=True, index=True)
    token_expires = Column(DateTime)
    requested_at = Column(DateTime, default=datetime.now(timezone.utc))
    requested_by = Column(String(36), ForeignKey('companies.company_id'))
    approvers = Column(ARRAY(String))  # List of user IDs
    status = Column(String(20), default='pending')  # pending/approved/rejected/expired
    decision_at = Column(DateTime, onupdate=datetime.now(timezone.utc))
    decision_by = Column(String(36), ForeignKey('users.user_id'))
    feedback = Column(Text)

    job = relationship("JobsORM", back_populates="approval_requests")


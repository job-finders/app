import uuid
from datetime import timezone
from typing import Optional

# install pip install python-slugify
from slugify import slugify
from sqlalchemy import Column, String, Text, Date, Float, Integer, Boolean, ForeignKey, JSON, Index, DateTime, inspect, \
    event, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, deferred

from src.database.constants import ID_LEN, NAME_LEN, utc_time
from src.database.models.jobs_model import JobApprovalStatusEnum, JobStatusEnum
from src.database.sql import Base, engine


class JobCategoryORM(Base):
    __tablename__ = "job_category"
    category_id = Column(String(ID_LEN), primary_key=True, index=True)
    name = Column(String(NAME_LEN), index=True)
    slug = Column(String(NAME_LEN), nullable=True)
    description = Column(Text, nullable=True)
    seo_description = Column(String(250), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_time)
    updated_at = Column(DateTime(timezone=True), default=utc_time, onupdate=utc_time)

    canonical_skills = Column(JSON)
    skill_synonyms = Column(JSON)
    jobs = relationship("JobsORM", back_populates="category")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    @hybrid_property
    def total_jobs(self) -> int:
        """Total jobs in this category"""
        return len(self.jobs)

    @hybrid_property
    def active_jobs(self) -> int:
        """Active jobs (not expired)"""
        now = utc_time()
        return sum(
            1 for job in self.jobs
            if job.status == 'active' and job.expires_at and job.expires_at > now
        )

    @hybrid_property
    def featured_jobs(self) -> int:
        """Featured jobs in this category"""
        return sum(1 for job in self.jobs if job.is_featured)

    @hybrid_property
    def avg_salary_min(self) -> Optional[float]:
        """Average minimum salary"""
        min_salaries = [job.salary_min for job in self.jobs if job.salary_min is not None]
        return sum(min_salaries) / len(min_salaries) if min_salaries else None

    @hybrid_property
    def avg_salary_max(self) -> Optional[float]:
        """Average maximum salary"""
        max_salaries = [job.salary_max for job in self.jobs if job.salary_max is not None]
        return sum(max_salaries) / len(max_salaries) if max_salaries else None

    def to_dict(self, include_jobs=False):
        """Convert to dictionary with computed statistics"""
        data = {
            "category_id": self.category_id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "seo_description": self.seo_description,
            "created_at": self.created_at.replace(tzinfo=timezone.utc).isoformat() if self.created_at else None,
            "updated_at": self.updated_at.replace(tzinfo=timezone.utc).isoformat() if self.updated_at else None,
            # computed statistics
            "total_jobs": self.total_jobs,
            "active_jobs": self.active_jobs,
            "featured_jobs": self.featured_jobs,
            "avg_salary_min": self.avg_salary_min,
            "avg_salary_max": self.avg_salary_max,
            # optional JSON fields
            "canonical_skills": self.canonical_skills or [],
            "skill_synonyms": self.skill_synonyms or {},
        }

        if include_jobs:
            data["jobs"] = [job.to_dict() for job in self.jobs]

        return data


class JobsORM(Base):
    """
    JobsORM represents a job posting in the system and contains comprehensive metadata
    about the job, its employer, location, requirements, application process, and internal tracking.
    """

    __tablename__ = 'jobs'

    # Core Identification
    job_id = Column(String(ID_LEN), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    category_id = Column(String(ID_LEN), ForeignKey('job_category.category_id'), index=True)
    job_ref = Column(String(NAME_LEN), unique=True, index=True)
    slug = Column(String(NAME_LEN), unique=True, index=True)
    external_source = Column(String(NAME_LEN))

    # Company Relationships
    employer_id = Column(String(ID_LEN), ForeignKey('employers.employer_id'), index=True)
    company_id = Column(String(ID_LEN), ForeignKey('companies.company_id'), index=True)

    # Job Details
    title = Column(String(255), index=True)
    description = deferred(Column(Text))
    position_type = Column(String(50), index=True)
    remote_policy = Column(String(50), index=True)

    # Compensation
    salary_min = Column(Float)
    salary_max = Column(Float)
    salary_currency = Column(String(3), default="ZAR")
    salary_confidential = Column(Boolean, default=False)

    # Location
    city = Column(String(NAME_LEN), index=True)
    province = Column(String(NAME_LEN), index=True)
    country = Column(String(NAME_LEN), index=True)
    geo_location = Column(String(100))

    # Timeline
    posted_at = Column(DateTime(timezone=True), default=utc_time, index=True)
    expires_at = Column(DateTime(timezone=True), index=True)
    application_deadline = Column(DateTime(timezone=True))

    # Requirements
    experience_level = Column(String(50), index=True)
    education_requirements = Column(JSON, default={})
    required_skills = Column(JSON, default=[])
    preferred_skills = Column(JSON, default=[])

    # Required documentations and questionnaire
    required_documents = Column(JSON, default=[])
    required_questionnaire = Column(JSON, default=[])

    # Application Process
    application_url = Column(String(255))
    application_instructions = Column(Text)

    # Statistics
    view_count = Column(Integer, default=0)
    application_count = Column(Integer, default=0)

    # Status & Moderation
    status = Column(String(20), default='active', index=True)
    is_featured = Column(Boolean, default=False)

    # Audit Fields
    created_at = Column(DateTime(timezone=True), default=utc_time)
    updated_at = Column(DateTime(timezone=True), default=utc_time, onupdate=utc_time)

    # Summary and SEO
    summary = Column(Text, nullable=True)
    seo_description = Column(Text, nullable=True)

    # Relationships
    company = relationship("CompanyORM", back_populates="jobs")
    category = relationship("JobCategoryORM", back_populates="jobs")
    applications = relationship("JobApplicationORM", back_populates="job")
    interested_jobseekers = relationship("SavedJobORM", back_populates="job")
    approval_request = relationship("JobApprovalRequestORM", uselist=False, back_populates="job")
    version_history = relationship("JobVersionHistoryORM")
    ats_reports = relationship("ATSReportORM", back_populates="job")
    likes = relationship("JobLikeORM", back_populates="job")
    shares = relationship("JobShareORM", back_populates="job")
    referrals = relationship("JobReferralORM", back_populates="job")

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
        return (self.status == JobStatusEnum.ACTIVE.value and
                self.expires_at and self.expires_at > utc_time())

    @hybrid_property
    def location(self):
        parts = [self.city, self.province, self.country]
        return ", ".join(part for part in parts if part)

    def generate_slug(self):
        return f"{self.title.lower().replace(' ', '-')}-{self.job_ref}"

    def to_dict(self, include_relationship=False) -> dict:
        return {
            "job_id": self.job_id,
            "job_ref": self.job_ref,
            "slug": self.slug,
            "external_source": self.external_source,
            "company_id": self.company_id,
            "title": self.title,
            "description": self.description,
            "summary": self.summary,
            "seo_description": self.seo_description,
            "category_id": self.category_id,
            "position_type": self.position_type,
            "remote_policy": self.remote_policy,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_currency": self.salary_currency,
            "salary_confidential": self.salary_confidential,
            "city": self.city,
            "province": self.province,
            "country": self.country,
            "geo_location": self.geo_location,
            "posted_at": self.posted_at.replace(tzinfo=timezone.utc).isoformat() if self.posted_at else None,
            "expires_at": self.expires_at.replace(tzinfo=timezone.utc).isoformat() if self.expires_at else None,
            "application_deadline": self.application_deadline.replace(
                tzinfo=timezone.utc).isoformat() if self.application_deadline else None,
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
            "created_at": self.created_at.replace(tzinfo=timezone.utc).isoformat() if self.created_at else None,
            "updated_at": self.updated_at.replace(tzinfo=timezone.utc).isoformat() if self.updated_at else None,
            "location": self.location,
            "is_active": self.is_active,
            "category": self.category.to_dict(include_jobs=False) if self.category and include_relationship else None,
            "company": self.company.to_dict() if self.company and include_relationship else None,
            "applications": [application.to_dict() for application in self.applications] if include_relationship else [],
            "interested_jobseekers": [_interest.to_dict() for _interest in
                                      self.interested_jobseekers] if include_relationship else [],
            "likes": [like.to_dict() for like in self.likes] if include_relationship else [],
            "shares": [share.to_dict() for share in self.shares] if include_relationship else [],
            "like_count": len(self.likes) if self.likes else 0,
            "share_count": len(self.shares) if self.shares else 0,
            "referrals": [referral.to_dict() for referral in self.referrals if referral] if include_relationship else []
        }

    def generate_and_set_slug(self):
        """Generate and set the slug based on title and job_ref if not already set."""
        if not self.slug and self.title and self.job_ref:
            base_slug = slugify(self.title)
            self.slug = f"{base_slug}-{self.job_ref.lower()}"


@event.listens_for(JobsORM, 'before_insert')
@event.listens_for(JobsORM, 'before_update')
def before_save_generate_slug(mapper, connection, target):
    target.generate_and_set_slug()


class JobVersionHistoryORM(Base):
    __tablename__ = 'job_version_history'
    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(ID_LEN), ForeignKey('jobs.job_id'), index=True)
    version = Column(Integer)
    changes = Column(JSON)
    modified_by = Column(String(ID_LEN), ForeignKey('users.uid'))
    modified_at = Column(DateTime(timezone=True), default=utc_time)

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)


class SavedJobORM(Base):
    """JobSeekers will save jobs they are interested in for later reference."""
    
    __tablename__ = 'saved_jobs'
    saved_job_id = Column(String(ID_LEN), primary_key=True, index=True)
    user_id = Column(String(ID_LEN), ForeignKey('jobseeker_profiles.user_uid'), index=True)
    job_id = Column(String(ID_LEN), ForeignKey('jobs.job_id'), index=True)
    created_at = Column(DateTime(timezone=True), default=utc_time)

    job = relationship("JobsORM", back_populates="interested_jobseekers")
    jobseeker_profile = relationship("JobSeekerProfileORM", back_populates="saved_jobs")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self, include_relationship=False) -> dict:
        return {
            "saved_job_id": self.saved_job_id,
            "user_id": self.user_id,
            "job_id": self.job_id,
            "created_at": self.created_at.replace(tzinfo=timezone.utc).isoformat() if self.created_at else None,
            "job": self.job.to_dict() if self.job and include_relationship else None,
            "jobseeker_profile": self.jobseeker_profile.to_dict() if self.jobseeker_profile and include_relationship else None
        }


class JobApplicationORM(Base):
    __tablename__ = 'job_applications'

    application_id = Column(String(ID_LEN), primary_key=True, index=True)
    user_id = Column(String(ID_LEN), ForeignKey('jobseeker_profiles.user_uid'), index=True)
    job_id = Column(String(ID_LEN), ForeignKey('jobs.job_id'), index=True)
    ats_report_id = Column(String(ID_LEN), ForeignKey('ats_reports.ats_report_id'), nullable=True, index=True)
    cv_id = Column(String(ID_LEN), index=True)

    jobseeker_profile = relationship("JobSeekerProfileORM", back_populates="applications")
    applied_date = Column(DateTime(timezone=True), default=utc_time)
    updated_at = Column(DateTime(timezone=True), default=utc_time, onupdate=utc_time)

    cover_letter = Column(Text, nullable=True)
    method = Column(String(50), default='website')
    notes = Column(String(255), nullable=True)

    expected_salary = Column(Integer, nullable=True)
    preferred_start_date = Column(Date, nullable=True)
    preferred_location = Column(String(255), nullable=True)

    required_documents = Column(JSON, default=[])
    questionnaire_answers = Column(JSON, default=[])
    last_application_stage = Column(String(50), nullable=True)
    application_stage = Column(String(50))
    validation_score = Column(Integer)
    missing_requirements = Column(JSON)
    review_summary = Column(Text)

    ats_report = relationship("ATSReportORM", uselist=False, back_populates="job_application")
    job = relationship("JobsORM", back_populates="applications")
    referral = relationship("JobReferralORM", back_populates="application", uselist=False)

    def to_dict(self, include_relationships=False) -> dict:
        return {
            "application_id": self.application_id,
            "user_id": self.user_id,
            "job_id": self.job_id,
            "job": self.job.to_dict() if self.job else None,
            "ats_report_id": self.ats_report_id,
            "cv_id": self.cv_id,
            "applied_date": self.applied_date.replace(tzinfo=timezone.utc).isoformat() if self.applied_date else None,
            "cover_letter": self.cover_letter,
            "updated_at": self.updated_at.replace(tzinfo=timezone.utc).isoformat() if self.updated_at else None,
            "method": self.method,
            "notes": self.notes,
            "required_documents": self.required_documents,
            "questionnaire_answers": self.questionnaire_answers,
            "expected_salary": self.expected_salary,
            "preferred_start_date": self.preferred_start_date if self.preferred_start_date else None,
            "preferred_location": self.preferred_location,
            "last_application_stage": self.last_application_stage,
            "application_stage": self.application_stage,
            "validation_score": self.validation_score,
            "missing_requirements": self.missing_requirements,
            "review_summary": self.review_summary,
            "jobseeker_profile": self.jobseeker_profile.to_dict() if self.jobseeker_profile and include_relationships else None,
            "ats_report": self.ats_report.to_dict() if self.ats_report and include_relationships else None,
            "referral": self.referral.to_dict() if self.referral and include_relationships else None
        }

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

    ats_report_id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(ID_LEN), ForeignKey('jobs.job_id'), unique=False, nullable=False, index=True)
    cv_id = Column(String(ID_LEN), unique=False, nullable=False, index=True)
    score = Column(Integer, nullable=False)
    matched_keywords = Column(JSON, nullable=False, default=list)
    missing_keywords = Column(JSON, nullable=False, default=list)
    feedback = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_time)

    job_application = relationship("JobApplicationORM", back_populates="ats_report")
    job = relationship("JobsORM", back_populates="ats_reports")

    __table_args__ = (
        UniqueConstraint('job_id', 'cv_id', name='uq_job_cv_pair'),
    )

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self, include_relationships: bool = False) -> dict:
        return {
            "ats_report_id": self.ats_report_id,
            "job_id": self.job_id,
            "cv_id": self.cv_id,
            "score": self.score,
            "matched_keywords": self.matched_keywords,
            "missing_keywords": self.missing_keywords,
            "feedback": self.feedback,
            "created_at": self.created_at.replace(tzinfo=timezone.utc).isoformat() if self.created_at else None,
            "job_application": self.job_application if include_relationships and self.job_application else None
        }


class JobApprovalRequestORM(Base):
    """
    SQLAlchemy ORM model representing job approval requests submitted by companies.

    This table tracks the approval lifecycle of jobs that require administrative or delegated approval
    before being listed publicly. Each request is tied to a specific job and includes metadata about
    the request such as token expiration, approvers, and decision status.
    """

    __tablename__ = 'job_approval_requests'

    request_id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(ID_LEN), ForeignKey('jobs.job_id'), unique=True)
    token = Column(String(36), unique=True, index=True)
    token_expires = Column(DateTime(timezone=True))
    requested_at = Column(DateTime(timezone=True), default=utc_time)
    requested_by = Column(String(ID_LEN), ForeignKey('companies.company_id'))
    approvers = Column(JSON, default=[])
    status = Column(String(20), default=JobApprovalStatusEnum.PENDING.value)
    decision_at = Column(DateTime(timezone=True), onupdate=utc_time)
    decision_by = Column(String(ID_LEN), ForeignKey('users.uid'))
    feedback = Column(Text)

    job = relationship("JobsORM", back_populates="approval_request")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self, include_relationship=False) -> dict:
        return {
            "request_id": self.request_id,
            "job_id": self.job_id,
            "token": self.token,
            "token_expires": self.token_expires.replace(tzinfo=timezone.utc).isoformat() if self.token_expires else None,
            "requested_at": self.requested_at.replace(tzinfo=timezone.utc).isoformat() if self.requested_at else None,
            "requested_by": self.requested_by,
            "approvers": self.approvers,
            "status": self.status,
            "decision_at": self.decision_at.replace(tzinfo=timezone.utc).isoformat() if self.decision_at else None,
            "decision_by": self.decision_by,
            "feedback": self.feedback,
            "job": self.job.to_dict() if include_relationship and self.job else None
        }


class ApplicationDashboardORM(Base):
    """Cached dashboard data for quick access"""
    __tablename__ = "application_dashboards"

    dashboard_id = Column(String(ID_LEN), primary_key=True)
    company_id = Column(String(ID_LEN), ForeignKey("companies.company_id"))
    snapshot_date = Column(DateTime(timezone=True), default=utc_time)
    data = Column(JSON)
    metrics = Column(JSON)

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
            "dashboard_id": self.dashboard_id,
            "company_id": self.company_id,
            "snapshot_date": self.snapshot_date.replace(tzinfo=timezone.utc).isoformat() if self.snapshot_date else None,
            "data": self.data,
            "metrics": self.metrics
        }


class TalentPoolReportORM(Base):
    """Historical talent pool reports"""
    __tablename__ = "talent_pool_reports"

    report_id = Column(String(ID_LEN), primary_key=True)
    company_id = Column(String(ID_LEN), ForeignKey("companies.company_id"))
    generated_at = Column(DateTime(timezone=True), default=utc_time)
    report_data = Column(JSON)
    insights = Column(JSON)

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
            "report_id": self.report_id,
            "company_id": self.company_id,
            "generated_at": self.generated_at.replace(tzinfo=timezone.utc).isoformat() if self.generated_at else None,
            "report_data": self.report_data,
            "insights": self.insights
        }


class JobLikeORM(Base):
    """
    JobLikeORM represents user likes on job postings.
    Tracks which users have liked which jobs for engagement analytics.
    """
    __tablename__ = 'job_likes'

    like_id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(ID_LEN), ForeignKey('jobseeker_profiles.user_uid'), nullable=False, index=True)
    job_id = Column(String(ID_LEN), ForeignKey('jobs.job_id'), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_time, index=True)

    # Relationships
    job = relationship("JobsORM", back_populates="likes")
    jobseeker_profile = relationship("JobSeekerProfileORM", back_populates="liked_jobs")

    # Unique constraint to prevent duplicate likes
    __table_args__ = (
        UniqueConstraint('user_id', 'job_id', name='unique_user_job_like'),
        Index('ix_job_likes_user_job', 'user_id', 'job_id'),
        Index('ix_job_likes_job_created', 'job_id', 'created_at'),
    )

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self, include_relationships=False) -> dict:
        return {
            "like_id": self.like_id,
            "user_id": self.user_id,
            "job_id": self.job_id,
            "created_at": self.created_at.replace(tzinfo=timezone.utc).isoformat() if self.created_at else None,
            "job": self.job.to_dict() if include_relationship and self.job else None,
            "jobseeker_profile": self.jobseeker_profile.to_dict() if include_relationship and self.jobseeker_profile else None
        }

    @property
    def is_recent(self) -> bool:
        """Check if this like was created within the last 24 hours"""
        if not self.created_at:
            return False
        return (utc_time() - self.created_at).total_seconds() < 86400


class JobShareORM(Base):
    """
    JobShareORM tracks job sharing activities across different platforms.
    Supports both authenticated and anonymous sharing with referral tracking.
    """
    __tablename__ = 'job_shares'

    share_id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(ID_LEN), ForeignKey('jobseeker_profiles.user_uid'), nullable=True,
                     index=True)  # Nullable for anonymous shares
    job_id = Column(String(ID_LEN), ForeignKey('jobs.job_id'), nullable=False, index=True)
    share_method = Column(String(50), nullable=False,
                          index=True)  # email, linkedin, twitter, facebook, whatsapp, copy_link
    shared_at = Column(DateTime(timezone=True), default=utc_time, index=True)
    referral_code = Column(String(20), nullable=True, index=True)  # For tracking conversions

    # Relationships
    job = relationship("JobsORM", back_populates="shares")
    jobseeker_profile = relationship("JobSeekerProfileORM", back_populates="shared_jobs")

    # Indexes for performance
    __table_args__ = (
        Index('ix_job_shares_job_method', 'job_id', 'share_method'),
        Index('ix_job_shares_user_shared', 'user_id', 'shared_at'),
        Index('ix_job_shares_referral', 'referral_code'),
    )

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self, include_relationship=False) -> dict:
        return {
            "share_id": self.share_id,
            "user_id": self.user_id,
            "job_id": self.job_id,
            "share_method": self.share_method,
            "shared_at": self.shared_at.replace(tzinfo=timezone.utc).isoformat() if self.shared_at else None,
            "referral_code": self.referral_code,
            "job": self.job.to_dict() if include_relationship and self.job else None,
            "jobseeker_profile": self.jobseeker_profile.to_dict() if include_relationship and self.jobseeker_profile else None
        }



    @property
    def is_anonymous(self) -> bool:
        """Check if this is an anonymous share"""
        return self.user_id is None

    @property
    def is_social_media(self) -> bool:
        """Check if this share was via social media"""
        social_methods = ['linkedin', 'twitter', 'facebook']
        return self.share_method in social_methods

    @classmethod
    def generate_referral_code(cls, user_id: str, job_id: str) -> str:
        """Generate a unique referral code for tracking"""
        import hashlib
        combined = f"{user_id}:{job_id}:{utc_time().timestamp()}"
        return hashlib.md5(combined.encode()).hexdigest()[:8].upper()


class ImportJobBatchORM(Base):
    """Track bulk import operations"""
    __tablename__ = "import_job_batches"

    batch_id = Column(String(ID_LEN), primary_key=True)
    company_id = Column(String(ID_LEN), ForeignKey("companies.company_id"))
    started_at = Column(DateTime(timezone=True), default=utc_time)
    completed_at = Column(DateTime(timezone=True), default=utc_time, onupdate=utc_time)
    status = Column(String(20))
    summary = Column(JSON)

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
            "batch_id": self.batch_id,
            "company_id": self.company_id,
            "started_at": self.started_at.replace(tzinfo=timezone.utc).isoformat() if self.started_at else None,
            "completed_at": self.completed_at.replace(tzinfo=timezone.utc).isoformat() if self.completed_at else None,
            "status": self.status,
            "summary": self.summary
        }
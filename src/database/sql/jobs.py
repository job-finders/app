import uuid
from datetime import datetime

from sqlalchemy import Column, String, Date, Text, inspect, DateTime, UniqueConstraint, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship

from src.database.constants import NAME_LEN, ID_LEN
from src.database.sql import Base, engine


class JobsORM(Base):
    __tablename__ = 'jobfinders_jobs'

    job_id = Column(String(ID_LEN), primary_key=True, index=True)
    search_term = Column(String(NAME_LEN), index=True)
    logo_link = Column(Text, nullable=True)
    job_link = Column(Text)
    title = Column(Text)
    company_name = Column(String(NAME_LEN))
    salary = Column(String(NAME_LEN))
    position = Column(String(NAME_LEN))
    location = Column(String(NAME_LEN))
    posted_date = Column(Date)
    updated_time = Column(String(NAME_LEN))
    expires = Column(String(NAME_LEN))
    job_ref = Column(String(NAME_LEN), unique=True, index=True)
    description = Column(Text, nullable=True)
    desired_skills = Column(Text, nullable=True)
    expiration_date = Column(Date)

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def __init__(self, **kwargs):
        # Initialize the ORM instance based on the Pydantic model
        super().__init__(
            job_id=kwargs.get('job_id', str(uuid.uuid4())),
            search_term=kwargs['search_term'],
            logo_link=kwargs['logo_link'],
            job_link=kwargs['job_link'],
            title=kwargs['title'],
            company_name=kwargs['company_name'],
            salary=kwargs['salary'],
            position=kwargs['position'],
            location=kwargs['location'],
            posted_date=kwargs['posted_date'],
            updated_time=kwargs['updated_time'],
            expires=kwargs['expires'],
            job_ref=kwargs['job_ref'],
            description=kwargs['description'],
            desired_skills=kwargs['desired_skills'],
            expiration_date=self.expiration_date
        )

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "search_term": self.search_term,
            "logo_link": self.logo_link,
            "job_link": self.job_link,
            "title": self.title,
            "company_name": self.company_name,
            "salary": self.salary,
            "position": self.position,
            "location": self.location,
            "posted_date": self.posted_date.isoformat() if self.posted_date else None,
            "updated_time": self.updated_time,
            "expires": self.expires,
            "job_ref": self.job_ref,
            "description": self.description,
            "desired_skills": self.desired_skills,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None
        }

class SavedJobORM(Base):
    __tablename__ = 'saved_jobs'

    user_id = Column(String(ID_LEN), primary_key=True)
    job_id = Column(String(ID_LEN), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

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
            "user_id": self.user_id,
            "job_id": self.job_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class JobApplicationORM(Base):
    __tablename__ = 'job_applications'

    application_id = Column(String(ID_LEN), primary_key=True, index=True)
    user_id = Column(String(ID_LEN), index=True)
    job_id = Column(String(ID_LEN), index=True)
    cv_id = Column(String(ID_LEN), index=True)

    applied_date = Column(DateTime, default=datetime.utcnow)

    cover_letter = Column(Text, nullable=True)
    status = Column(String(50), default='pending')  # pending, accepted, rejected, withdrawn
    updated_at = Column(DateTime, nullable=True)
    method = Column(String(50), default='website')  # e.g., "website", "email"
    notes = Column(String(255), nullable=True)

    expected_salary = Column(Integer, nullable=True)
    preferred_start_date = Column(Date, nullable=True)
    preferred_location = Column(String(255), nullable=True)

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def __init__(self, **kwargs):
        super().__init__(
            application_id=kwargs.get('application_id', str(uuid.uuid4())),
            user_id=kwargs['user_id'],
            job_id=kwargs['job_id'],
            cv_id=kwargs.get('cv_id'),
            applied_date=kwargs.get('applied_date', datetime.utcnow()),
            cover_letter=kwargs.get('cover_letter'),
            status=kwargs.get('status', 'pending'),
            updated_at = kwargs.get('updated_at'),
            method=kwargs.get('method', 'website'),
            notes=kwargs.get('notes'),
            expected_salary=kwargs.get('expected_salary'),
            preferred_start_date=kwargs.get('preferred_start_date'),
            preferred_location=kwargs.get('preferred_location'),
        )

    def to_dict(self) -> dict:
        return {
            "application_id": self.application_id,
            "user_id": self.user_id,
            "job_id": self.job_id,
            "cv_id": self.cv_id,
            "applied_date": self.applied_date.isoformat() if self.applied_date else None,
            "cover_letter": self.cover_letter,
            "status": self.status,
            "updated_at" : self.updated_at.isoformat() if self.updated_at else None,
            "method": self.method,
            "notes": self.notes,
            "expected_salary": self.expected_salary,
            "preferred_start_date": self.preferred_start_date.isoformat() if self.preferred_start_date else None,
            "preferred_location": self.preferred_location,
        }


class ATSReportORM(Base):
    __tablename__ = "ats_reports"

    ats_report_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, nullable=False)
    cv_id = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    matched_keywords = Column(JSON, nullable=False, default=list)
    missing_keywords = Column(JSON, nullable=False, default=list)
    feedback = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


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

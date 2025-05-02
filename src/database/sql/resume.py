import uuid
from sqlalchemy import Column, String, Date, DateTime, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.database.constants import ID_LEN, NAME_LEN
from src.database.sql import Base, engine
from sqlalchemy import inspect
from datetime import datetime


class JobSeekerCVORM(Base):
    __tablename__ = 'jobseeker_cvs'

    cv_id = Column(String(36), primary_key=True, unique=True, index=True)
    user_uid = Column(String(36), nullable=False, index=True)
    professional_title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    skills = Column(JSONB, default=[])
    portfolio_links = Column(JSONB, default=[])
    resume_file_url = Column(String(255), nullable=True)
    profile_image_url = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)  # Added location
    phone = Column(String(255), nullable=True)  # Added phone
    website = Column(String(255), nullable=True)  # Added website
    linkedin = Column(String(255), nullable=True)  # Added linkedin
    github = Column(String(255), nullable=True)  # Added github
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships (if needed)
    experience = relationship("ExperienceORM", back_populates="cv", cascade="all, delete-orphan")
    education = relationship("EducationORM", back_populates="cv", cascade="all, delete-orphan")
    certifications = relationship("CertificationORM", back_populates="cv", cascade="all, delete-orphan")
    languages = relationship("LanguageORM", back_populates="cv", cascade="all, delete-orphan")
    projects = relationship("ProjectORM", back_populates="cv", cascade="all, delete-orphan")
    publications = relationship("PublicationORM", back_populates="cv", cascade="all, delete-orphan")
    awards = relationship("AwardORM", back_populates="cv", cascade="all, delete-orphan")
    custom_sections = relationship("CustomSectionORM", back_populates="cv", cascade="all, delete-orphan")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            cls.__table__.create(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self) -> dict:
        return {
            "cv_id": self.cv_id,
            "user_uid": self.user_uid,
            "professional_title": self.professional_title,
            "summary": self.summary,
            "skills": self.skills,
            "portfolio_links": self.portfolio_links,
            "resume_file_url": self.resume_file_url,
            "profile_image_url": self.profile_image_url,
            "location": self.location,
            "phone": self.phone,
            "website": self.website,
            "linkedin": self.linkedin,
            "github": self.github,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class ExperienceORM(Base):
    __tablename__ = 'cv_experience'

    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = Column(String(ID_LEN), ForeignKey('jobseeker_cvs.cv_id'), nullable=False, index=True)
    job_title = Column(String(NAME_LEN), nullable=False)
    company = Column(String(NAME_LEN), nullable=False)
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)
    location = Column(String(NAME_LEN), nullable=True)
    description = Column(Text, nullable=True)

    cv = relationship("JobSeekerCVORM", back_populates="experience")


class EducationORM(Base):
    __tablename__ = 'cv_education'

    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = Column(String(ID_LEN), ForeignKey('jobseeker_cvs.cv_id'), index=True)
    institution = Column(String(NAME_LEN))
    qualification = Column(String(NAME_LEN))
    field_of_study = Column(String(NAME_LEN))
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)
    description = Column(Text)

    cv = relationship("JobSeekerCVORM", back_populates="education")


class CertificationORM(Base):
    __tablename__ = 'cv_certifications'

    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = Column(String(ID_LEN), ForeignKey('jobseeker_cvs.cv_id'), index=True)
    name = Column(String(NAME_LEN))
    issuer = Column(String(NAME_LEN))
    issue_date = Column(Date)
    expiry_date = Column(Date, nullable=True)
    credential_url = Column(String(255), nullable=True)

    cv = relationship("JobSeekerCVORM", back_populates="certifications")


class LanguageORM(Base):
    __tablename__ = 'cv_languages'

    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = Column(String(ID_LEN), ForeignKey('jobseeker_cvs.cv_id'), index=True)
    name = Column(String(NAME_LEN))
    proficiency = Column(String(NAME_LEN))

    cv = relationship("JobSeekerCVORM", back_populates="languages")


class ProjectORM(Base):
    __tablename__ = 'cv_projects'

    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = Column(String(ID_LEN), ForeignKey('jobseeker_cvs.cv_id'), index=True)
    title = Column(String(NAME_LEN))
    description = Column(Text)
    technologies = Column(JSONB, default=[])
    link = Column(String(255), nullable=True)

    cv = relationship("JobSeekerCVORM", back_populates="projects")

class PublicationORM(Base):
    __tablename__ = 'cv_publications'

    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = Column(String(ID_LEN), ForeignKey('jobseeker_cvs.cv_id'), index=True)
    title = Column(String(NAME_LEN))
    publisher = Column(String(NAME_LEN), nullable=True)
    date = Column(Date, nullable=True)
    link = Column(String(255), nullable=True)

    cv = relationship("JobSeekerCVORM", back_populates="publications")


class AwardORM(Base):
    __tablename__ = 'cv_awards'

    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = Column(String(ID_LEN), ForeignKey('jobseeker_cvs.cv_id'), index=True)
    title = Column(String(NAME_LEN))
    issuer = Column(String(NAME_LEN), nullable=True)
    date = Column(Date, nullable=True)
    description = Column(Text)

    cv = relationship("JobSeekerCVORM", back_populates="awards")


class CustomSectionORM(Base):
    __tablename__ = 'cv_custom_sections'

    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = Column(String(ID_LEN), ForeignKey('jobseeker_cvs.cv_id'), index=True)
    title = Column(String(NAME_LEN))
    content = Column(JSONB)  # Can be text or list

    cv = relationship("JobSeekerCVORM", back_populates="custom_sections")


class SavedCVORM(Base):
    __tablename__ = "saved_cvs"

    id = Column(String(ID_LEN), primary_key=True)
    employer_uid = Column(String(ID_LEN), ForeignKey("users.uid"), nullable=False, index=True)
    cv_id = Column(String(ID_LEN), ForeignKey("job_seeker_cvs.id"), nullable=False, index=True)
    saved_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("employer_uid", "cv_id", name="uq_employer_cv"),
    )

    def __bool__(self):
        return bool(self.id) and bool(self.cv_id)

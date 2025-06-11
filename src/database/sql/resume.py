import uuid
from datetime import timezone

from sqlalchemy import Column, String, Date, DateTime, Boolean, ForeignKey, Text, UniqueConstraint, JSON
from sqlalchemy import inspect
from sqlalchemy.orm import relationship

from src.database.constants import ID_LEN, NAME_LEN
from src.database.constants import utc_time
from src.database.sql import Base, engine


class JobSeekerCVORM(Base):
    __tablename__ = 'jobseeker_cvs'

    cv_id = Column(String(ID_LEN), primary_key=True, unique=True, index=True)
    user_uid = Column(ForeignKey('jobseeker_profiles.user_uid'), nullable=False, index=True)
    is_primary = Column(Boolean, default=False)
    professional_title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    skills = Column(JSON, default=[])
    portfolio_links = Column(JSON, default=[])
    resume_file_url = Column(String(255), nullable=True)
    profile_image_url = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)  # Added location
    phone = Column(String(255), nullable=True)  # Added phone
    website = Column(String(255), nullable=True)  # Added website
    linkedin = Column(String(255), nullable=True)  # Added linkedin
    github = Column(String(255), nullable=True)  # Added github
    created_at = Column(DateTime(timezone=True), default=utc_time)

    # Relationships (if needed)
    experience = relationship("ExperienceORM", back_populates="cv", cascade="all, delete-orphan")
    education = relationship("EducationORM", back_populates="cv", cascade="all, delete-orphan")
    certifications = relationship("CertificationORM", back_populates="cv", cascade="all, delete-orphan")
    languages = relationship("LanguageORM", back_populates="cv", cascade="all, delete-orphan")
    projects = relationship("ProjectORM", back_populates="cv", cascade="all, delete-orphan")
    publications = relationship("PublicationORM", back_populates="cv", cascade="all, delete-orphan")
    awards = relationship("AwardORM", back_populates="cv", cascade="all, delete-orphan")
    custom_sections = relationship("CustomSectionORM", back_populates="cv", cascade="all, delete-orphan")
    jobseeker_profile = relationship("JobSeekerProfileORM", back_populates="resumes_list")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            cls.__table__.create(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self, include_relationship: bool = False) -> dict:
        return {
            "cv_id": self.cv_id,
            "user_uid": self.user_uid,
            "is_primary": self.is_primary,
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
            "created_at": self.created_at.replace(tzinfo=timezone.utc) if self.created_at else None,
            "experience": [exp.to_dict() for exp in self.experience] if include_relationship and self.experience else [],
            "education": [edu.to_dict() for edu in self.education] if include_relationship and self.education else [],
            "certifications": [cert.to_dict() for cert in self.certifications] if include_relationship and self.certifications else [],
            "languages": [lang.to_dict() for lang in self.languages] if include_relationship and self.languages else [],
            "projects": [proj.to_dict() for proj in self.projects] if include_relationship and self.projects else [],
            "publications": [pub.to_dict() for pub in self.publications] if include_relationship and self.publications else [],
            "awards": [award.to_dict() for award in self.awards] if include_relationship and self.awards else [],
            "custom_sections": [cust.to_dict() for cust in self.custom_sections] if include_relationship and self.custom_sections else [],
            "jobseeker_profile": [prof.to_dict() for prof in
                                  self.jobseeker_profile] if include_relationship and self.jobseeker_profile else []
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

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)
    def to_dict(self):
        return {
            "id": self.id,
            "cv_id": self.cv_id,
            "job_title": self.job_title,
            "company": self.company,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "location": self.location,
            "description": self.description
        }


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

    # noinspection PyUnresolvedReferences
    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self):
        return {
            'id': self.id,
            'cv_id': self.cv_id,
            'institution': self.institution,
            'qualification': self.qualification,
            'field_of_study': self.field_of_study,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'description': self.description
        }


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

    # noinspection PyUnresolvedReferences
    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self):
        return {
            'id': self.id,
            'cv_id': self.cv_id,
            'name': self.name,
            'issuer': self.issuer,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'credential_url': self.credential_url
        }

class LanguageORM(Base):
    __tablename__ = 'cv_languages'

    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = Column(String(ID_LEN), ForeignKey('jobseeker_cvs.cv_id'), index=True)
    name = Column(String(NAME_LEN))
    proficiency = Column(String(NAME_LEN))

    cv = relationship("JobSeekerCVORM", back_populates="languages")

    # noinspection PyUnresolvedReferences
    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self):
        return {
            'id': self.id,
            'cv_id': self.cv_id,
            'name': self.name,
            'proficiency': self.proficiency
        }


class ProjectORM(Base):
    __tablename__ = 'cv_projects'

    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = Column(String(ID_LEN), ForeignKey('jobseeker_cvs.cv_id'), index=True)
    title = Column(String(NAME_LEN))
    description = Column(Text)
    technologies = Column(JSON, default=[])
    link = Column(String(255), nullable=True)

    cv = relationship("JobSeekerCVORM", back_populates="projects")

    # noinspection PyUnresolvedReferences
    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)


    def to_dict(self):
        return {
            'id': self.id,
            'cv_id': self.cv_id,
            'title': self.title,
            'description': self.description,
            'technologies': self.technologies,
            'link': self.link
        }

class PublicationORM(Base):
    __tablename__ = 'cv_publications'

    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = Column(String(ID_LEN), ForeignKey('jobseeker_cvs.cv_id'), index=True)
    title = Column(String(NAME_LEN))
    publisher = Column(String(NAME_LEN), nullable=True)
    date = Column(Date, nullable=True)
    link = Column(String(255), nullable=True)

    cv = relationship("JobSeekerCVORM", back_populates="publications")

    # noinspection PyUnresolvedReferences
    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self):
        return {
            'id': self.id,
            'cv_id': self.cv_id,
            'title': self.title,
            'publisher': self.publisher,
            'date': self.date.isoformat() if self.date else None,
            'link': self.link
        }



class AwardORM(Base):
    __tablename__ = 'cv_awards'

    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = Column(String(ID_LEN), ForeignKey('jobseeker_cvs.cv_id'), index=True)
    title = Column(String(NAME_LEN))
    issuer = Column(String(NAME_LEN), nullable=True)
    date = Column(Date, nullable=True)
    description = Column(Text)

    cv = relationship("JobSeekerCVORM", back_populates="awards")

    # noinspection PyUnresolvedReferences
    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self):
        return {
            'id': self.id,
            'cv_id': self.cv_id,
            'title': self.title,
            'issuer': self.issuer,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description
        }


class CustomSectionORM(Base):
    __tablename__ = 'cv_custom_sections'

    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = Column(String(ID_LEN), ForeignKey('jobseeker_cvs.cv_id'), index=True)
    title = Column(String(NAME_LEN))
    content = Column(JSON)  # Can be text or list

    cv = relationship("JobSeekerCVORM", back_populates="custom_sections")

    # noinspection PyUnresolvedReferences
    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self):
        return {
            'id': self.id,
            'cv_id': self.cv_id,
            'title': self.title,
            'content': self.content
        }




class SavedCVORM(Base):
    __tablename__ = "saved_cvs"

    id = Column(String(ID_LEN), primary_key=True)
    employer_id = Column(String(ID_LEN), ForeignKey("users.uid"), nullable=False, index=True)
    cv_id = Column(String(ID_LEN), ForeignKey("jobseeker_cvs.cv_id"), nullable=False, index=True)
    saved_at = Column(DateTime(timezone=True), default=lambda: utc_time())
    notes = Column(Text)

    __table_args__ = (
        UniqueConstraint("employer_id", "cv_id", name="uq_employer_cv"),
    )

    def __bool__(self):
        return bool(self.id) and bool(self.cv_id)

    # noinspection PyUnresolvedReferences
    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self):
        return {
            'id': self.id,
            'employer_uid': self.employer_uid,
            'cv_id': self.cv_id,
            'notes': self.notes,
            'saved_at': self.saved_at.isoformat() if self.saved_at else None
        }

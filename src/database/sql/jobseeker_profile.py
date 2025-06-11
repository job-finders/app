from datetime import timezone

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, inspect, Integer, JSON
from sqlalchemy.orm import relationship

from src.database.constants import ID_LEN, NAME_LEN, utc_time
from src.database.sql import Base, engine  # Assuming this is your declarative base


class JobSeekerProfileORM(Base):
    __tablename__ = "jobseeker_profiles"

    user_uid = Column(String(ID_LEN), ForeignKey("users.uid"), primary_key=True)
    email : str = Column(String(NAME_LEN), index=True)
    # Job Seeker need to enable Job Alerts in order to get alerts based on their preferences
    alerts_enabled: bool = Column(Boolean, default=False)

    receive_deadline_reminders = Column(Boolean, default=True)
    reminder_days_before = Column(Integer, default=3)  # Days before deadline to remind
    last_reminded_at = Column(DateTime(timezone=True))  # Track last reminder time
    receive_company_updates = Column(Boolean, default=True)

    first_name = Column(String(NAME_LEN))
    last_name = Column(String(NAME_LEN))
    gender = Column(String(24), nullable=True)

    has_disability = Column(Boolean, default=False)
    # Basic info
    bio = Column(Text, nullable=True)
    profile_image_url = Column(String(NAME_LEN), nullable=True)
    location = Column(String(NAME_LEN), nullable=True)
    phone = Column(String(36), nullable=True)
    website = Column(String(NAME_LEN), nullable=True)
    linkedin = Column(String(NAME_LEN), nullable=True)
    github = Column(String(NAME_LEN), nullable=True)

    # Job preferences
    job_titles_of_interest = Column(JSON, default=[])
    industries_of_interest = Column(JSON, default=[])
    locations_of_interest = Column(JSON, default=[])
    remote_preference = Column(Boolean, default=False)
    availability = Column(String(NAME_LEN), nullable=True)
    expected_salary = Column(Integer, nullable=True)

    # Settings
    visibility = Column(Boolean, default=True)
    profile_completion = Column(String(NAME_LEN), default="0")  # or Integer if more appropriate
    last_updated = Column(DateTime, default=utc_time)
    # Relationships

    # List of job applications submitted by the Job Seeker
    applications = relationship("JobApplicationORM", back_populates="jobseeker_profile")
    # List of records showing records where companies saved the candidate for further onsideration
    interested_companies = relationship("SavedCandidatesORM", back_populates="candidate")
    # Companies the Job Seeker is following
    following_companies = relationship("CompanyFollowingORM", back_populates="jobseeker_follower")

    resumes_list = relationship("JobSeekerCVORM", back_populates="jobseeker_profile", cascade="all, delete-orphan")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)


    def to_dict(self, include_relationship: bool =False):
        return {
            "user_uid": self.user_uid,

            "first_name": self.first_name,
            "last_name": self.last_name,

            "bio": self.bio,
            "gender": self.gender,
            "has_disability": self.has_disability,

            "email": self.email,
            "receive_deadline_reminders": self.receive_deadline_reminders,
            "reminder_days_before": self.reminder_days_before,
            "last_reminded_at": self.last_reminded_at.replace(tzinfo=timezone.utc),
            "alerts_enabled": self.alerts_enabled,
            "receive_company_updates" : self.receive_company_updates,

            "profile_image_url": self.profile_image_url,
            "location": self.location,
            "phone": self.phone,
            "website": self.website,
            "linkedin": self.linkedin,
            "github": self.github,
            "job_titles_of_interest": self.job_titles_of_interest,
            "industries_of_interest": self.industries_of_interest,
            "locations_of_interest": self.locations_of_interest,
            "remote_preference": self.remote_preference,
            "expected_salary":self.expected_salary,
            "availability": self.availability,
            "visibility": self.visibility,
            "profile_completion": int(self.profile_completion),
            "last_updated": self.last_updated.replace(tzinfo=timezone.utc),
            "applications": [application.to_dict() for application in self.applications] if include_relationship else [],
            "interested_companies": [company.to_dict() for company in self.interested_companies] if include_relationship and self.interested_companies else [],
            "following_companies": [company_follow.to_dict() for company_follow in self.following_companies] if include_relationship and self.self.following_companies else []
        }

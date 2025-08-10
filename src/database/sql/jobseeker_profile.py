from datetime import timezone, datetime

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, inspect, Integer, JSON
from sqlalchemy.orm import relationship

from src.database.constants import ID_LEN, NAME_LEN, utc_time
from src.database.sql import Base, engine  # Assuming this is your declarative base


class JobSeekerProfileORM(Base):
    __tablename__ = "jobseeker_profiles"

    user_uid = Column(String(ID_LEN), ForeignKey("users.uid"), primary_key=True)
    email = Column(String(NAME_LEN), index=True)
    first_name = Column(String(NAME_LEN))
    last_name = Column(String(NAME_LEN))
    gender = Column(String(24), nullable=True)
    bio = Column(Text, nullable=True)
    profile_image_url = Column(String(NAME_LEN), nullable=True)

    has_disability = Column(Boolean, default=False)

    alerts_enabled = Column(Boolean, default=False)
    receive_deadline_reminders = Column(Boolean, default=True)
    reminder_days_before = Column(Integer, default=7)  # Days before deadline to remind
    last_reminded_at = Column(DateTime(timezone=True))  # Track last reminder time
    receive_company_updates = Column(Boolean, default=True)
    visibility = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=utc_time())

    # --- Verification ---
    verified_email = Column(Boolean, default=False)
    verified_phone = Column(Boolean, default=False)
    verified_linkedin = Column(Boolean, default=False)
    verified_github = Column(Boolean, default=False)

    location = Column(String(NAME_LEN), nullable=True)
    phone = Column(String(36), nullable=True)
    website = Column(String(NAME_LEN), nullable=True)
    linkedin = Column(String(NAME_LEN), nullable=True)
    github = Column(String(NAME_LEN), nullable=True)

    job_titles_of_interest = Column(JSON, default=[])
    industries_of_interest = Column(JSON, default=[])
    locations_of_interest = Column(JSON, default=[])
    remote_preference = Column(Boolean, default=False)
    availability = Column(String(NAME_LEN), nullable=True)
    expected_salary = Column(Integer, nullable=True)

    is_freelancer = Column(Boolean, default=False)  # Added missing field
    freelance_skills = Column(JSON, default=[])  # Added missing field
    hourly_rate = Column(Integer, nullable=True)  # Ensure this can be NULL
    freelance_experience = Column(Text, nullable=True)  # Added missing field
    freelance_availability = Column(String(NAME_LEN), nullable=True)  # Added missing field

    ip_address = Column(String(NAME_LEN), nullable=True)
    device_finger_print = Column(String(NAME_LEN), nullable=True)  # For device tracking
    # Relationships
    applications = relationship("JobApplicationORM", back_populates="jobseeker_profile")
    interested_companies = relationship("SavedCandidatesORM", back_populates="candidate")
    following_companies = relationship("CompanyFollowingORM", back_populates="jobseeker_follower")
    resumes_list = relationship("JobSeekerCVORM", back_populates="jobseeker_profile", cascade="all, delete-orphan")
    saved_jobs = relationship("SavedJobORM", back_populates="jobseeker_profile", cascade="all, delete-orphan")
    liked_jobs = relationship("JobLikeORM", back_populates="jobseeker_profile")
    shared_jobs = relationship("JobShareORM", back_populates="jobseeker_profile")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self, include_relationships: bool = False):
        def _format_datetime(dt):
            return dt.replace(tzinfo=timezone.utc).isoformat() if dt else None

        data = {
            'user_uid': self.user_uid,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'gender': self.gender,
            'bio': self.bio,
            'profile_image_url': self.profile_image_url,
            'has_disability': self.has_disability if self.has_disability is not None else False,
            'alerts_enabled': self.alerts_enabled if self.alerts_enabled is not None else True,
            'receive_deadline_reminders': self.receive_deadline_reminders if self.receive_deadline_reminders is not None else True,
            'reminder_days_before': self.reminder_days_before if self.reminder_days_before is not None else 7,
            'last_reminded_at': _format_datetime(self.last_reminded_at),
            'receive_company_updates': self.receive_company_updates if bool(self.receive_company_updates) else True,
            'visibility': self.visibility if bool(self.visibility) else True,
            'last_updated': _format_datetime(self.last_updated),
            'verified_email': self.verified_email if bool(self.verified_email) else False,
            'verified_phone': self.verified_phone if bool(self.verified_phone) else False,
            'verified_linkedin': self.verified_linkedin if bool(self.verified_linkedin) else False,
            'verified_github': self.verified_github if bool(self.verified_github) else False,
            'location': self.location,
            'phone': self.phone,
            'website': self.website,
            'linkedin': self.linkedin,
            'github': self.github,
            'job_titles_of_interest': self.job_titles_of_interest,
            'industries_of_interest': self.industries_of_interest,
            'locations_of_interest': self.locations_of_interest,
            'remote_preference': self.remote_preference,
            'availability': self.availability,
            'expected_salary': self.expected_salary,
            'is_freelancer': self.is_freelancer,
            'freelance_skills': self.freelance_skills,
            'hourly_rate': self.hourly_rate,
            'freelance_experience': self.freelance_experience,
            'freelance_availability': self.freelance_availability,
            'ip_address': self.ip_address,
            'device_finger_print': self.device_finger_print
        }

        if include_relationships:
            data['applications'] = [application.to_dict() for application in self.applications]
            data['interested_companies'] = [company.to_dict() for company in self.interested_companies]
            data['following_companies'] = [company_follow.to_dict() for company_follow in self.following_companies]
            data['resumes_list'] = [resume.to_dict() for resume in self.resumes_list]
            data['saved_jobs'] = [job.to_dict() for job in self.saved_jobs]
            data['liked_jobs'] = [like.to_dict() for like in self.liked_jobs]
            data['shared_jobs'] = [share.to_dict() for share in self.shared_jobs]

        return data

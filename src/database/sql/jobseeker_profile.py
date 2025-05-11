
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, inspect, Integer
from sqlalchemy.dialects.postgresql import ARRAY

from src.database.sql import Base, engine  # Assuming this is your declarative base


class JobSeekerProfileORM(Base):
    __tablename__ = "job_seeker_profiles"

    user_uid = Column(String, ForeignKey("users.uid"), primary_key=True)

    # Basic info
    bio = Column(Text, nullable=True)
    profile_image_url = Column(String, nullable=True)
    location = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    github = Column(String, nullable=True)

    # Job preferences
    job_titles_of_interest = Column(ARRAY(String), default=[])
    industries_of_interest = Column(ARRAY(String), default=[])
    locations_of_interest = Column(ARRAY(String), default=[])
    remote_preference = Column(Boolean, default=False)
    availability = Column(String, nullable=True)
    expected_salary = Column(Integer, nullable=True)

    # Settings
    visibility = Column(Boolean, default=True)
    profile_completion = Column(String, default="0")  # or Integer if more appropriate
    last_updated = Column(DateTime, default=datetime.utcnow)

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
            "user_uid": self.user_uid,
            "bio": self.bio,
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
            "last_updated": self.last_updated,
        }

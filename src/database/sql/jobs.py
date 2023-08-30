import uuid
from datetime import date
from sqlalchemy import Column, String, Date, Text, inspect

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
            expiration_date=self.date_expires
        )

    def to_dict(self) -> dict[str, str | date]:
        """
        Convert the instance to a dictionary.

        :return: A dictionary representation of the instance.
        """
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
            "posted_date": self.posted_date,
            "updated_time": self.updated_time,
            "expires": self.expires,
            "job_ref": self.job_ref,
            "description": self.description,
            "desired_skills": self.desired_skills,
            "expiration_date": self.date_expires,
        }

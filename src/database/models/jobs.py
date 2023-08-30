import re
from pydantic import BaseModel, validator

from src.utils import format_reference


class Job(BaseModel):
    search_term: str
    logo_link: str | None
    job_link: str
    title: str
    company_name: str
    salary: str
    position: str
    location: str
    updated_time: str
    expires: str
    job_ref: str
    description: str | None
    desired_skills: list[str] | None

    @validator('job_ref', pre=True)
    def format_job_ref(cls, value):
        # Remove spaces and convert to lowercase
        return format_reference(ref=value)

    @property
    def dynamic_expires(self):
        pass


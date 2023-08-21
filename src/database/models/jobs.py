from pydantic import BaseModel


class Job(BaseModel):
    logo_link: str
    job_link: str
    title: str
    company_name: str
    salary: str
    position: str
    location: str
    updated_time: str
    expires: str
    job_ref: str
    description: str
    desired_skills: list[str]

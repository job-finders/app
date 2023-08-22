from pydantic import BaseModel, validator


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

    @validator('job_ref', pre=True)
    def format_job_ref(cls, value):
        # Remove spaces and convert to lowercase
        return value.replace(' ', '').lower()
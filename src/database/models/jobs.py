import re
from datetime import datetime, timedelta, date
from pydantic import BaseModel, validator
from src.utils import format_reference


# noinspection PyMethodParameters
class Job(BaseModel):
    job_id: str | None
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
    def slug(self) -> str:
        """

        :return:
        """
        special_chars = r'[!@#$%^&*()+=\[\]{}|;:",<>/`~]-'
        _title = ""
        for char in self.title:
            if char not in special_chars:
                _title += char
        _title = f"{_title}_{self.job_ref.replace('-', '_')}"
        return _title.replace(" ", "_").lower().strip()

    @property
    def posted_date(self) -> date:
        """
        Validate and convert the posted_date string to a date object.

        :param value: The posted_date string to be validated.
        :return: The validated and converted date object.
        """
        # Assume the format is "Posted {day} {month abbreviation} {year} by {author}"
        try:
            posted_date_str = self.updated_time.split("by")[0].strip()[len("Posted "):]
            posted_date = datetime.strptime(posted_date_str, "%d %b %Y").date()
            return posted_date
        except ValueError:
            raise ValueError("Invalid posted_date format")

    @property
    def date_expires(self) -> date:
        # Extract the number of days from the expires string
        days_left = int(self.expires.split()[2])

        # Calculate the expiration date based on the posted date
        expiration_date = self.posted_date + timedelta(days=days_left)
        return expiration_date

    def disp_dict(self) -> dict[str, str | date]:
        """
        Return a dictionary representation of the Job instance.

        :return: A dictionary containing various attributes of the Job.
        """
        expiration_date = self.date_expires

        # Create the dictionary and return
        return {
            "job_id": self.job_id,
            "search_term": self.search_term,
            "logo_link": self.logo_link,
            "job_link": self.job_link,
            "title": self.title,
            "slug": self.slug,
            "company_name": self.company_name,
            "salary": self.salary,
            "position": self.position,
            "location": self.location,
            "updated_time": self.updated_time,
            "posted_date": self.posted_date,
            "expires": self.expires,
            "job_ref": self.job_ref,
            "description": self.description,
            "desired_skills": self.desired_skills,
            "expiration_date": expiration_date  # Add the calculated expiration date
        }

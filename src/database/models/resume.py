from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator
from typing import List, Optional, Union
from datetime import date, datetime
import uuid

from rich.table import Column


# Experience
class Experience(BaseModel):
    job_title: str
    company: str
    start_date: date
    end_date: Optional[date] = None
    location: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat(),
        }

    @validator('job_title', 'company')
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v


# Education
class Education(BaseModel):
    institution: str
    qualification: str
    field_of_study: str
    start_date: date
    end_date: Optional[date] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat(),
        }

    @validator('institution', 'qualification', 'field_of_study')
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v


# Certification
class Certification(BaseModel):
    name: str
    issuer: str
    issue_date: date
    expiry_date: Optional[date] = None
    credential_url: Optional[HttpUrl] = None

    class Config:
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat(),
        }

# Language
class Language(BaseModel):
    name: str
    proficiency: str  # e.g., Beginner, Intermediate, Fluent, Native

    class Config:
        from_attributes = True


# Publication (for academics)
class Publication(BaseModel):
    title: str
    publisher: Optional[str]
    date: Optional[date]
    link: Optional[HttpUrl]

    class Config:
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat(),
        }

# Project (for technical/creative fields)
class Project(BaseModel):
    title: str
    description: str
    technologies: Optional[List[str]] = []
    link: Optional[HttpUrl] = None

    class Config:
        from_attributes = True

# Award or Honor
class Award(BaseModel):
    title: str
    issuer: Optional[str]
    date: Optional[date]
    description: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat(),
        }

# Custom Section for extra content
class CustomSection(BaseModel):
    title: str
    content: Union[str, List[str]]  # Supports plain text or bullet lists

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class SavedCV(BaseModel):
    save_id: str = Field(default_factory= lambda : str(uuid.uuid4()))
    employer_id: str
    cv_id: str
    saved_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(default=None)

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class JobSeekerCV(BaseModel):
    cv_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_uid: str  # FK to User.uid
    is_primary: bool = Field(default=False)
    professional_title: str
    summary: Optional[str] = None
    location: Optional[str] = None  # New field for location
    phone: Optional[str] = None  # New field for phone
    website: Optional[str] = None  # New field for website
    linkedin: Optional[str] = None  # New field for linkedin
    github: Optional[str] = None  # New field for github
    skills: List[str]
    experience: List[Experience] = []
    education: List[Education] = []
    certifications: Optional[List[Certification]] = []
    languages: Optional[List[Language]] = []
    projects: Optional[List[Project]] = []
    publications: Optional[List[Publication]] = []
    awards: Optional[List[Award]] = []
    custom_sections: Optional[List[CustomSection]] = []

    # Media and links
    portfolio_links: Optional[List[HttpUrl]] = []
    resume_file_url: Optional[HttpUrl] = None  # Link to uploaded original resume
    profile_image_url: Optional[HttpUrl] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    jobseeker_profile: Optional[list['JobSeekerProfile']] = Field(default_factory=list)

    @validator('professional_title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Professional title cannot be empty")
        return v

    @validator('skills')
    def skills_must_have_values(cls, v):
        if not v or not all(s.strip() for s in v):
            raise ValueError("At least one valid skill must be provided")
        return v

    @property
    def ats_description(self) -> str:
        """
        Generates an ATS-friendly text representation of the resume.
        Structured for optimal parsing by applicant tracking systems and LLM agents.
        """
        sections = []

        # Header section
        header = [
            f"Professional Title: {self.professional_title}",
            f"Summary: {self.summary}" if self.summary else "",
            f"Location: {self.location}" if self.location else "",
            f"Contact: {self.phone} | {self.website}" if self.phone or self.website else "",
            f"LinkedIn: {self.linkedin}" if self.linkedin else "",
            f"GitHub: {self.github}" if self.github else ""
        ]
        sections.append("\n".join([line for line in header if line]))

        # Skills section
        if self.skills:
            skills_section = [
                "Skills:",
                ", ".join(self.skills)
            ]
            sections.append("\n".join(skills_section))

        # Experience section
        if self.experience:
            exp_section = ["Work Experience:"]
            for exp in self.experience:
                exp_entry = [
                    f"- {exp.job_title} at {exp.company}",
                    f"  {exp.start_date} to {exp.end_date or 'Present'}",
                    f"  Location: {exp.location}" if exp.location else "",
                    f"  Description: {exp.description}" if exp.description else ""
                ]
                exp_section.append("\n".join([line for line in exp_entry if line]))
            sections.append("\n".join(exp_section))

        # Education section
        if self.education:
            edu_section = ["Education:"]
            for edu in self.education:
                edu_entry = [
                    f"- {edu.qualification} in {edu.field_of_study}",
                    f"  Institution: {edu.institution}",
                    f"  {edu.start_date} to {edu.end_date or 'Present'}",
                    f"  Description: {edu.description}" if edu.description else ""
                ]
                edu_section.append("\n".join([line for line in edu_entry if line]))
            sections.append("\n".join(edu_section))

        # Projects section
        if self.projects:
            project_section = ["Projects:"]
            for project in self.projects:
                project_entry = [
                    f"- {project.title}",
                    f"  Technologies: {', '.join(project.technologies)}" if project.technologies else "",
                    f"  Link: {project.link}" if project.link else "",
                    f"  Description: {project.description}" if project.description else ""
                ]
                project_section.append("\n".join([line for line in project_entry if line]))
            sections.append("\n".join(project_section))

        # Additional sections
        additional = []
        if self.certifications:
            certs = [f"- {cert.name} ({cert.issuer})" for cert in self.certifications]
            additional.append("Certifications:\n" + "\n".join(certs))

        if self.languages:
            langs = [f"- {lang.name} ({lang.proficiency})" for lang in self.languages]
            additional.append("Languages:\n" + "\n".join(langs))

        if self.awards:
            awards = [f"- {award.title} ({award.issuer})" for award in self.awards]
            additional.append("Awards:\n" + "\n".join(awards))

        if self.publications:
            pubs = [f"- {pub.title} ({pub.publisher})" for pub in self.publications]
            additional.append("Publications:\n" + "\n".join(pubs))

        if self.custom_sections:
            for custom in self.custom_sections:
                content = custom.content
                if isinstance(content, list):
                    content = "\n".join([f"- {item}" for item in content])
                additional.append(f"{custom.title}:\n{content}")

        if additional:
            sections.append("\n\n".join(additional))

        # Portfolio links
        if self.portfolio_links:
            portfolio = [f"Portfolio: {link}" for link in self.portfolio_links]
            sections.append("\n".join(portfolio))

        return "\n\n".join(sections)

    @property
    def resume_has_boilerplate(self) -> bool:
        """
        Checks if the resume contains boilerplate or fake data (e.g., lorem ipsum, repeated patterns).
        """
        if not self.ats_description:
            return False

        lower = self.ats_description

        boilerplate_phrases = [
            "lorem ipsum", "your name here", "insert experience", "n/a", "no experience",
            "generic title", "template content", "objective goes here"
        ]
        match_count = sum(1 for phrase in boilerplate_phrases if phrase in lower)
        return match_count >= 2

    class Config:
        # Allow the model to use `datetime` fields as ISO format strings when serialized
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()  # Ensure the datetime fields are serialized in ISO format
        }

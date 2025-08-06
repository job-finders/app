import uuid
from datetime import date
from typing import List, Optional, Union, Any

from pydantic import BaseModel, Field, HttpUrl, ConfigDict, field_validator, AwareDatetime, field_serializer
from src.database.constants import utc_time


# Experience
class Experience(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cv_id: str  # FK to JobSeekerCV.cv_id
    job_title: str
    company: str
    start_date: date
    end_date: Optional[date] = None
    location: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(
        extra='ignore',
        from_attributes=True
    )

    @field_validator('job_title', 'company')
    @classmethod
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v


# Education
class Education(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cv_id: str  # FK to JobSeekerCV.cv_id
    institution: str
    qualification: str
    field_of_study: str
    start_date: date
    end_date: Optional[date] = None
    description: Optional[str] = None

    model_config = ConfigDict(
        extra='ignore',
        from_attributes=True
    )

    @field_validator('institution', 'qualification', 'field_of_study')
    @classmethod
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v


# Certification
class Certification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cv_id: str  # FK to JobSeekerCV.cv_id
    name: str
    issuer: str
    issue_date: date
    expiry_date: Optional[date] = None
    credential_url: Optional[HttpUrl] = None

    model_config = ConfigDict(
        extra='ignore',
        from_attributes=True
    )

    @field_serializer('credential_url')
    def serialize_credential_url(self, value: Optional[HttpUrl]) -> Optional[str]:
        return str(value) if value else None


# Language
class Language(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cv_id: str  # FK to JobSeekerCV.cv_id
    name: str
    proficiency: str  # e.g., Beginner, Intermediate, Fluent, Native

    model_config = ConfigDict(
        extra='ignore',
        from_attributes=True
    )


# Publication (for academics)
class Publication(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cv_id: str  # FK to JobSeekerCV.cv_id
    title: str
    publisher: Optional[str]
    date: Optional[date]
    link: Optional[HttpUrl]

    model_config = ConfigDict(
        extra='ignore',
        from_attributes=True
    )

    @field_serializer('link')
    def serialize_link(self, value: Optional[HttpUrl]) -> Optional[str]:
        return str(value) if value else None


# Project (for technical/creative fields)
class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cv_id: str  # FK to JobSeekerCV.cv_id
    title: str
    description: str
    technologies: Optional[List[str]] = []
    link: Optional[HttpUrl] = None

    model_config = ConfigDict(
        extra='ignore',
        from_attributes=True
    )

    @field_serializer('link')
    def serialize_link(self, value: Optional[HttpUrl]) -> Optional[str]:
        return str(value) if value else None


# Award or Honor
class Award(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cv_id: str  # FK to JobSeekerCV.cv_id
    title: str
    issuer: Optional[str]
    date: Optional[date]
    description: Optional[str] = None

    model_config = ConfigDict(
        extra='ignore',
        from_attributes=True
    )


# Custom Section for extra content
class CustomSection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cv_id: str  # FK to JobSeekerCV.cv_id
    title: str
    content: Union[str, List[str]]  # Supports plain text or bullet lists

    model_config = ConfigDict(
        extra='ignore',
        from_attributes=True
    )


class SavedCV(BaseModel):
    save_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employer_id: str
    cv_id: str
    saved_at: AwareDatetime = Field(default_factory=utc_time())
    notes: Optional[str] = Field(default=None)

    model_config = ConfigDict(from_attributes=True)


class JobSeekerCV(BaseModel):
    cv_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_uid: str  # FK to User.uid
    is_primary: bool = Field(default=False)
    professional_title: str
    summary: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    website: Optional[str] = Field(default=None)
    linkedin: Optional[str] = Field(default=None)
    github: Optional[str] = Field(default=None)
    skills: List[str] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    certifications: Optional[List[Certification]] = Field(default_factory=list)
    languages: Optional[List[Language]] = Field(default_factory=list)
    projects: Optional[List[Project]] = Field(default_factory=list)
    publications: Optional[List[Publication]] = Field(default_factory=list)
    awards: Optional[List[Award]] = Field(default_factory=list)
    custom_sections: Optional[List[CustomSection]] = Field(default_factory=list)

    # Media and links
    portfolio_links: Optional[List[HttpUrl]] = Field(default_factory=list)
    resume_file_url: Optional[HttpUrl] = Field(default=None)
    profile_image_url: Optional[HttpUrl] = Field(default=None)

    created_at: AwareDatetime = Field(default_factory=lambda: utc_time())
    jobseeker_profile: Optional['JobSeekerProfile'] = Field(default=None)

    model_config = ConfigDict(from_attributes=True)

    # Serialize HttpUrl fields to strings
    @field_serializer('portfolio_links')
    def serialize_portfolio_links(self, value: Optional[List[HttpUrl]]) -> Optional[List[str]]:
        return [str(link) for link in value] if value else []

    @field_serializer('resume_file_url')
    def serialize_resume_file_url(self, value: Optional[HttpUrl]) -> Optional[str]:
        return str(value) if value else None

    @field_serializer('profile_image_url')
    def serialize_profile_image_url(self, value: Optional[HttpUrl]) -> Optional[str]:
        return str(value) if value else None

    @field_validator('professional_title')
    @classmethod
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Professional title cannot be empty")
        return v

    @field_validator('skills')
    @classmethod
    def skills_must_have_values(cls, v):
        if not v or not all(s.strip() for s in v):
            raise ValueError("At least one valid skill must be provided")
        return v

    # Rest of your methods remain the same...
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

    @property
    def resume_completion_percentage(self) -> int:
        score = 0
        max_score = 0

        def add_score(condition: bool, weight: float):
            nonlocal score, max_score
            max_score += weight
            if condition:
                score += weight

        # 🔹 Header Info
        add_score(bool(getattr(self, "professional_title", None)), 5)
        summary = getattr(self, "summary", "")
        add_score(bool(summary and summary.strip()), 5)
        add_score(bool(getattr(self, "location", None)), 2)
        add_score(bool(getattr(self, "phone", None)), 2)
        contact_fields = [getattr(self, "website", None), getattr(self, "linkedin", None), getattr(self, "github", None)]
        add_score(any(contact_fields), 3)

        # 🔹 Skills
        skills = getattr(self, "skills", []) or []
        add_score(bool(skills), 8)

        # 🔹 Experience
        experience = getattr(self, "experience", []) or []
        add_score(bool(experience), 12)
        has_descriptions = all(
            isinstance(e.description, str) and len(e.description.strip()) > 30
            for e in experience if e and hasattr(e, "description")
        )
        add_score(has_descriptions, 3)

        # 🔹 Education
        education = getattr(self, "education", []) or []
        add_score(bool(education), 10)

        # 🔹 Projects
        projects = getattr(self, "projects", []) or []
        add_score(bool(projects), 4)
        project_has_tech = any(getattr(p, "technologies", []) for p in projects)
        add_score(project_has_tech, 1)

        # 🔹 Certifications / Awards / Languages / Publications
        add_score(bool(getattr(self, "certifications", []) or []), 2)
        add_score(bool(getattr(self, "awards", []) or []), 1)
        add_score(bool(getattr(self, "languages", []) or []), 1)
        add_score(bool(getattr(self, "publications", []) or []), 1)

        # 🔹 Media / Branding
        add_score(bool(getattr(self, "resume_file_url", None)), 3)
        add_score(bool(getattr(self, "profile_image_url", None)), 2)
        add_score(bool(getattr(self, "portfolio_links", []) or []), 2)

        # 🔹 Custom Sections
        add_score(bool(getattr(self, "custom_sections", []) or []), 2)

        percent = int((score / max_score) * 100) if max_score else 0
        return min(percent, 100)

    @property
    def trust_score(self) -> int:
        score = 0
        max_score = 100

        def is_filled(x):
            return bool(x and str(x).strip())

        # ---- Completeness (30 pts) ----
        if is_filled(self.professional_title): score += 5
        if is_filled(self.summary): score += 5
        if self.skills: score += 5
        if self.experience: score += 5
        if self.education: score += 5
        if self.certifications: score += 2.5
        if self.languages: score += 2.5

        # ---- Consistency & Boilerplate Check (20 pts) ----
        if not self.resume_has_boilerplate: score += 10
        try:
            for exp in self.experience:
                if exp.end_date and exp.end_date < exp.start_date:
                    break
            else:
                score += 10
        except Exception:
            pass

        # ---- Verifiability (20 pts) ----
        if self.linkedin: score += 5
        if self.github: score += 5
        if self.website: score += 5
        if self.phone: score += 2.5
        if self.resume_file_url: score += 2.5

        # ---- Evidence/Assets (20 pts) ----
        if self.portfolio_links: score += 10
        if self.profile_image_url: score += 5
        if self.projects: score += 5

        # ---- Depth (10 pts) ----
        if any(p.description for p in self.projects or []): score += 5
        if any(e.description for e in self.experience or []): score += 5

        return min(int(score), 100)

    @property
    def relevance_score(self, job_posting_keywords: List[str]) -> int:
        """
        Calculates the relevance of the CV to a specific job posting based on keyword matching.
        """
        score = 0
        max_score = 100

        # Check for keyword matches in summary, skills, experience, and education
        cv_text = f"{self.summary} {' '.join(self.skills)} {' '.join([exp.description for exp in self.experience if exp.description])} {' '.join([edu.description for edu in self.education if edu.description])}"
        cv_text = cv_text.lower()

        keyword_matches = sum(1 for keyword in job_posting_keywords if keyword.lower() in cv_text)
        score = (keyword_matches / len(job_posting_keywords)) * 100

        return min(int(score), 100)

    @property
    def experience_quality_score(self) -> int:
        """
        Evaluates the quality of work experience based on duration, job titles, and descriptions.
        """
        score = 0
        max_score = 100

        if not self.experience:
            return 0

        total_duration = 0
        for exp in self.experience:
            if exp.end_date:
                total_duration += (exp.end_date - exp.start_date).days
            else:
                total_duration += (date.today() - exp.start_date).days

        avg_duration = total_duration / len(self.experience)
        score += (avg_duration / 365) * 20  # Assuming 20 points for experience duration

        has_descriptions = all(
            isinstance(e.description, str) and len(e.description.strip()) > 30
            for e in self.experience if e and hasattr(e, "description")
        )
        if has_descriptions:
            score += 20

        return min(int(score), 100)

    @property
    def education_quality_score(self) -> int:
        """
        Evaluates the quality of education based on institution prestige, degrees, and GPA.
        """
        score = 0
        max_score = 100

        if not self.education:
            return 0

        # Placeholder for institution prestige (could be a predefined list or API call)
        institution_prestige = {"Harvard University": 10, "MIT": 10, "Stanford University": 10, "Other": 5}

        for edu in self.education:
            score += institution_prestige.get(edu.institution, 5)
            if "Master" in edu.qualification or "PhD" in edu.qualification:
                score += 10
            if edu.description and "GPA" in edu.description:
                score += 10

        return min(int(score / len(self.education)), 100)

    @property
    def skills_relevance_score(self, job_posting_skills: List[str]) -> int:
        """
        Evaluates the relevance of skills to a specific job posting.
        """
        score = 0
        max_score = 100

        if not self.skills:
            return 0

        skill_matches = sum(1 for skill in job_posting_skills if skill in self.skills)
        score = (skill_matches / len(job_posting_skills)) * 100

        return min(int(score), 100)

    @property
    def custom_section_quality_score(self) -> int:
        """
        Evaluates the quality of custom sections based on content completeness and relevance.
        """
        score = 0
        max_score = 100

        if not self.custom_sections:
            return 0

        for section in self.custom_sections:
            if isinstance(section.content, str) and len(section.content.strip()) > 50:
                score += 20
            elif isinstance(section.content, list) and len(section.content) > 3:
                score += 20

        return min(int(score / len(self.custom_sections)), 100)

    @property
    def overall_quality_score(self, job_posting_keywords: List[str], job_posting_skills: List[str]) -> int:
        """
        Combines multiple quality metrics into a single overall quality score.
        """
        score = 0
        max_score = 100

        score += self.resume_completion_percentage * 0.2
        score += self.trust_score * 0.2
        score += self.relevance_score(job_posting_keywords) * 0.2
        score += self.experience_quality_score * 0.2
        score += self.education_quality_score * 0.1
        score += self.skills_relevance_score(job_posting_skills) * 0.1
        score += self.custom_section_quality_score * 0.1

        return min(int(score), 100)

# agents/employer/job_post_intelligence.py
import uuid
from typing import Type, Optional, List, Dict

from pydantic import BaseModel, Field, field_validator

# from src.database.models import Job
from src.agents.base import BaseAgent


class EnhanceJobPostInput(BaseModel):
    """
    Input model for job post enhancement agent.
    Contains partial information about a job post that needs enhancement.
    """
    title: str = Field(..., min_length=5, description="Job title (can be partial or basic)")
    description: str = Field(..., description="Job description (can be incomplete)")
    position_type: Optional[str] = Field(
        None,
        description="Type of position (FULL_TIME, PART_TIME, CONTRACT)",
        pattern="FULL_TIME|PART_TIME|CONTRACT"
    )
    remote_policy: Optional[str] = Field(
        None,
        description="Remote work policy (ONSITE, HYBRID, REMOTE)",
        pattern="ONSITE|HYBRID|REMOTE"
    )
    salary_min: Optional[float] = Field(None, ge=0, description="Minimum salary in local currency")
    salary_max: Optional[float] = Field(None, ge=0, description="Maximum salary in local currency")
    salary_currency: Optional[str] = Field("ZAR", description="Currency code (3 characters)")
    city: Optional[str] = Field(None, description="Job city location")
    province: Optional[str] = Field(None, description="Job province/state location")
    country: Optional[str] = Field(None, description="Job country location")
    experience_level: Optional[str] = Field(
        None,
        description="Experience level (ENTRY, MID, SENIOR)",
        pattern="ENTRY|MID|SENIOR"
    )
    required_skills: Optional[List[str]] = Field([], description="List of required skills")
    preferred_skills: Optional[List[str]] = Field([], description="List of preferred skills")

    @field_validator("salary_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if v and len(v) != 3:
            raise ValueError("Currency code must be 3 characters")
        return v.upper()


class EnhanceJobPostOutput(BaseModel):
    """
    Enhanced job post output model that directly maps to the Job ORM model.
    Contains a complete, professionally enhanced job post ready for conversion.
    """
    # Core Identification
    job_ref: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4())[:8].upper())

    # Job Details
    title: str = Field(..., min_length=5, max_length=255, description="Enhanced job title")
    description: str = Field(..., description="Detailed job description")
    position_type: str = Field(
        ...,
        description="Position event_type (FULL_TIME, PART_TIME, CONTRACT)",
        pattern="FULL_TIME|PART_TIME|CONTRACT"
    )
    remote_policy: str = Field(
        ...,
        description="Remote work policy (ONSITE, HYBRID, REMOTE)",
        pattern="ONSITE|HYBRID|REMOTE"
    )
    category: Optional[str] = Field(None, description="Job category")

    # Compensation
    salary_min: float = Field(..., ge=0, description="Competitive minimum salary")
    salary_max: float = Field(..., ge=0, description="Competitive maximum salary")
    salary_currency: str = Field("ZAR", min_length=3, max_length=3, description="Currency code")
    salary_confidential: bool = Field(False, description="Salary confidentiality flag")

    # Location
    city: str = Field(..., min_length=2, max_length=100, description="Job city")
    province: str = Field(..., min_length=2, max_length=100, description="Job province/state")
    country: str = Field(..., min_length=2, max_length=100, description="Job country")
    geo_location: Optional[str] = Field(None, description="Geolocation coordinates")

    # Timeline
    expires_at: Optional[str] = Field(None, description="Job expiration date (ISO format)")
    application_deadline: Optional[str] = Field(None, description="Application deadline (ISO format)")

    # Requirements
    experience_level: str = Field(
        ...,
        description="Experience level (ENTRY, MID, SENIOR)",
        pattern="ENTRY|MID|SENIOR"
    )
    education_requirements: Optional[Dict[str, str]] = Field(
        {},
        description="Education requirements as key-value pairs"
    )
    required_skills: List[str] = Field(..., description="List of required skills")
    preferred_skills: List[str] = Field([], description="List of preferred skills")
    required_documents: List[str] = Field([], description="List of required documents")
    required_questionnaire: List[str] = Field([], description="List of required questionnaire IDs")

    # Application Process
    application_url: Optional[str] = Field(None, description="Application URL")
    application_instructions: str = Field(..., min_length=10, description="Application instructions")

    # Status
    status: str = Field("draft", pattern="draft|pending|active|closed|archived")
    is_featured: bool = Field(False, description="Featured job flag")

    class Config:
        from_attributes = True


class EnhanceJobPostAgent(BaseAgent):
    """Agent that enhances partial job posts into complete, professional listings."""
    name = "enhance_job_post"
    description = "Creates complete, professional job posts from partial inputs"

    def system_prompt(self) -> str:
        return (
            "You are a professional job post generator for employers. "
            "Create complete, attractive job posts using ONLY the following JSON schema:"
        )

    def prompt(self, input_model: EnhanceJobPostInput) -> str:
        # Build context from input
        context = [
            f"Title: {input_model.title}",
            f"Description: {input_model.description}",
            f"Position Type: {input_model.position_type or 'Not specified'}",
            f"Remote Policy: {input_model.remote_policy or 'Not specified'}",
            f"Salary: {input_model.salary_min or 'N/A'} - {input_model.salary_max or 'N/A'} {input_model.salary_currency}",
            f"Location: {input_model.city or ''}, {input_model.province or ''}, {input_model.country or ''}",
            f"Experience Level: {input_model.experience_level or 'Not specified'}",
            f"Required Skills: {', '.join(input_model.required_skills) if input_model.required_skills else 'None'}",
            f"Preferred Skills: {', '.join(input_model.preferred_skills) if input_model.preferred_skills else 'None'}"
        ]

        return f"""
Create a complete, professional job post based on the following partial information:

{"\n".join(context)}

Generate a comprehensive job post including:
1. An attractive, clear job title (5-255 characters)
2. Detailed job description with responsibilities and expectations
3. Position event_type (FULL_TIME, PART_TIME, or CONTRACT)
4. Remote work policy (ONSITE, HYBRID, or REMOTE)
5. Competitive salary range as numbers (min and max)
6. Salary currency (3-letter code, default to ZAR)
7. Location details (city, province, country)
8. Experience level (ENTRY, MID, or SENIOR)
9. Comprehensive list of required skills
10. List of preferred skills
11. Suggested education requirements as key-value pairs
12. Clear application instructions (min 10 characters)
13. Application deadline (30 days from now in ISO format)
14. Expiration date (60 days from now in ISO format)

Additional guidelines:
- Salary should be competitive for the role and location
- Application instructions should include how to apply
- Education requirements should be realistic for the role
- Use South African context when location is unspecified

Output MUST be in valid JSON format matching the specified schema.
"""

    def output_model(self):
        return EnhanceJobPostOutput


# Job Post Insights Models
class JobPostInsights(BaseModel):
    clarity_score: float
    salary_benchmark: str
    missing_information: List[str]
    suggestions: List[str]

    class Config:
        from_attributes = True


class JobPostIntelligenceAgent(BaseAgent):
    __doc__ = "This Agent is used to Analyze Existing Job posts"
    name = "job_post_intelligence"
    description = "Analyzes job post quality, clarity, and competitiveness based on salary, skills, and completeness."

    def system_prompt(self) -> str:
        return (
            "You are an expert in recruitment and job post optimization. "
            "Your role is to analyze job posts for clarity, market competitiveness, and completeness. "
            "Return structured insights, and suggest improvements where necessary."
        )

    def prompt(self, input_model: 'Job') -> str:
        return (
            f"Analyze the following job post:\n\n"
            f"{input_model.ats_description.strip()}\n\n"
            f"Provide feedback on:\n"
            f"- Clarity\n"
            f"- Salary competitiveness\n"
            f"- Skill requirements\n"
            f"- Missing information\n"
            f"- Overall completeness\n\n"
            f"Respond in structured JSON using the defined schema."
        )

    def output_model(self) -> Type[BaseModel]:
        return JobPostInsights




# Job Summary Models
class JobSummaryInput(BaseModel):
    ats_description: str


class JobSummaryOutput(BaseModel):
    summary: str = Field(..., description="A short, engaging summary of the job suitable for listing previews.")
    seo_description: str = Field(..., description="SEO-optimized description for the job post.")

class JobSummaryAgent(BaseAgent):
    __doc__ = "This Agent creates both a user-facing summary and an SEO-optimized description for a job post."
    name = "job_summary"
    description = (
        "Generates a preview summary for job listings and a separate SEO-optimized meta description."
    )

    def system_prompt(self) -> str:
        return (
            "You are an expert in writing job summaries and SEO content for job listings. "
            "Your task is to generate two things:\n"
            "1. A concise, engaging summary (2–3 sentences) suitable for display in job listing previews.\n"
            "2. A search engine optimized (SEO) description designed for meta tags and social sharing, "
            "highlighting key job info in a way that improves discoverability.\n\n"
            "Both must be clear, professional, and informative."
        )

    def prompt(self, input_model: JobSummaryInput) -> str:
        return (
            f"Here is the full job description (ATS format):\n\n"
            f"{input_model.job_ats_description.strip()}\n\n"
            f"Using the above, generate the following in JSON format:\n"
            f'{{\n'
            f'  "summary": "<Concise, 2–3 sentence summary for display>",\n'
            f'  "seo_description": "<SEO-optimized meta description>"\n'
            f'}}'
        )

    def output_model(self) -> Type[BaseModel]:
        return JobSummaryOutput

# agents/employer/job_post_intelligence.py
import uuid
from typing import Type, Optional, List, Dict

from pydantic import BaseModel, Field, field_validator, ConfigDict

from src.agents.base import BaseAgent

from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ------------------------------------------------------------------
# Enumerations (used for clarity and validation)
# ------------------------------------------------------------------
class PositionType(str, Enum):
    """Legal values for the *position_type* field."""
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"


class RemotePolicy(str, Enum):
    """Legal values for the *remote_policy* field."""
    ONSITE = "ONSITE"
    HYBRID = "HYBRID"
    REMOTE = "REMOTE"


class ExperienceLevel(str, Enum):
    """Legal values for the *experience_level* field."""
    ENTRY = "ENTRY"
    MID = "MID"
    SENIOR = "SENIOR"


# ------------------------------------------------------------------
# INPUT  – partial or incomplete job post submitted by the user
# ------------------------------------------------------------------
class EnhanceJobPostInput(BaseModel):
    """
    Represents the **partial** or **draft** data that a recruiter / HR system
    already has for a job post.
    All fields are optional **except** `title` and `description`, which must be
    provided (even if they are rough).

    The agent will use this sparse information to generate a **complete,
    polished, market-competitive job listing** that conforms to
    `EnhanceJobPostOutput`.

    Field notes
    -----------
    - salary_* values must be expressed in the currency given by
      `salary_currency` (default = ZAR).
    - Currency codes must be the 3-letter ISO-4217 form (e.g. ZAR, USD, EUR).
    - Lists such as `required_skills` may be empty or incomplete; the agent
      will expand and refine them.
    """

    title: str = Field(
        ...,
        min_length=5,
        description="Job title as currently known (can be a fragment or placeholder)."
    )
    description: str = Field(
        ...,
        description="Free-text description of the role. May be incomplete or informal."
    )
    position_type: Optional[PositionType] = Field(
        None,
        description="Employment arrangement."
    )
    remote_policy: Optional[RemotePolicy] = Field(
        None,
        description="Where the employee is expected to work from."
    )
    salary_min: Optional[float] = Field(
        None,
        ge=0,
        description="Minimum gross annual (or monthly) salary expressed in `salary_currency`."
    )
    salary_max: Optional[float] = Field(
        None,
        ge=0,
        description="Maximum gross annual (or monthly) salary expressed in `salary_currency`."
    )
    salary_currency: Optional[str] = Field(
        "ZAR",
        description="3-letter ISO-4217 currency code. Defaults to South African Rand (ZAR)."
    )
    city: Optional[str] = Field(None, description="Primary workplace city.")
    province: Optional[str] = Field(None, description="State / Province.")
    country: Optional[str] = Field(None, description="Country (ISO-3166 name or code).")
    experience_level: Optional[ExperienceLevel] = Field(
        None,
        description="Seniority expectation for applicants."
    )
    required_skills: Optional[List[str]] = Field(
        default_factory=list,
        description="Skills that are currently considered mandatory. May be expanded."
    )
    preferred_skills: Optional[List[str]] = Field(
        default_factory=list,
        description="Skills that are currently considered nice-to-have. May be expanded."
    )

    model_config = ConfigDict(extra="ignore")

    @field_validator("salary_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """
        Ensures the currency code is exactly 3 uppercase characters.
        """
        if v and len(v) != 3:
            raise ValueError("Currency code must be exactly 3 characters (ISO-4217).")
        return v.upper()

# ------------------------------------------------------------------
# OUTPUT – fully-fledged, publication-ready job post
# ------------------------------------------------------------------
class EnhanceJobPostOutput(BaseModel):
    """
    Final, **complete** job post returned by the agent.
    All core fields are **mandatory** so that downstream consumers
    (job boards, applicant tracking systems, etc.) can rely on consistent data.

    The agent guarantees:
    - Competitive salary range researched for the role and location.
    - A crisp, human-readable description and title.
    - A realistic set of required/preferred skills and education expectations.
    - All salary figures are in South African Rands (ZAR) unless otherwise
      instructed.
    """
    # ── Job Identity -------------------------------------------------
    title: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Polished, market-standard job title (no internal codes)."
    )
    description: str = Field(
        ...,
        description="Full-length, engaging description covering responsibilities, "
                    "day-to-day tasks, growth opportunities, and company culture."
    )

    # ── Compensation -------------------------------------------------
    salary_min: float = Field(
        ...,
        ge=0,
        description="Competitive minimum gross annual salary in ZAR."
    )
    salary_max: float = Field(
        ...,
        ge=0,
        description="Competitive maximum gross annual salary in ZAR."
    )
    salary_currency: str = Field(
        "ZAR",
        min_length=3,
        max_length=3,
        description="Currency of salary. Always 'ZAR' unless explicitly requested otherwise."
    )

    # ── Requirements -------------------------------------------------
    experience_level: ExperienceLevel = Field(
        ...,
        description="Seniority level as enumerated."
    )
    education_requirements: Dict[str, str] = Field(
        default_factory=dict,
        description="Key-value mapping of education expectations. "
                    "Example: {'Diploma': 'Marketing or related field', "
                    "'Certification': 'Google Ads preferred'}."
    )
    required_skills: List[str] = Field(
        ...,
        description="Concise list of non-negotiable technical and soft skills."
    )
    preferred_skills: List[str] = Field(
        default_factory=list,
        description="Additional skills that would give a candidate an edge."
    )
    required_documents: List[str] = Field(
        default_factory=list,
        description="List of documents applicants must upload (CV, cover letter, "
                    "portfolio, etc.)."
    )
    required_questionnaire: List[str] = Field(
        default_factory=list,
        description="IDs of questionnaires or screening tests that must be completed."
    )

    model_config = ConfigDict(extra="ignore")

# ------------------------------------------------------------------
# AGENT – LLM-powered job-post enhancer
# ------------------------------------------------------------------
class EnhanceJobPostAgent(BaseAgent):
    """
    LangChain-compatible agent that converts **incomplete** or **rough** job
    post data into **complete, attractive, and market-ready listings**.

    Responsibilities
    ----------------
    1. Accepts `EnhanceJobPostInput` (sparse data).
    2. Generates a fully populated `EnhanceJobPostOutput`.
    3. Ensures salary ranges are competitive for the role and location.
    4. Expands skill lists and crafts clear, inclusive descriptions.
    5. Returns structured JSON that can be posted directly to job boards.

    Usage example
    -------------
        agent = EnhanceJobPostAgent()
        partial_data = EnhanceJobPostInput(
            title="Python dev",
            description="Need someone who knows Django",
            city="Cape Town"
        )
        final_post = agent.run(partial_data)
    """

    name: str = "enhance_job_post"
    description: str = (
        "Transforms partial or informal job posts into complete, professional, "
        "and market-competitive South-African job listings."
    )
    user_prompt: Optional[str] = None

    def system_prompt(self) -> str:
        """
        Static system-level instructions that are always injected at the top
        of the LLM prompt.  Emphasises JSON schema compliance and South-African
        salary norms.
        """
        return (
            "You are a South-African talent acquisition specialist. "
            "Your sole task is to generate polished, inclusive, and realistic "
            "job posts in **valid JSON** matching the `EnhanceJobPostOutput` schema. "
            "All salaries must be expressed in **South African Rands (ZAR)**."
        )

    def set_user_prompt(self, user_prompt: Optional[str] = None) -> None:
        """
        Allows the caller to inject an additional free-text prompt that will be
        appended to the generation instructions (e.g. “Focus on diversity hiring”).
        """
        self.user_prompt = user_prompt

    def prompt(self, input_model: EnhanceJobPostInput) -> str:
        """
        Constructs the full prompt sent to the LLM.

        Combines:
        - The system prompt
        - The raw candidate data (formatted as human-readable bullet points)
        - Any caller-supplied `user_prompt`
        - Explicit JSON schema constraints
        """
        context_lines = [
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
Create a complete, professional job post based on the sparse information below.

{chr(10).join(context_lines)}

Requirements for the generated post:
    1. Title must be market-standard and between 5-255 characters.
    2. Description must be engaging, inclusive, and cover key responsibilities, KPIs, and growth opportunities.
    3. Salary range must be **competitive for South Africa** in **ZAR only**.
    4. Experience level must be exactly one of: ENTRY, MID, SENIOR.
    5. Required skills list must be non-empty and realistic.
    6. Preferred skills list may be empty but must be exhaustive.
    7. Education requirements should be provided as key-value pairs (e.g. {{ "Diploma": "Information Technology" }}).
    8. Output must be **valid JSON** conforming to the `EnhanceJobPostOutput` schema.

Additional instructions from caller:
    - {self.user_prompt or "No additional instructions."}

Return **only** the JSON object.
"""

    def output_model(self) -> type[EnhanceJobPostOutput]:
        """
        Returns the Pydantic model that the LLM response should be parsed into.
        """
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


class JobCategoryNameInput(BaseModel):
    category_name: str = Field(..., min_length=2, max_length=100, description="Raw category name to be defined")


class JobCategoryDefinitionOutput(BaseModel):
    __doc__ = "Ensure Job Category Definitions do not exceed the limits in characters"
    description: str = Field(..., min_length=10, max_length=400)
    slug: str = Field(..., min_length=2, max_length=60, pattern=r"^[a-z0-9-]+$")
    seo_description: str = Field(..., min_length=50, max_length=255)


class JobCategoryDefinitionAgent(BaseAgent):
    __doc__ = (
        "This agent takes a raw category name and produces a complete definition "
        "ready for the JobCategory model."
    )
    name = "job_category_definition"
    description = (
        "Generates a human-friendly description, URL slug, and SEO meta description "
        "for a new job-portal category."
    )

    def system_prompt(self) -> str:
        return (
            "You are a job-portal taxonomist and SEO specialist. "
            "Given only a category name, you must:\n"
            "1. Write a concise but informative description (≈ 40–80 words) explaining what jobs belong to this category.\n"
            "2. Produce a clean, kebab-case slug suitable for URLs (max 60 chars).\n"
            "3. Craft a 150–160 character SEO description optimized for search results.\n\n"
            "Keep the tone professional and inclusive. "
            "Return valid JSON only, no extra commentary."
        )

    def prompt(self, input_model: JobCategoryNameInput) -> str:
        return (
            f'Category name: "{input_model.category_name.strip()}"\n\n'
            f"Respond in JSON:\n"
            f'{{\n'
            f'  "description": "<Human description>",\n'
            f'  "slug": "<kebab-case-slug>",\n'
            f'  "seo_description": "<SEO meta description>"\n'
            f'}}'
        )

    def output_model(self) -> type[BaseModel]:
        return JobCategoryDefinitionOutput

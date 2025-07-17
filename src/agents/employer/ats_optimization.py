from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from src.models.base import utc_time


class KeywordSourceType(str, Enum):
    INDUSTRY_TAXONOMY = "industry_taxonomy"
    PEER_JOBS = "peer_jobs"
    PARSED_CVS = "parsed_cvs"


class KeywordSource(BaseModel):
    keyword: str
    frequency: int = Field(ge=0)
    source_type: KeywordSourceType
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class SuggestionImpact(BaseModel):
    estimated_score_increase: int = Field(ge=0, le=30)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class AIEnhancementSuggestion(BaseModel):
    field: str
    action: str = Field(description="replace | append | delete")
    current: Optional[str] = None
    recommended: Optional[str] = None
    keywords_added: List[str] = Field(default_factory=list)
    impact: SuggestionImpact


# ---------- Agent I/O -------------------------------------------------
class ATSOptimisationInput(BaseModel):
    """
    Minimal input required to produce an AI-powered ATS report.
    The agent will perform its own keyword mining internally.
    """
    job_id: str
    title: str
    description: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None


class ATSOptimisationOutput(BaseModel):
    """
    Structured AI recommendations that can be displayed/edited by the recruiter.
    """
    generated_at: str = Field(default_factory=lambda: utc_time().isoformat())
    suggestions: List[AIEnhancementSuggestion]
    top_missing_keywords: List[str] = Field(
        description="Top 5 missing keywords ordered by impact"
    )



# ------------------------------------------------------------------
# AGENT – AI ATS Optimiser
# ------------------------------------------------------------------
class ATSOptimiseAgent(BaseAgent):
    """
    Generates AI-driven ATS optimisation suggestions for an existing Job record.
    Follows the same BaseAgent pattern already established in the project.
    """

    name: str = "ats_optimise"
    description: str = (
        "Produces concrete, AI-generated recommendations to boost a job post’s "
        "ATS discoverability and overall quality score."
    )

    def system_prompt(self) -> str:
        return (
            "You are an expert ATS (Applicant Tracking System) optimisation specialist "
            "with deep knowledge of South-African hiring practices. "
            "Your ONLY task is to return valid JSON that matches the `ATSOptimisationOutput` schema. "
            "Each suggestion must be actionable and measurable. "
            "Always prioritise high-impact keywords that are missing from the job description or skills lists."
        )

    def prompt(self, input_model: ATSOptimisationInput) -> str:
        location = ", ".join(filter(None, [input_model.city, input_model.province, input_model.country]))
        return (
            f"Optimise the following job post for ATS performance:\n\n"
            f"Title: {input_model.title}\n"
            f"Location: {location or 'Not specified'}\n"
            f"Description:\n{input_model.description}\n\n"
            f"Required Skills: {', '.join(input_model.required_skills) or 'None'}\n"
            f"Preferred Skills: {', '.join(input_model.preferred_skills) or 'None'}\n\n"
            "Return JSON only."
        )

    def output_model(self) -> Type[BaseModel]:
        return ATSOptimisationOutput

        
        
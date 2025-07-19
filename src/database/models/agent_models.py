
# src/database/models/agent_models.py
from typing import List
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class CVOptimizationSuggestion(BaseModel):
    summary: str
    suggested_changes: List[str]
    ats_keywords: List[str]

    model_config = ConfigDict(from_attributes=True)


class CoverLetterOutput(BaseModel):
    opening: str
    body: str
    closing: str

    model_config = ConfigDict(from_attributes=True)


class JobMatchInsights(BaseModel):
    match_score: float
    reasons: List[str]
    suggested_improvements: List[str]
    model_config = ConfigDict(from_attributes=True)


class JobPostInsights(BaseModel):
    clarity_score: float
    salary_benchmark: str
    missing_information: List[str]
    suggestions: List[str]

    model_config = ConfigDict(from_attributes=True)


class CandidateBenchmarkReport(BaseModel):
    """
    Comprehensive candidate evaluation report containing dual-perspective insights
    """
    summary: str = Field(
        description="Concise overall assessment of candidate-job fit"
    )
    percentile_rank: float = Field(
        ge=0, le=100,
        description="Candidate's competitive position percentile (0-100 scale)"
    )
    key_strengths: List[str] = Field(
        description="Candidate's strongest qualifications relative to position"
    )
    development_areas: List[str] = Field(
        description="Areas needing improvement for this specific role"
    )
    employer_insights: Optional[List[str]] = Field(
        default=None,
        description="Hiring considerations specific to employer perspective"
    )
    candidate_insights: Optional[List[str]] = Field(
        default=None,
        description="Career development insights specific to candidate perspective"
    )
    interview_indicators: Optional[List[str]] = Field(
        default=None,
        description="Key areas to explore during interviews (employer only)"
    )
    cv_optimization_tips: Optional[List[str]] = Field(
        default=None,
        description="Specific CV improvements for this role (candidate only)"
    )
    risk_factors: Optional[List[str]] = Field(
        default=None,
        description="Potential concerns about candidate fit (employer only)"
    )
    growth_opportunities: Optional[List[str]] = Field(
        default=None,
        description="Career development paths (candidate only)"
    )

    model_config = ConfigDict(from_attributes=True)
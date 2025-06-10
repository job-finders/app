# agents/schemas.py
from typing import List

from pydantic import BaseModel, ConfigDict


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
    strength_summary: str
    improvement_areas: List[str]
    percentile_rank: float

    model_config = ConfigDict(from_attributes=True)

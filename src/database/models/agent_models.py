# agents/schemas.py
from pydantic import BaseModel
from typing import List, Optional

class CVOptimizationSuggestion(BaseModel):
    summary: str
    suggested_changes: List[str]
    ats_keywords: List[str]

class CoverLetterOutput(BaseModel):
    opening: str
    body: str
    closing: str

class JobMatchInsights(BaseModel):
    match_score: float
    reasons: List[str]
    suggested_improvements: List[str]

class JobPostInsights(BaseModel):
    clarity_score: float
    salary_benchmark: str
    missing_information: List[str]
    suggestions: List[str]

class CandidateBenchmarkReport(BaseModel):
    strength_summary: str
    improvement_areas: List[str]
    percentile_rank: float

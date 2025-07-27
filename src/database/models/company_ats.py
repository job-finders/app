# src/models/ats_report.py  (or wherever your models live)
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, computed_field
from uuid import uuid4

from src.database.constants import utc_time


# ------------------------------------------------------------------
# Domain models (same as before)
# ------------------------------------------------------------------
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


class ATSOptimisationInput(BaseModel):
    job_id: str
    title: str
    description: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None


class ATSOptimisationOutput(BaseModel):
    generated_at: str = Field(default_factory=lambda: utc_time().isoformat())
    suggestions: List[AIEnhancementSuggestion]
    top_missing_keywords: List[str] = Field(
        description="Top 5 missing keywords ordered by impact"
    )


# ------------------------------------------------------------------
# Tool interfaces and default implementations
# ------------------------------------------------------------------


class KeywordTool(ABC):
    source_type: KeywordSourceType

    @abstractmethod
    def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        ...

class ATSScoreBreakdown(BaseModel):
    title_score: float = 0
    skills_score: float = 0
    description_score: float = 0
    formatting_score: float = 0
    experience_level_score: float = 0

    @computed_field
    @property
    def total(self) -> int:
        return min(
            int(
                0.25 * self.title_score
                + 0.30 * self.skills_score
                + 0.20 * self.description_score
                + 0.15 * self.formatting_score
                + 0.10 * self.experience_level_score
            ),
            100,
        )


class AIATSReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    generated_at: str = Field(default_factory=lambda: utc_time().isoformat())

    score_breakdown: ATSScoreBreakdown
    matched_keywords: List[KeywordSource]
    missing_keywords: List[KeywordSource]
    suggestions: List[AIEnhancementSuggestion]

    keyword_corpora: List[str] = ["industry_taxonomy", "peer_jobs", "parsed_cvs"]

    @computed_field
    @property
    def ai_enhanced_score(self) -> int:
        uplift = sum(s.impact.estimated_score_increase for s in self.suggestions)
        return min(self.score_breakdown.total + uplift, 100)

    @computed_field
    @property
    def top_5_missing(self) -> List[str]:
        return [
            kw.keyword
            for kw in sorted(
                self.missing_keywords, key=lambda k: k.frequency * k.weight, reverse=True
            )[:5]
        ]
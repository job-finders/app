from __future__ import annotations
import math
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from src.models.base import utc_time
from .base import BaseAgent

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
from abc import ABC, abstractmethod


class KeywordTool(ABC):
    source_type: KeywordSourceType

    @abstractmethod
    def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        ...


class IndustryTaxonomyTool(KeywordTool):
    source_type = KeywordSourceType.INDUSTRY_TAXONOMY

    def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        return [("python", 42), ("django", 18)]


class PeerJobsTool(KeywordTool):
    source_type = KeywordSourceType.PEER_JOBS

    def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        return [("rest api", 30), ("postgresql", 25)]


class ParsedCVsTool(KeywordTool):
    source_type = KeywordSourceType.PARSED_CVS

    def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        return [("fastapi", 20), ("asyncio", 12)]


# ------------------------------------------------------------------
# Agent
# ------------------------------------------------------------------
class ATSOptimiseAgent(BaseAgent):
    """
        This agent generates AI-driven ATS optimisation suggestions for an existing Job record.
        Helps improve job visibility and applicant matching by suggesting keyword enhancements.
        Uses pluggable keyword tools for high-precision mining.

    """
    name: str = "ats_optimise"
    description: str = (
        "Generates AI-driven ATS optimisation suggestions for an existing Job record. "
        "Uses pluggable keyword tools for high-precision mining."
    )

    def __init__(self, tools: Optional[List[KeywordTool]] = None):
        super().__init__()
        self.tools: List[KeywordTool] = tools or [
            IndustryTaxonomyTool(),
            PeerJobsTool(),
            ParsedCVsTool(),
        ]

    # ---------- Prompts ----------
    def system_prompt(self) -> str:
        return (
            "You are an expert ATS optimisation specialist. "
            "Return valid JSON matching `ATSOptimisationOutput`. "
            "Only use keywords provided in the mined list; do not invent new ones."
        )

    def prompt(self, input_model: ATSOptimisationInput) -> str:
        location = ", ".join(filter(None, [input_model.city, input_model.province, input_model.country]))
        mined = self._mine_keywords(input_model)
        kw_context = "\n".join(
            f"{i+1}. {ks.keyword} (src={ks.source_type}, weight={ks.weight}, freq={ks.frequency})"
            for i, ks in enumerate(mined[:20])
        )
        return (
            f"Title: {input_model.title}\n"
            f"Location: {location or 'Not specified'}\n\n"
            f"Description:\n{input_model.description}\n\n"
            f"Required Skills: {', '.join(input_model.required_skills)}\n"
            f"Preferred Skills: {', '.join(input_model.preferred_skills)}\n\n"
            f"Top mined missing keywords:\n{kw_context}\n\n"
            "Return JSON only."
        )

    def output_model(self):
        return ATSOptimisationOutput

    # ---------- Mining logic ----------
    def _mine_keywords(self, job: ATSOptimisationInput) -> List[KeywordSource]:
        """
        1. Pull raw keywords from every tool.
        2. Merge + TF-IDF weighting.
        3. Remove duplicates & already-present terms.
        """
        from collections import Counter
        import re

        # 1. Aggregate raw contributions
        corpus: List[Counter] = []
        for tool in self.tools:
            raw = tool.fetch(job)
            counter = Counter({kw: freq for kw, freq in raw})
            corpus.append(counter)

        # 2. Compute TF-IDF across tools (treat each tool as a 'document')
        def _tf_idf(corpus: List[Counter]) -> Counter:
            df = Counter()
            for doc in corpus:
                for term in doc:
                    df[term] += 1
            N = len(corpus)
            tf_idf_scores = Counter()
            for doc in corpus:
                total = max(sum(doc.values()), 1)
                for term, cnt in doc.items():
                    tf_idf_scores[term] += (cnt / total) * (math.log(N / df[term]) + 1)
            return tf_idf_scores

        tf_idf_scores = _tf_idf(corpus)

        # 3. Remove already-present terms
        already = set(re.findall(r"\b\w+\b", " ".join([
            job.description,
            *job.required_skills,
            *job.preferred_skills
        ]).lower()))

        mined = []
        for kw, score in tf_idf_scores.most_common():
            if kw.lower() in already:
                continue
            # Map back to source types
            for tool in self.tools:
                tool_counter = corpus[self.tools.index(tool)]
                freq = tool_counter.get(kw, 0)
                if freq:
                    mined.append(
                        KeywordSource(
                            keyword=kw,
                            frequency=freq,
                            source_type=tool.source_type,
                            weight=round(score, 3),
                        )
                    )
        return mined
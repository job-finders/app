from __future__ import annotations
import math
from typing import List, Optional
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field
from enum import Enum

from src.models.base import utc_time
from src.agents.employer.llm_keyword_miner import LLMKeywordMinerAgent, LLMKeywordMiningTool
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

class ATSKeywordSuggestionAgent(BaseAgent):
    """
        This agent generates ATS optimisation suggestions based on job descriptions.
        Helps enhance Job Visibility and candidate matching by suggesting missing keywords.
        Keyword mining is done using a combination of classic tools and an LLM fallback.
        
    Keyword arguments:
    argument -- description
    Return: return_description
    """
    
    name: str = "ats_optimise"
    description: str = (
        "Generates AI-driven ATS optimisation suggestions. "
        "Falls back to an LLM keyword miner when classic sources are insufficient."
    )

    def __init__(
        self,
        tools: Optional[List[KeywordTool]] = None,
        fallback_threshold: int = 5,
    ):
        super().__init__()
        self.tools: List[KeywordTool] = tools or [
            IndustryTaxonomyTool(),
            PeerJobsTool(),
            ParsedCVsTool(),
        ]
        # Always add the LLM tool last; we decide at runtime whether to use it
        self.llm_tool = LLMKeywordMiningTool(LLMKeywordMinerAgent())
        self.fallback_threshold = fallback_threshold

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
        """sumary_line
            Keyword mining logic that combines classic tools and LLM fallback.
        Keyword arguments:
        argument -- description
        Return: return_description
        """
        
        from collections import Counter
        import re
        import math

        # 1. Classic tools
        corpus: List[Counter] = []
        for tool in self.tools:
            raw = tool.fetch(job)
            corpus.append(Counter({kw: f for kw, f in raw}))

        # 2. Determine if we need fallback
        classic_keywords = set()
        for c in corpus:
            classic_keywords.update(c.keys())
        if len(classic_keywords) < self.fallback_threshold:
            # 3. Run LLM tool and append
            llm_counter = Counter({kw: f for kw, f in self.llm_tool.fetch(job)})
            corpus.append(llm_counter)

        # 4. TF-IDF as before
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

        # 5. Remove already-present terms
        already = set(re.findall(r"\b\w+\b", " ".join([
            job.description,
            *job.required_skills,
            *job.preferred_skills
        ]).lower()))

        mined = []
        for kw, score in tf_idf_scores.most_common():
            if kw.lower() in already:
                continue
            for tool in self.tools + [self.llm_tool]:
                tool_counter = (
                    corpus[self.tools.index(tool)]
                    if tool in self.tools
                    else corpus[-1]  # LLM
                )
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
from __future__ import annotations

import asyncio
import inspect
from typing import List, Optional

from src.agents.base import BaseAgent
from src.agents.employer.llm_keyword_miner import LLMKeywordMinerAgent, LLMKeywordMiningTool
from src.database.models.company_ats import KeywordTool, KeywordSourceType, ATSOptimisationInput, ATSOptimisationOutput, \
    KeywordSource


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

    def __init__(self, user_id: str, tools: Optional[List[KeywordTool]] = None, fallback_threshold: int = 5):
        super().__init__(user_id=user_id)
        if self.logger:
            self.logger.info("Initialized Keyword Suggestion Agent Tool")
        self.tools: List[KeywordTool] = tools or [
            IndustryTaxonomyTool(),
            PeerJobsTool(),
            ParsedCVsTool(),
        ]
        # Always add the LLM tool last; we decide at runtime whether to use it
        self.llm_tool = LLMKeywordMiningTool(LLMKeywordMinerAgent(user_id=user_id))
        self.fallback_threshold = fallback_threshold

    # ---------- Prompts ----------
    def system_prompt(self) -> str:
        return (
            "You are an expert ATS optimisation specialist. "
            "Return valid JSON matching `ATSOptimisationOutput`. "
            "Only use keywords provided in the mined list; do not invent new ones."
        )

    async def prompt(self, input_model: ATSOptimisationInput) -> str:
        location = ", ".join(filter(None, [input_model.city, input_model.province, input_model.country]))
        mined = await self._mine_keywords(job=input_model)
        if mined and self.logger:
            self.logger.info(f"MINED KEYWORDS : {mined}")

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
    async def _mine_keywords(self, job: ATSOptimisationInput) -> List[KeywordSource]:
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
            if inspect.iscoroutine(raw):
                raw = await raw
            corpus.append(Counter({kw: f for kw, f in raw}))

        # 2. Determine if we need fallback
        classic_keywords = set()
        for c in corpus:
            classic_keywords.update(c.keys())
        if len(classic_keywords) < self.fallback_threshold:
            # 3. Run LLM tool and append
            from_llm = await self.llm_tool.fetch(job=job)
            llm_counter = Counter({kw: f for kw, f in from_llm})
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
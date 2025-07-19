from __future__ import annotations
        
from collections import Counter
import re
import math

import asyncio
import inspect
from typing import List, Optional

from src.agents.base import BaseAgent
from src.agents.employer.llm_keyword_miner import LLMKeywordMinerAgent, LLMKeywordMiningTool
from src.database.models.company_ats import KeywordTool, KeywordSourceType, ATSOptimisationInput, ATSOptimisationOutput, \
    KeywordSource
from src.utils import tokenize

class IndustryTaxonomyTool(KeywordTool):
    """sumary_line
        This tool finds and returns keywords based on the Industry Taxonomy of the Industry 
        The Job Being created belongs in, 
        Taxonomy is mainly based on the JobCategory class 
    Keyword arguments:
    argument -- description
    Return: return_description
    """
    
    source_type = KeywordSourceType.INDUSTRY_TAXONOMY

    def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        return [("python", 42), ("django", 18)]


class PeerJobsTool(KeywordTool):
    """sumary_line
        
        This tool will find keywords based on the jobs similar to the job being created, 
        the keywords retained will be passed onto the LLM for selection based on the criteria 
        where there should be an improvement on ATS Rating and also Relevancy to the Job Being 
        Created.

    Keyword arguments:
    argument -- description
    Return: return_description
    """
    
    source_type = KeywordSourceType.PEER_JOBS

    def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        return [("rest api", 30), ("postgresql", 25)]


class ParsedCVsTool(KeywordTool):
    """sumary_line
        This tool takes a job being created find jobs similar to this jobs but with applications - 
        it then takes the Resumes that where used for this applications, obtains unique keywords 
        that are also not found in the present job descriptions. 
        sends all keywords to the LLM so see which keywords the LLM selects for improving the Job 
        Based on ATS and Relevancy to the Job.
    Keyword arguments:
    argument -- description
    Return: return_description
    """
    
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

        This agents gets a list of keywords based on the Job Description from Old Jobs and
        Previous Resumes which where successfull in applying for jobs similar to the Job being 
        created.

        It then takes those keywords 
        
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
            "You are an expert ATS optimization specialist. Your task is to analyze job descriptions and "
            "generate enhancement suggestions with strict adherence to these rules:\n"
            "1. ONLY use keywords from the provided 'Mined Keywords' list\n"
            "2. For suggestions:\n"
            "   - Each must target a specific 'field' (description/required_skills/preferred_skills)\n"
            "   - Specify 'action' type: 'append' (add keywords) or 'replace' (modify text)\n"
            "   - For 'replace': provide both 'current' snippet and 'recommended' text\n"
            "   - For 'append': list exact 'keywords_added'\n"
            "   - Include impact assessment with:\n"
            "        • estimated_score_increase (0-30)\n"
            "        • confidence (0.0-1.0)\n"
            "        • brief reasoning\n"
            "3. For top_missing_keywords: Select exactly 5 highest-impact keywords\n"
            "4. Output MUST be pure JSON matching this schema:\n"
            "{\n"
            "  \"suggestions\": [\n"
            "    {\n"
            "      \"field\": \"description\",\n"
            "      \"action\": \"append\",\n"
            "      \"keywords_added\": [\"keyword1\", \"keyword2\"],\n"
            "      \"impact\": {\n"
            "        \"estimated_score_increase\": 8,\n"
            "        \"confidence\": 0.85,\n"
            "        \"reasoning\": \"Explanation\"\n"
            "      }\n"
            "    },\n"
            "    {\n"
            "      \"field\": \"required_skills\",\n"
            "      \"action\": \"replace\",\n"
            "      \"current\": \"Current text snippet\",\n"
            "      \"recommended\": \"Improved text with keywords\",\n"
            "      \"keywords_added\": [\"keyword3\"],\n"
            "      \"impact\": {...}\n"
            "    }\n"
            "  ],\n"
            "  \"top_missing_keywords\": [\"kw1\", \"kw2\", \"kw3\", \"kw4\", \"kw5\"]\n"
            "}"
        )

    async def prompt(self, input_model: ATSOptimisationInput) -> str:
        location = ", ".join(filter(None, [input_model.city, input_model.province, input_model.country]))
        mined = await self._mine_keywords(job=input_model)
        
        # Tokenize existing content to identify present terms
        existing_tokens = set(
            token for field in [
                input_model.description,
                *input_model.required_skills,
                *input_model.preferred_skills
            ] 
            for token in tokenize(field)
        )
        
        # Format keyword context with source metadata
        kw_context = "\n".join(
            f"- {ks.keyword} (src: {ks.source_type.value}, weight: {ks.weight}, freq: {ks.frequency})"
            for ks in mined[:15]
        )
        
        # Format existing tokens for display
        excluded_display = ', '.join(sorted(existing_tokens)[:50])
        if len(existing_tokens) > 50:
            excluded_display += f" ... (+{len(existing_tokens)-50} more)"
        
        return (
            "## JOB ANALYSIS REQUEST ##\n"
            f"JOB ID: {input_model.job_id}\n"
            f"TITLE: {input_model.title}\n"
            f"LOCATION: {location or 'Unspecified'}\n\n"
            "## EXISTING CONTENT ##\n"
            f"DESCRIPTION:\n{input_model.description}\n\n"
            f"REQUIRED SKILLS: {', '.join(input_model.required_skills) or 'None'}\n"
            f"PREFERRED SKILLS: {', '.join(input_model.preferred_skills) or 'None'}\n\n"
            "## EXISTING TOKENS (ALREADY PRESENT) ##\n"
            f"{excluded_display}\n\n"
            "## MINED KEYWORDS (MISSING FROM ABOVE) ##\n"
            f"{kw_context}\n\n"
            "## ACTION REQUIRED ##\n"
            "1. Generate 3-5 enhancement suggestions:\n"
            "   - For TEXT FIELDS: Use 'replace' with exact text snippets\n"
            "   - For SKILL LISTS: Use 'append' with specific keywords\n"
            "   - IMPACT: Estimate score increase (1-5 per keyword)\n"
            "2. Select top 5 missing keywords:\n"
            "   - MUST NOT be in existing tokens above\n"
            "   - Ordered by: [weight × frequency] > source priority\n"
            "   - Source priority: peer_jobs > industry_taxonomy > parsed_cvs\n"
            "3. OUTPUT: Pure JSON only - no commentary"
        )

    def output_model(self) -> ATSOptimisationOutput:
        return ATSOptimisationOutput

    # ---------- Mining logic ----------
    async def _mine_keywords(self, job: ATSOptimisationInput) -> List[KeywordSource]:
        """sumary_line
            Keyword mining logic that combines classic tools and LLM fallback.

            The Keywords will contain words that are found on jobs similar to the one being created but 
            not present on the job being created.

        Keyword arguments:
        argument -- description
        Return: return_description
        """

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
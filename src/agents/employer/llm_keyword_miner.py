from typing import List, Optional
from pydantic import BaseModel, Field

from src.database.models.company_ats import KeywordTool, KeywordSourceType, ATSOptimisationInput
from src.agents.base import BaseAgent  # your project’s agent base


class LLMKeywordMiningInput(BaseModel):
    title: str
    description: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)


class LLMKeywordMiningOutput(BaseModel):
    keywords: List[str] = Field(description="Keywords the LLM considers high-impact")


class LLMKeywordMinerAgent(BaseAgent):
    """
    Tiny inner agent whose only job is to read a job post
    and return a list of ATS-friendly keywords.
    """
    name: str = "llm_keyword_miner"
    description: str = "LLM-powered keyword extractor used as a fallback."

    def system_prompt(self) -> str:
        return (
            "You are an expert recruiter. "
            "Given a job post, return the 15 most important ATS keywords "
            "that do NOT already appear literally in the description or skills. "
            "Output a JSON array of strings only, e.g. [\"react\", \"typescript\"]."
        )

    def prompt(self, input_model: LLMKeywordMiningInput) -> str:
        return (
            f"Title: {input_model.title}\n"
            f"Description: {input_model.description}\n"
            f"Required Skills: {', '.join(input_model.required_skills)}\n"
            f"Preferred Skills: {', '.join(input_model.preferred_skills)}\n"
            "Return JSON array only."
        )

    def output_model(self):
        return LLMKeywordMiningOutput


# Thin wrapper so it conforms to KeywordTool interface
class LLMKeywordMiningTool(KeywordTool):
    source_type = KeywordSourceType.INDUSTRY_TAXONOMY  # re-use; any value is OK

    def __init__(self, agent: LLMKeywordMinerAgent):
        self.agent = agent

    async def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        llm_input = LLMKeywordMiningInput(
            title=job.title,
            description=job.description,
            required_skills=job.required_skills,
            preferred_skills=job.preferred_skills,
        )
        # noinspection PyTypeChecker
        llm_output: LLMKeywordMiningOutput = await self.agent.run(llm_input)
        # simulate frequency = 1 for every keyword
        return [(kw, 1) for kw in llm_output.keywords]
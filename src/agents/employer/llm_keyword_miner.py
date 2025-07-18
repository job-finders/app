from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError

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
            "You are an expert recruiter using your knowledge to optimize job posts for Applicant Tracking Systems (ATS).\n"
            "Your task is to extract up to 15 high-impact keywords that are relevant to the role but do NOT appear literally in the job description or skills.\n"
            "You must ONLY return a **single JSON object** matching this exact structure:\n\n"
            '{\n  "keywords": ["keyword1", "keyword2", ...]\n}\n\n'
            "Strict rules:\n"
            "- DO NOT include any reasoning, explanations, markdown, or narrative.\n"
            "- DO NOT include any text outside of the JSON.\n"
            "- DO NOT format with comments or extra sections.\n"
            "- DO NOT mention 'Here is the JSON' or anything similar.\n"
            "- You must return valid JSON. No trailing commas, no malformed syntax.\n"
        )

    def prompt(self, input_model: LLMKeywordMiningInput) -> str:
        return (
            f"Title: {input_model.title}\n"
            f"Description: {input_model.description}\n"
            f"Required Skills: {', '.join(input_model.required_skills)}\n"
            f"Preferred Skills: {', '.join(input_model.preferred_skills)}\n"
            "Return only the JSON object with the 'keywords' list as described."
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
        try:
            llm_output: LLMKeywordMiningOutput = await self.agent.run(input_model=llm_input)
        except ValidationError as e:
            print(str(e))
            return []
        # simulate frequency = 1 for every keyword
        return [(kw, 1) for kw in llm_output.keywords]
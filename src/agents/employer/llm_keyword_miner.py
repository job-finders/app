from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError

from src.database.models import KeywordTool, KeywordSourceType, ATSOptimisationInput
from src.agents.base import BaseAgent  # your project’s agent base
from src.utils import tokenize

class LLMKeywordMiningInput(BaseModel):
    title: str
    description: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)


class LLMKeywordMiningOutput(BaseModel):
    keywords: List[str] = Field(description="Keywords the LLM considers high-impact")


class LLMKeywordMinerAgent(BaseAgent):
    """
    Precision keyword extractor using advanced tokenization to identify
    high-impact, missing terms for ATS optimization
    """
    name: str = "llm_keyword_miner"
    description: str = "Token-enhanced keyword extractor for ATS optimization"

    def system_prompt(self) -> str:
        return (
            "You are an ATS optimization specialist. Extract ONLY high-impact keywords that:\n"
            "1. Are industry-standard terms MISSING from the job content\n"
            "2. Directly relate to required/preferred skills\n"
            "3. Are proven to boost application visibility\n\n"
            "Output MUST be pure JSON matching this exact schema:\n"
            '{"keywords": ["term1", "term2", ...]}\n\n'
            "Strict Rules:\n"
            "- Return 8-15 keywords MAX\n"
            "- Never include terms present in tokenized content\n"
            "- Prioritize: technical skills > certifications > methodologies > tools\n"
            "- Exclude: company names, locations, soft skills\n"
            "- Format: Multi-word phrases in snake_case (rest_api)\n"
            "- Validation: Output must pass JSON.parse() with no errors\n"
            "- No additional text outside JSON structure"
        )

    def prompt(self, input_model: LLMKeywordMiningInput) -> str:
        # Extract and tokenize existing terms
        existing_terms = set(
            token for term in input_model.required_skills + input_model.preferred_skills
            for token in tokenize(term)
        )
        
        # Tokenize description and add to exclusion set
        existing_terms.update(tokenize(input_model.description))
        
        # Format excluded terms for display
        excluded_display = ', '.join(sorted(existing_terms)[:50])
        if len(existing_terms) > 50:
            excluded_display += f" ... (+{len(existing_terms)-50} more)"

        return (
            "## JOB ANALYSIS FOR KEYWORD MINING ##\n"
            f"TITLE: {input_model.title}\n\n"
            "## EXISTING CONTENT (TOKENIZED) ##\n"
            f"DESCRIPTION: {input_model.description[:800]}{'...' if len(input_model.description) > 800 else ''}\n\n"
            f"REQUIRED SKILLS: {', '.join(input_model.required_skills) or 'None'}\n"
            f"PREFERRED SKILLS: {', '.join(input_model.preferred_skills) or 'None'}\n\n"
            "## EXCLUDED TOKENS (DO NOT USE) ##\n"
            f"{excluded_display}\n\n"
            "## INSTRUCTIONS ##\n"
            "1. Identify 8-15 high-value ATS keywords MISSING from tokenized content\n"
            "2. Filter by: Technical relevance > Industry prevalence > ATS impact\n"
            "3. Format: snake_case for multi-word terms (kubernetes_operator)\n"
            "4. Output: ONLY valid JSON object - no commentary"
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
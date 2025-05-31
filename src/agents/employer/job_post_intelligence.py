# agents/employer/job_post_intelligence.py
from typing import Type
from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.database.models.agent_models import JobPostInsights


class EnhanceJobPostInput(BaseModel):
    title: str
    description: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    position_type: Optional[str] = None


class EnhancedJobPost(BaseModel):
    title: Optional[str]
    description: Optional[str]
    skills: Optional[str]
    education: Optional[str]
    salary: Optional[str]



class JobPostAgent(BaseAgent):
    name = "job_post_intelligence"
    description = "Analyzes job post quality, clarity, and competitiveness based on salary, skills, and completeness."

    class Input(BaseModel):
        job_post_text: str

    def system_prompt(self) -> str:
        return (
            "You are an expert in recruitment and job post optimization. "
            "Your role is to analyze job posts for clarity, market competitiveness, and completeness. "
            "Return structured insights, and suggest improvements where necessary."
        )

    def prompt(self, input: Input) -> str:
        return (
            f"Analyze the following job post:\n\n"
            f"{input.job_post_text.strip()}\n\n"
            f"Provide feedback on:\n"
            f"- Clarity\n"
            f"- Salary competitiveness\n"
            f"- Skill requirements\n"
            f"- Missing information\n"
            f"- Overall completeness\n\n"
            f"Respond in structured JSON using the defined schema."
        )

    def output_model(self) -> Type[BaseModel]:
        return JobPostInsights


# agents/employer/job_post_intelligence.py

class EnhanceJobPost(BaseAgent):
    name = "enhance_job_post"
    description = "Given partial job post description or title - create a detailed and enhanced job post."
    
    def system_prompt(self) -> str:
        return (
            "You are a professional job post generator for employers. "
            "You help them craft clear, attractive, and complete job posts tailored to their input."
        )

    def prompt(self, input: EnhanceJobPostInput) -> str:
        prompt = f"""
You are an expert job post generator.

Here is a partial job post provided by an employer:

- Title: {input.title}
- Description: {input.description}
- Salary Range: {input.salary_min or 'N/A'} - {input.salary_max or 'N/A'}
- Position Type: {input.position_type or 'Not specified'}

Generate an improved version of this job post. Your output should include:
- A more attractive and clear job title
- A detailed job description
- Recommended skills
- Suggested educational qualifications
- A competitive salary range suggestion (formatted in local currency, e.g., R35,000 - R50,000).
"""
        return prompt.strip()

    def output_model(self):
        return EnhancedJobPost

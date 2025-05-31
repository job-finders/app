# agents/employer/job_post_intelligence.py
from src.agents.base import BaseAgent
from src.database.models.agent_models import JobPostInsights


class JobPostAgent(BaseAgent):
    name = "job_post_intelligence"
    description = "Analyzes job post quality and market competitiveness."

    def prompt(self, job_post_text: str) -> str:
        return (
            f"Evaluate this job post for clarity, salary range, and completeness:\n{job_post_text}"
        )

    def output_model(self):
        return JobPostInsights

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


# agents/employer/job_post_intelligence.py

class EnhanceJobPost(BaseAgent):
    name = "enhance_job_post"
    description = "Given partial job post description or title - create a detailed and enhanced job post."

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

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

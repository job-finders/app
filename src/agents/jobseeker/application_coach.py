# agents/jobseeker/application_coach.py
from src.agents.base import BaseAgent
from src.database.models.agent_models import JobMatchInsights


class ApplicationCoachAgent(BaseAgent):
    name = "application_coach"
    description = "Analyzes your fit and offers advice for a job posting."

    def prompt(self, job_description: str, cv_text: str) -> str:
        return (
            f"Analyze this CV against the job post and suggest improvements:\n"
            f"Job: {job_description}\n\nCV: {cv_text}"
        )

    def output_model(self):
        return JobMatchInsights

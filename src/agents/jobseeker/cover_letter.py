# agents/jobseeker/cover_letter.py
from src.agents.base import BaseAgent
from src.database.models.agent_models import CoverLetterOutput


class CoverLetterAgent(BaseAgent):
    name = "cover_letter_writer"
    description = "Generates a tailored cover letter."

    def prompt(self, job_description: str, cv_text: str) -> str:
        return (
            f"Write a professional cover letter for this job:\n{job_description}\n\n"
            f"Based on this CV:\n{cv_text}\n\nRespond with opening, body, and closing."
        )

    def output_model(self):
        return CoverLetterOutput

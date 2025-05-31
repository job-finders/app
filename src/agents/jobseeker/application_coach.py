# agents/jobseeker/application_coach.py

from typing import Type
from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.database.models.agent_models import JobMatchInsights

# agents/jobseeker/application_coach.py

class ApplicationCoachAgent(BaseAgent):
    name = "application_coach"
    description = "Analyzes your CV and cover letter for a job and offers advice to improve."

    class Input(BaseModel):
        job_post: str
        cv_text: str
        cover_letter: Optional[str] = None

    def system_prompt(self) -> str:
        return (
            "You are an expert career coach. Help the candidate assess and improve their application. "
            "Analyze the job posting, CV, and (optionally) cover letter. "
            "Provide insights on alignment, improvements, and actionable advice. "
            "Encourage the candidate while maintaining a helpful tone."
        )

    def prompt(self, input: Input) -> str:
        prompt = (
            f"Job Posting:\n{input.job_post.strip()}\n\n"
            f"Candidate CV:\n{input.cv_text.strip()}\n\n"
            f"Please analyze:\n"
            f"- Relevance of experience\n"
            f"- Strengths and gaps\n"
            f"- Suggestions to improve CV\n"
        )
        if input.cover_letter:
            prompt += (
                f"\nCover Letter:\n{input.cover_letter.strip()}\n\n"
                f"Also analyze:\n"
                f"- Tone and structure of the cover letter\n"
                f"- Alignment with job description\n"
                f"- Suggestions for improvement"
            )

        prompt += "\n\nClose with a short motivational note."
        return prompt

    def output_model(self) -> Type[BaseModel]:
        return JobMatchInsights


# agents/jobseeker/cover_letter.py

from typing import Optional, Type
from pydantic import BaseModel
from src.agents.base import BaseAgent
from src.database.models.agent_models import CoverLetterOutput


class CoverLetterInput(BaseModel):
    job_description: str
    cv_text: str
    tone: Optional[str] = "professional"  # Can be: "professional", "friendly", "enthusiastic", etc.


class CoverLetterAgent(BaseAgent):
    name = "cover_letter_writer"
    description = "Generates a personalized, persuasive, and well-structured cover letter."

    def system_prompt(self) -> str:
        return (
            "You are an expert in writing personalized and compelling cover letters that align a candidate's CV "
            "with the job description. Ensure the tone matches the user's preference and follow a professional structure."
        )

    def prompt(self, input: CoverLetterInput) -> str:
        return (
            f"Write a {input.tone.lower()} cover letter for the following job description and candidate profile.\n\n"
            f"Job Description:\n{input.job_description.strip()}\n\n"
            f"Candidate CV:\n{input.cv_text.strip()}\n\n"
            f"The letter should:\n"
            f"- Be 3 to 5 paragraphs long\n"
            f"- Clearly express interest in the role\n"
            f"- Highlight key relevant experiences\n"
            f"- Use a {input.tone.lower()} tone\n"
            f"- Conclude with a strong and confident closing statement\n\n"
            f"Respond with the full cover letter text only."
        )

    def output_model(self) -> Type[BaseModel]:
        return CoverLetterOutput

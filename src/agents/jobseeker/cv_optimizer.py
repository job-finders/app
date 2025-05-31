# agents/jobseeker/cover_letter.py

from typing import Optional, Type
from pydantic import BaseModel
from src.agents.base import BaseAgent
from src.database.models.agent_models import CoverLetterOutput


class CoverLetterInput(BaseModel):
    job_description: str
    cv_text: str
    tone: Optional[str] = "professional"  # professional, friendly, persuasive, formal, etc.
    highlight_skills: Optional[str] = None  # Optional field to focus on certain skills or achievements


class CoverLetterAgent(BaseAgent):
    name = "cover_letter_writer"
    description = (
        "Generates a customized cover letter aligning the user's CV with a specific job description. "
        "Supports tone and skill highlighting preferences."
    )

    def system_prompt(self) -> str:
        return (
            "You are a career writing assistant specializing in personalized cover letters. "
            "Your goal is to craft professional, persuasive, and job-specific letters that effectively showcase a candidate's experience."
        )

    def prompt(self, input: CoverLetterInput) -> str:
        prompt = (
            f"Write a {input.tone.lower()} cover letter tailored to the following job description and candidate CV.\n\n"
            f"Job Description:\n{input.job_description.strip()}\n\n"
            f"Candidate CV:\n{input.cv_text.strip()}\n\n"
        )

        if input.highlight_skills:
            prompt += (
                f"The candidate wants to highlight the following skills or achievements:\n"
                f"{input.highlight_skills.strip()}\n\n"
            )

        prompt += (
            "The letter should:\n"
            "- Have a compelling opening\n"
            "- Be 3–5 concise paragraphs\n"
            "- Highlight experiences most relevant to the job\n"
            "- Match the requested tone\n"
            "- End with a strong call to action\n\n"
            "Respond with the complete cover letter only. No commentary or headings."
        )

        return prompt

    def output_model(self) -> Type[BaseModel]:
        return CoverLetterOutput

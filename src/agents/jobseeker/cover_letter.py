# agents/jobseeker/cover_letter.py

from typing import Optional, Type
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent


class CoverLetterInput(BaseModel):
    """
    Input schema for generating a tailored cover letter.

    Attributes:
    - job_description: The full text of the job posting the user is applying to.
    - cv_text: The complete CV or resume text of the candidate.
    - tone: Desired tone of the letter (e.g., "professional", "friendly", "enthusiastic").
    """
    job_description: str = Field(..., description="The job description to tailor the cover letter to.")
    cv_text: str = Field(..., description="The candidate's CV or resume text.")
    tone: Optional[str] = Field("professional", description="Tone of the letter: professional, friendly, etc.")


class CoverLetterOutput(BaseModel):
    """
    Structured output of a generated cover letter, split into meaningful sections.

    Attributes:
    - opening: The introductory paragraph, expressing interest in the position.
    - body: One or more paragraphs connecting the candidate’s experience to the job.
    - closing: A strong and confident final paragraph expressing enthusiasm and next steps.
    """
    opening: str = Field(..., description="Opening paragraph of the letter.")
    body: str = Field(..., description="Main body with supporting qualifications and relevance.")
    closing: str = Field(..., description="Closing paragraph with a call to action or final impression.")

    class Config:
        from_attributes = True


class CoverLetterAgent(BaseAgent):
    name = "cover_letter_writer"
    description = "Generates a personalized, persuasive, and well-structured cover letter."

    def system_prompt(self) -> str:
        return (
            "You are an expert in writing personalized and compelling cover letters that align a candidate's CV "
            "with the job description. Ensure the tone matches the user's preference and follow a professional structure."
        )

    def prompt(self, cover_letter_input: CoverLetterInput) -> str:
        return (
            f"Write a {cover_letter_input.tone.lower()} cover letter for the following job description and candidate profile.\n\n"
            f"Job Description:\n{cover_letter_input.job_description.strip()}\n\n"
            f"Candidate CV:\n{cover_letter_input.cv_text.strip()}\n\n"
            f"The letter should:\n"
            f"- Be 3 to 5 paragraphs long\n"
            f"- Clearly express interest in the role\n"
            f"- Highlight key relevant experiences\n"
            f"- Use a {cover_letter_input.tone.lower()} tone\n"
            f"- Conclude with a strong and confident closing statement\n\n"
            f"Respond with the full cover letter text only."
        )

    def output_model(self) -> Type[BaseModel]:
        return CoverLetterOutput

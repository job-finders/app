# agents/jobseeker/application_coach.py

from typing import List, Optional, Type
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent


class JobMatchInsights(BaseModel):
    """
    Insights into how well the candidate matches a specific job.

    Attributes:
    - match_score: Estimated likelihood (0–100) the candidate will be shortlisted based on CV and cover letter.
    - fit_level: Textual label for score bucket (e.g., 'high', 'medium', 'low').
    - strengths: Relevant highlights from CV that match job requirements.
    - gaps: Key missing experiences or skills.
    - recommendations: Tips to improve the application for this job.
    - motivational_note: Friendly, encouraging statement for the jobseeker.
    """
    match_score: float = Field(..., ge=0.0, le=100.0, description="Estimated match percentage from 0 to 100.")
    fit_level: str = Field(..., description="Label for match score: 'high', 'medium', or 'low'.")
    strengths: List[str] = Field(default_factory=list, description="Matching strengths between CV and job.")
    gaps: List[str] = Field(default_factory=list, description="Missing skills or qualifications.")
    recommendations: List[str] = Field(default_factory=list, description="Suggestions to improve application.")
    motivational_note: Optional[str] = Field(None, description="Supportive message for the candidate.")

    class Config:
        from_attributes = True



class ApplicationCoachAgent(BaseAgent):
    name = "application_coach"
    description = "Evaluates how well a candidate matches a job and provides actionable feedback."

    class Input(BaseModel):
        job_post: str
        cv_text: str
        cover_letter: Optional[str] = None

    def system_prompt(self) -> str:
        return (
            "You are a smart career advisor. Analyze job descriptions against a candidate's CV and cover letter.\n"
            "Your job is to:\n"
            "- Score the likelihood the candidate could be shortlisted\n"
            "- Identify strengths and missing elements\n"
            "- Offer clear, practical improvement suggestions\n"
            "- Encourage the candidate with a positive tone\n\n"
            "Respond using the following structured fields:\n"
            "1. match_score (0–100)\n"
            "2. fit_level (low/medium/high)\n"
            "3. strengths (list)\n"
            "4. gaps (list)\n"
            "5. recommendations (list)\n"
            "6. motivational_note"
        )

    def prompt(self, input: Input) -> str:
        prompt = (
            f"Job Posting:\n{input.job_post.strip()}\n\n"
            f"Candidate CV:\n{input.cv_text.strip()}\n\n"
            f"Instructions:\n"
            f"- Estimate how well this candidate fits the role\n"
            f"- Provide a match_score out of 100\n"
            f"- Label the fit_level as 'low', 'medium', or 'high'\n"
            f"- Extract key strengths\n"
            f"- List missing qualifications or skills\n"
            f"- Give recommendations to improve chances\n")
        if input.cover_letter:
            prompt += (
                f"\nCover Letter:\n{input.cover_letter.strip()}\n"
                f"- Also analyze tone and alignment of the cover letter\n"
            )
        prompt += "\nFinish with a short motivational note."

        return prompt

    def output_model(self) -> Type[BaseModel]:
        return JobMatchInsights

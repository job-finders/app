# agents/employer/candidate_benchmark.py
from typing import Type, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent
from src.database.models import CandidateBenchmarkReport

class UserMode(str, Enum):
    EMPLOYER = "employer"
    EMPLOYEE = "employee"

class JobPostSummaryInput(BaseModel):
    ats_description: str

class CandidateBenchmarkAgent(BaseAgent):

    
    name = "candidate_benchmark"
    description = "Evaluates candidate CVs against job posts with dual perspective analysis"

    class Input(BaseModel):
        cv_text: str
        job_post: str
        mode: UserMode = Field(
            default=UserMode.EMPLOYER,
            description="Evaluation perspective: 'employer' or 'employee'"
        )

    def system_prompt(self) -> str:
        return (
            "You are a professional talent evaluation assistant. "
            "Your role is to analyze candidate CVs against job requirements from two perspectives:\n"
            "1. For EMPLOYERS: Evaluate candidate suitability and competitive positioning\n"
            "2. For EMPLOYEES: Provide actionable development insights\n"
            "Maintain professional tone and provide evidence-based assessments. "
            "Use industry-standard benchmarks and focus on measurable factors."
        )

    def prompt(self, input: Input) -> str:
        perspective_specific = {
            UserMode.EMPLOYER: (
                "### Employer Perspective Requirements:\n"
                "- Quantify candidate's competitive position against typical applicants\n"
                "- Identify strong alignment with role requirements\n"
                "- Flag potential hiring risks or concerns\n"
                "- Highlight unique value propositions\n"
                "- Recommend interview focus areas\n\n"
            ),
            UserMode.EMPLOYEE: (
                "### Employee Perspective Requirements:\n"
                "- Identify transferable skills and development opportunities\n"
                "- Suggest concrete CV improvements for this specific role\n"
                "- Provide career path alignment analysis\n"
                "- Recommend skill-building resources\n"
                "- Suggest complementary roles/industries\n\n"
            )
        }

        return (
            f"## Evaluation Context\n"
            f"Evaluation Mode: {input.mode.value.upper()}\n\n"
            f"## Job Post Details\n{input.job_post.strip()}\n\n"
            f"## Candidate CV\n{input.cv_text.strip()}\n\n"
            f"{perspective_specific[input.mode]}"
            f"## Required Analysis Output\n"
            f"Generate comprehensive benchmarking report including:\n"
            f"- Competitive positioning metrics\n"
            f"- Alignment analysis with role requirements\n"
            f"- Actionable recommendations specific to the perspective\n"
            f"- Evidence-based strengths and development areas\n\n"
            f"Structure your response in JSON format according to the schema."
        )

    def output_model(self) -> Type[CandidateBenchmarkReport]:
        return CandidateBenchmarkReport

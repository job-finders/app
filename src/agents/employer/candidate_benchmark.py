# agents/employer/candidate_benchmark.py

from typing import Type
from pydantic import BaseModel
from src.agents.base import BaseAgent
from src.database.models.agent_models import CandidateBenchmarkReport

class JobPostSummaryInput(BaseModel):
    ats_description: str

class CandidateBenchmarkAgent(BaseAgent):
    name = "candidate_benchmark"
    description = "Evaluates a candidate's CV against a full job post and provides benchmarking feedback."

    class Input(BaseModel):
        cv_text: str
        job_post: str  # Full job description including title, responsibilities, etc.

    def system_prompt(self) -> str:
        return (
            "You are a professional CV benchmarking assistant. "
            "Your job is to evaluate a candidate's CV against the full job post, comparing it to industry standards. "
            "You return structured insights including a percentile ranking, key strengths, areas for improvement, "
            "and job-specific recommendations to improve the CV's competitiveness."
        )

    def prompt(self, input: Input) -> str:
        return (
            f"Job Post:\n{input.job_post.strip()}\n\n"
            f"Candidate CV:\n{input.cv_text.strip()}\n\n"
            f"Evaluate the CV for this job post. Benchmark the candidate against typical applicants for this kind of role. "
            f"Return structured insights in JSON format, including:\n"
            f"- Estimated percentile rank\n"
            f"- Strong skills or qualifications\n"
            f"- Weaknesses or missing elements\n"
            f"- Specific suggestions to improve the CV"
        )

    def output_model(self) -> Type[BaseModel]:
        return CandidateBenchmarkReport

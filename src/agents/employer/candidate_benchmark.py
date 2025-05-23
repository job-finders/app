# agents/employer/candidate_benchmark.py
from src.agents.base import BaseAgent
from src.database.models.agent_models import CandidateBenchmarkReport


class CandidateBenchmarkAgent(BaseAgent):
    name = "candidate_benchmark"
    description = "Evaluates a candidate's CV against peers and industry standards."

    def prompt(self, cv_text: str, job_title: str) -> str:
        return (
            f"Assess this CV for a '{job_title}' position, and compare against typical candidates."
            f"Provide percentile ranking, strong points, and areas of improvement.\n\nCV:\n{cv_text}"
        )

    def output_model(self):
        return CandidateBenchmarkReport

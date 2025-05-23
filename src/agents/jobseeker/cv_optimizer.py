# agents/jobseeker/cv_optimizer.py
from src.agents.base import BaseAgent
from src.database.models.agent_models import CVOptimizationSuggestion


class CVOptimizerAgent(BaseAgent):
    name = "cv_optimizer"
    description = "Suggests ATS-optimized improvements for a CV."

    def prompt(self, cv_text: str, target_role: str) -> str:
        return (
            f"You're an ATS system expert. Analyze the following CV for a '{target_role}' role:\n\n"
            f"{cv_text}\n\n"
            "Return suggestions and ATS keyword improvements in JSON."
        )

    def output_model(self):
        return CVOptimizationSuggestion

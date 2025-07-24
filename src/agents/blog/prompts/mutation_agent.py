from typing import List
from pydantic import BaseModel
from src.agents.base import BaseAgent, UserRole
from src.database.models import {BlogFeedbackOutput}

# ------------------------------------------------------------------
# Prompt Mutator Agent  (standard BaseAgent pattern)
# ------------------------------------------------------------------
class PromptMutatorAgent(BaseAgent):
    """
        Given a target agent name, prompt version, performance summary,
        and examples of the agent's output, this agent generates a new system prompt
        and prompt that will guide the target agent to produce higher-performing content.
        This agent is designed to be used in a blog content generation context,
        where it analyzes the performance of a specific agent and suggests improvements
    """
    name = "PromptMutatorAgent"

    # ---------- input / output ----------
    class Input(BaseModel):
        agent_name: str
        prompt_version: int
        performance_summary: BlogFeedbackOutput        # flattened DetailedFeedbackORM
        examples: List[dict]             # last N articles with full metrics

    class Output(BaseModel):
        system_prompt: str
        prompt: str
        reason: str

    # ---------- prompts ----------
    def system_prompt(self) -> str:
        return (
            "You are a senior prompt engineer.\n"
            "Your task is to analyse aggregated performance data and concrete examples, "
            "then produce an improved system prompt and prompt that will guide "
            "the target agent to generate higher-performing content.\n"
            "Return ONLY valid JSON matching the PromptMutatorAgent.Output schema."
        )

    def prompt(self, inp: Input) -> str:
        return inp.model_dump_json(indent=2)

    # ---------- output model ----------
    def output_model(self):
        return self.Output
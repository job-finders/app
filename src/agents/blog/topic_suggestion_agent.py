# agents/jobseeker/topic_suggestion.py
from src.agents.base import BaseAgent
from pydantic import BaseModel
from typing import List

class TopicSuggestions(BaseModel):
    topics: List[str]
    explanations: List[str]

class TopicSuggestionAgent(BaseAgent):
    name = "topic_suggestion"
    description = "Suggests relevant topics for discussion"

    def prompt(self, context: str) -> str:
        return f"Analyze this context and suggest relevant topics:\n{context}"

    def output_model(self):
        return TopicSuggestions


def generate_new_topics():
    pass

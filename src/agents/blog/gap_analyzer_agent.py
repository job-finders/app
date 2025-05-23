# agents/blog/gap_analyzer_agent.py
from src.agents.base import BaseAgent
from pydantic import BaseModel
from typing import List

class TopicPrompts(BaseModel):
    title: str
    prompts: List[str]

class GapAnalyzerAgent(BaseAgent):
    async def run(self, existing_posts):
        # Placeholder AI logic
        titles = [post["title"].lower() for post in existing_posts]
        new_topic = "Career Paths for Remote Work in South Africa"
        if new_topic.lower() not in titles:
            return TopicPrompts(
                title=new_topic,
                prompts=[
                    "Top Remote Jobs for South African Developers in 2025",
                    "How to Prepare for Remote Interviews: SA Edition"
                ]
            )
        return TopicPrompts(title="", prompts=[])

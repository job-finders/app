from typing import List
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent, UserRole
from .schemas import Topic, ArticleOutline, PerformanceMetrics, RefinementInstructions


# ------------------------------------------------------------------
# Topic Discovery Agent
# ------------------------------------------------------------------
class TopicDiscoveryAgent(BaseAgent):
    name = "TopicDiscoveryAgent"

    def system_prompt(self) -> str:
        return (
            "You are an expert content strategist.\n"
            "Return ONLY valid JSON that matches the Topic schema."
        )

    def prompt(self, site_map: dict) -> str:
        sections = ", ".join(site_map.keys())
        return (
            f"Site sections: {sections}\n"
            f"Site map JSON: {site_map}\n"
            "Generate a list of high-value blog topics for each section."
        )

    def output_model(self):
        return List[Topic]


# ------------------------------------------------------------------
# Article Planner Agent
# ------------------------------------------------------------------
class ArticlePlannerAgent(BaseAgent):
    name = "ArticlePlannerAgent"

    def system_prompt(self) -> str:
        return (
            "You are a senior blog editor.\n"
            "Return ONLY valid JSON that matches the ArticleOutline schema."
        )

    def prompt(self, topic: Topic) -> str:
        return (
            f"Topic: {topic.title}\n"
            f"Keywords: {', '.join(topic.keywords)}"
        )

    def output_model(self):
        return ArticleOutline


# ------------------------------------------------------------------
# Performance Monitor Agent
# ------------------------------------------------------------------
class PerformanceMonitorAgent(BaseAgent):
    name = "PerformanceMonitorAgent"

    def system_prompt(self) -> str:
        return (
            "You are a data analyst for blog performance.\n"
            "Return ONLY valid JSON that matches the PerformanceMetrics schema."
        )

    def prompt(self, slug: str) -> str:
        return f"Slug: {slug}"

    def output_model(self):
        return PerformanceMetrics


# ------------------------------------------------------------------
# Refiner Agent
# ------------------------------------------------------------------
class RefinerAgent(BaseAgent):
    name = "RefinerAgent"

    def system_prompt(self) -> str:
        return (
            "You are a blog optimisation strategist.\n"
            "Return ONLY valid JSON that matches the RefinementInstructions schema."
        )

    def prompt(self, metrics: PerformanceMetrics) -> str:
        return f"Performance metrics: {metrics.model_dump_json()}"

    def output_model(self):
        return RefinementInstructions
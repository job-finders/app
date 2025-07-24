from typing import List
from pydantic import BaseModel, Field
from ..base import BaseAgent   # mirrors employer-agent base
from .memory import memory     # shared wrapper
from .schemas import Topic, ArticleOutline, PerformanceMetrics     # will be defined next


class TopicDiscoveryAgent(BaseAgent):
    name = "TopicDiscoveryAgent"
    system_template = "prompts/system.jinja2"
    user_template   = "prompts/user.jinja2"

    def __init__(self):
        super().__init__()
        self.memory_prefix = "topics:raw"

    async def run(self, site_map: dict) -> List[Topic]:
        prompt_vars = {
            "agent_type": "TopicDiscovery",
            "job_description": "discover high-value blog topics from the site map",
            "schema_json": Topic.schema_json(indent=2),
            "memory_keys": [f"{self.memory_prefix}:{section}" for section in site_map.keys()],
            "input_json": site_map
        }
        raw = await self.call_llm(prompt_vars)
        topics = [Topic(**t) for t in raw]
        for t in topics:
            memory.set(f"{self.memory_prefix}:{t.section}", t.dict())
        return topics

#--------------------------------------------------------------------------------------
#--------------------------- Article Planner Agent -----------------------------------
#--------------------------------------------------------------------------------------

class ArticlePlannerAgent(BaseAgent):
    name = "ArticlePlannerAgent"
    system_template = "prompts/system.jinja2"
    user_template = "prompts/user.jinja2"

    def __init__(self):
        super().__init__()
        self.memory_prefix = "outline"

    async def run(self, topic: Topic) -> ArticleOutline:
        prompt_vars = {
            "agent_type": "ArticlePlanner",
            "job_description": "produce a detailed outline for a blog article",
            "schema_json": ArticleOutline.schema_json(indent=2),
            "memory_keys": [f"{self.memory_prefix}:{topic.id}"],
            "input_json": topic.dict()
        }
        raw = await self.call_llm(prompt_vars)
        outline = ArticleOutline(**raw)
        memory.set(f"{self.memory_prefix}:{outline.slug}", outline.dict())
        return outline


#----------------------------------------------------------------------------------------
#--------------------------- Performance Monitor Agent --------------------------------------


class PerformanceMonitorAgent(BaseAgent):
    name = "PerformanceMonitorAgent"
    system_template = "prompts/system.jinja2"
    user_template   = "prompts/user.jinja2"

    def __init__(self):
        super().__init__()
        self.memory_prefix = "perf"

    async def run(self, slug: str) -> PerformanceMetrics:
        # TODO: replace with real adapters (GA4, social APIs, etc.)
        prompt_vars = {
            "agent_type": "PerformanceMonitor",
            "job_description": "collect engagement and SEO metrics for a published article",
            "schema_json": PerformanceMetrics.schema_json(indent=2),
            "memory_keys": [f"{self.memory_prefix}:{slug}"],
            "input_json": {"slug": slug}
        }
        raw = await self.call_llm(prompt_vars)
        metrics = PerformanceMetrics(**raw)
        memory.set(f"{self.memory_prefix}:{slug}", metrics.dict())
        return metrics

#----------------------------------------------------------------------------------------
#--------------------------- Refiner Agent ----------------------------------------------
#-----------------------------------------------------------------------------------------


class RefinerAgent(BaseAgent):
    name = "RefinerAgent"
    system_template = "prompts/system.jinja2"
    user_template   = "prompts/user.jinja2"

    def __init__(self):
        super().__init__()
        self.memory_prefix = "refinement"

    async def run(self, metrics: PerformanceMetrics) -> RefinementInstructions:
        prompt_vars = {
            "agent_type": "Refiner",
            "job_description": "decide whether to refine, drop, or expand an article based on performance",
            "schema_json": RefinementInstructions.schema_json(indent=2),
            "memory_keys": [f"{self.memory_prefix}:{metrics.slug}"],
            "input_json": metrics.dict()
        }
        raw = await self.call_llm(prompt_vars)
        instructions = RefinementInstructions(**raw)
        memory.set(f"{self.memory_prefix}:{metrics.slug}", instructions.dict())
        return instructions
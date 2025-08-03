from __future__ import annotations
import inspect
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Type

from pydantic import BaseModel


from src.cache.cache_redis import cached
from src.agents.memory import AgentMemoryStore
from src.agents.openrouter_client import OpenRouterClient
from src.config import config_instance
from src.utils.route_helpers import get_service


class ModelType(str, Enum):
    GPT4 = "openai/gpt-4"
    CLAUDE = "anthropic/claude-3-haiku"
    DEEPSEEK_CHAT = "deepseek/deepseek-chat-v3-0324"
    DEEPSEEK_REASONER = "deepseek/deepseek-r1-0528"
    DEEPSEEK_CODER = "deepseek/deepseek-chat-v3-0324"
    DEEPSEEK_V3_FREE = "deepseek/deepseek-chat-v3-0324:free"
    MOONSHOT_KIMI_K2 = "moonshotai/kimi-k2"
    MOONSHOT_KIMI_K2_FREE = "moonshotai/kimi-k2:free"
    DEEPSEEK_CHIMERA_FREE = "tngtech/deepseek-r1t2-chimera:free"


class UserRole(str, Enum):
    JOB_SEEKER = "job_seeker"
    EMPLOYER = "employer"
    RECRUITER = "recruiter"
    HR_MANAGER = "hr_manager"
    ADMIN = "admin"
    SYSTEM_ADMIN = "system_admin"


class UsageTier(Enum):
    FREE = {"daily_limit": 10, "monthly_limit": 100}
    BASIC = {"daily_limit": 50, "monthly_limit": 1000}
    PREMIUM = {"daily_limit": 200, "monthly_limit": 5000}
    ENTERPRISE = {"daily_limit": 1000, "monthly_limit": 25000}


class UsageTracker:
    def __init__(self, user_id: str, tier: UsageTier = UsageTier.FREE):
        self.user_id = user_id
        self.tier = tier
        self._redis: dict[str, int] = {}  # replace with real Redis

    def _key(self, period: str) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        suffix = today if period == "daily" else month
        return f"{self.user_id}:{period}:{suffix}"

    def current(self, period: str) -> int:
        return self._redis.get(self._key(period), 0)

    def bump(self, period: str):
        key = self._key(period)
        self._redis[key] = self._redis.get(key, 0) + 1

    def within_limits(self) -> bool:
        limits = self.tier.value
        return (
            self.current("daily") < limits["daily_limit"]
            and self.current("monthly") < limits["monthly_limit"]
        )

    def record(self) -> bool:
        if not self.within_limits():
            return False
        self.bump("daily")
        self.bump("monthly")
        return True


class TaskType(str, Enum):
    """agents must select the task type they wish to execute from this task types"""
    # Job Seeker Utilities
    RESUME = "resume"
    COVER_LETTER = "cover letter"
    JOB_SEARCH = "job search"
    APPLICATION_TRACKING = "application tracking"

    # Employer / HR Screening
    SCREENING = "screening"
    CANDIDATE_FILTER = "candidate filter"
    INTERVIEW_QUESTIONS = "interview questions"

    # Matching
    MATCHING = "matching"
    JOB_MATCHING = "job matching"
    SKILLS_MATCH = "skills match"

    # Writing & Optimization
    WRITING = "writing"
    OPTIMIZE = "optimize"
    REWORD = "reword"
    SUMMARIZE = "summarize"

    # Salary & Budget
    SALARY = "salary"
    BUDGET = "budget"
    COMPENSATION = "compensation"

    # Conversation / General
    CHAT = "chat"
    CONVERSATION = "conversation"
    FOLLOW_UP = "follow up"
    REPLY = "reply"

    # Reasoning
    PLAN = "plan"
    STRATEGY = "strategy"
    EVALUATION = "evaluation"
    ASSESSMENT = "assessment"

    # Technical
    CODE = "code"
    EXTRACT = "extract"
    PARSE = "parse"
    GENERATE_CODE = "generate code"


class BaseAgent(ABC):
    ROUTING_RULES: dict[str, ModelType] = {
        # --- Job Seeker Utilities ---
        "resume": ModelType.DEEPSEEK_CHAT,
        "cover letter": ModelType.DEEPSEEK_CHAT,
        "job search": ModelType.MOONSHOT_KIMI_K2,
        "application tracking": ModelType.MOONSHOT_KIMI_K2,

        # --- Employer / HR Screening ---
        "screening": ModelType.MOONSHOT_KIMI_K2,
        "candidate filter": ModelType.MOONSHOT_KIMI_K2,
        "interview questions": ModelType.MOONSHOT_KIMI_K2,

        # --- Analysis & Matching ---
        "matching": ModelType.MOONSHOT_KIMI_K2,
        "job matching": ModelType.MOONSHOT_KIMI_K2,
        "skills match": ModelType.MOONSHOT_KIMI_K2,

        # --- Writing & Optimization ---
        "writing": ModelType.DEEPSEEK_CHAT,
        "optimize": ModelType.DEEPSEEK_CHAT,
        "reword": ModelType.DEEPSEEK_CHAT,
        "summarize": ModelType.DEEPSEEK_CHAT,

        # --- Salary & Budget ---
        "salary": ModelType.MOONSHOT_KIMI_K2,
        "budget": ModelType.MOONSHOT_KIMI_K2,
        "compensation": ModelType.MOONSHOT_KIMI_K2,

        # --- Conversation / General ---
        "chat": ModelType.DEEPSEEK_CHAT,
        "conversation": ModelType.DEEPSEEK_CHAT,
        "follow up": ModelType.DEEPSEEK_CHAT,
        "reply": ModelType.DEEPSEEK_CHAT,

        # --- Advanced Reasoning & Logic ---
        "plan": ModelType.DEEPSEEK_REASONER,
        "strategy": ModelType.DEEPSEEK_REASONER,
        "evaluation": ModelType.DEEPSEEK_REASONER,
        "assessment": ModelType.DEEPSEEK_REASONER,

        # --- Technical / Code / Parsing ---
        "code": ModelType.DEEPSEEK_CODER,
        "extract": ModelType.DEEPSEEK_CODER,
        "parse": ModelType.DEEPSEEK_CODER,
        "generate code": ModelType.DEEPSEEK_CODER,
    }

    def __init__(self, user_id: str, usage_tier: UsageTier = UsageTier.FREE):
        self.user_id = user_id
        self.name = getattr(self, "name", self.__class__.__name__)
        self.memory = AgentMemoryStore(user_id, self.name)
        self.usage = UsageTracker(user_id, usage_tier)
        self.hashnode_token = config_instance().HASHNODE_TOKEN
        self.client = OpenRouterClient()
        self._logger = get_service("logger")()(self.name)
        self._last_interaction = {}
        self.client.init_app()

    @abstractmethod
    def system_prompt(self) -> str: ...

    @abstractmethod
    def prompt(self, *args, **kwargs) -> str: ...

    @abstractmethod
    def output_model(self) -> Type[BaseModel]: ...


    @classmethod
    def select_model(cls, user_prompt: str, user_role: UserRole | None = None,
                     task_type: str | None = None) -> ModelType:
        text = user_prompt.lower()

        if user_role == UserRole.EMPLOYER and "screening" in text:
            return ModelType.MOONSHOT_KIMI_K2
        if user_role == UserRole.JOB_SEEKER and "search" in text:
            return ModelType.MOONSHOT_KIMI_K2

        if task_type and task_type in cls.ROUTING_RULES:
            return cls.ROUTING_RULES[task_type]

        for phrase, model in cls.ROUTING_RULES.items():
            if phrase in text:
                return model

        return ModelType.DEEPSEEK_CHAT  # safe default

    async def check_usage_and_select_model(
            self,
            user_prompt: str,
            user_role: UserRole | None = None,
            task_type: str | None = None,
    ) -> ModelType:
        """
        Checks user limits, analyzes the prompt/task/role and returns the ideal model.
        Falls back to free-tier if limits are exceeded.
        """
        # Analyze prompt and role/task to route model
        model = self.select_model(user_prompt, user_role, task_type)

        # If the user has exceeded their limits, fall back to a free-tier model
        if not self.usage.within_limits():
            if self.usage.tier == UsageTier.FREE:
                raise RuntimeError("Daily/monthly limit exceeded. Please upgrade.")
            fallback_model = self.fallback_for(model)
            self._logger.warning(f"Limits exceeded, falling back to: {fallback_model.value}")
            return fallback_model

        self._logger.info(f"Selected model: {model.value}")
        return model

    @staticmethod
    def fallback_for(model: ModelType) -> ModelType:
        return (
            ModelType.MOONSHOT_KIMI_K2_FREE
            if model == ModelType.MOONSHOT_KIMI_K2
            else ModelType.DEEPSEEK_CHIMERA_FREE
        )

    @cached(ttl=3600)
    async def run(self, user_role: UserRole | None = None, task_type: str | None = None, *args, **kwargs) -> BaseModel:
        prompt = self.prompt(*args, **kwargs)
        if inspect.iscoroutine(prompt):
            prompt = await prompt

        # Check structured memory first
        if mem_cached := self.memory.get_cached_result(prompt):
            self._logger.info("Returning cached result from memory store.")
            return self.output_model().model_validate(mem_cached)

        model = await self.check_usage_and_select_model(prompt, user_role, task_type)

        if not self.usage.record():
            raise RuntimeError("Usage limit exceeded")

        self.memory.add_entry("user", prompt, protect=kwargs.get("protect_user_message", False))
        messages = [
            {"role": "system", "content": self.system_prompt()},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.client.structured_completion(
                messages=messages,
                output_model=self.output_model(),
                model=model.value,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2048),
            )

            if response is None:
                raise ValueError("Agent produced no output.")

            self.memory.add_entry("assistant", response.model_dump_json(),
                                  protect=kwargs.get("protect_response", False))
            self.memory.add_result(prompt, response.model_dump())
            return response

        except Exception as e:
            self._logger.error(f"Error during structured completion: {e}")
            return await self._run_fallback(messages, prompt, kwargs)

    async def _run_fallback(
            self,
            messages: list[dict[str, str]],
            user_id: str,
            kwargs: dict[str, Any],
    ) -> BaseModel:
        """
        Called when a primary model fails due to quota or billing issue.
        Uses fallback model based on the original selection.
        """
        original_prompt = messages[-1]["content"]
        original_model = self.select_model(original_prompt)
        fallback_model = self.fallback_for(original_model)

        self._logger.warning(f"Running fallback agent with model: {fallback_model.value}")

        response = await self.client.structured_completion(
            messages=messages,
            output_model=self.output_model(),
            model=fallback_model.value,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 1024),
        )

        if response is None:
            raise ValueError("Fallback agent produced no output.")

        self.memory.add_entry(
            "assistant",
            f"[FALLBACK:{fallback_model.value}] {response.model_dump_json()}",
            protect=kwargs.get("protect_response", False),
        )
        return response


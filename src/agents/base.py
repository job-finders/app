from __future__ import annotations
import inspect
import time
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Type

from pydantic import BaseModel

from src.agents.memory import AgentMemoryStore
from src.agents.openrouter_client import OpenRouterClient
from src.config import config_instance
from src.utils.route_helpers import get_service


# ---------- Configuration Enums ------------------------------------------------
class ModelType(str, Enum):
    # deepseek
    DEEPSEEK_CHAT = "deepseek/deepseek-chat"
    DEEPSEEK_REASONER = "deepseek/deepseek-reasoner"
    DEEPSEEK_V3 = "deepseek/deepseek-v3"
    DEEPSEEK_CODER = "deepseek/deepseek-coder"
    DEEPSEEK_CHIMERA_FREE = "tngtech/deepseek-r1t2-chimera:free"
    DEEPSEEK_R1_GWEN_FREE = "deepseek/deepseek-r1-0528-qwen3-8b:free"
    DEEPSEEK_R1_528_FREE = "deepseek/deepseek-r1-0528:free"

    # moonshot
    MOONSHOT_KIMI_K2 = "moonshotai/kimi-k2"
    MOONSHOT_KIMI_K2_FREE = "moonshotai/kimi-k2:free"

    # qwen
    GWEN_30B = "qwen/qwen3-30b-a3b:free"

    # fallbacks
    GPT4 = "openai/gpt-4"
    CLAUDE = "anthropic/claude-3-haiku"


class UserRole(str, Enum):
    JOB_SEEKER = "job_seeker"
    EMPLOYER = "employer"
    HR_MANAGER = "hr_manager"
    RECRUITER = "recruiter"
    ADMIN = "admin"


class UsageTier(Enum):
    FREE = {"daily_limit": 10, "monthly_limit": 100}
    BASIC = {"daily_limit": 50, "monthly_limit": 1000}
    PREMIUM = {"daily_limit": 200, "monthly_limit": 5000}
    ENTERPRISE = {"daily_limit": 1000, "monthly_limit": 25000}


# ---------- Usage Tracking -----------------------------------------------------
class UsageTracker:
    def __init__(self, user_id: str, tier: UsageTier = UsageTier.FREE) -> None:
        self.user_id = user_id
        self.tier = tier
        self._redis: dict[str, int] = {}  # Replace with real Redis or DB

    # ---------------------------------------------------------------------
    def _key(self, period: str) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        suffix = today if period == "daily" else month
        return f"{self.user_id}:{period}:{suffix}"

    def current(self, period: str) -> int:
        return self._redis.get(self._key(period), 0)

    def bump(self, period: str) -> None:
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


# ---------- Agent --------------------------------------------------------------
class BaseAgent(ABC):
    def __init__(
        self,
        user_id: str,
        usage_tier: UsageTier = UsageTier.FREE,
    ) -> None:
        self.user_id = user_id
        self.name = getattr(self, "name", self.__class__.__name__)
        self.memory = AgentMemoryStore(user_id, self.name)
        self.usage = UsageTracker(user_id, usage_tier)
        self.hashnode_token = config_instance().HASHNODE_TOKEN
        self.client = OpenRouterClient()
        self._logger = get_service("logger")()(self.name)
        self._last_interaction: dict[str, Any] = {}
        self.client.init_app()

    # ------------------------------------------------------------------
    @abstractmethod
    def system_prompt(self) -> str: ...
    @abstractmethod
    def prompt(self, *args, **kwargs) -> str: ...
    @abstractmethod
    def output_model(self) -> Type[BaseModel]: ...

    # ------------------------------------------------------------------
    # Model Routing
    # ------------------------------------------------------------------
    ROUTING_RULES = {
        "matching": ModelType.MOONSHOT_KIMI_K2,
        "analysis": ModelType.MOONSHOT_KIMI_K2,
        "budget": ModelType.MOONSHOT_KIMI_K2,
        "salary": ModelType.MOONSHOT_KIMI_K2,
        "writing": ModelType.DEEPSEEK_CHAT,
        "conversation": ModelType.DEEPSEEK_CHAT,
        "resume": ModelType.DEEPSEEK_CHAT,
        "cover letter": ModelType.DEEPSEEK_CHAT,
        "interview": ModelType.DEEPSEEK_CHAT,
    }

    @classmethod
    def select_model(
        cls,
        user_prompt: str,
        user_role: UserRole | None = None,
        task_type: str | None = None,
    ) -> ModelType:
        """Return the best model for the given prompt / role / task."""
        text = user_prompt.lower()

        # Role-specific shortcuts
        if user_role == UserRole.EMPLOYER and "screening" in text:
            return ModelType.MOONSHOT_KIMI_K2
        if user_role == UserRole.JOB_SEEKER and "job search" in text:
            return ModelType.MOONSHOT_KIMI_K2

        # Task-type override
        if task_type and task_type in cls.ROUTING_RULES:
            return cls.ROUTING_RULES[task_type]

        # Keyword-based fallthrough
        for phrase, model in cls.ROUTING_RULES.items():
            if phrase in text:
                return model

        return ModelType.DEEPSEEK_CHAT  # default

    @staticmethod
    def fallback_for(model: ModelType) -> ModelType:
        return (
            ModelType.MOONSHOT_KIMI_K2_FREE
            if model == ModelType.MOONSHOT_KIMI_K2
            else ModelType.DEEPSEEK_CHIMERA_FREE
        )

    # ------------------------------------------------------------------
    async def check_usage_and_select_model(
        self,
        user_prompt: str,
        user_role: UserRole | None = None,
        task_type: str | None = None,
    ) -> ModelType:
        model = self.select_model(user_prompt, user_role, task_type)

        if not self.usage.within_limits():
            if self.usage.tier == UsageTier.FREE:
                raise RuntimeError("Daily / monthly limit exceeded. Please upgrade.")
            model = self.fallback_for(model)

        self._logger.info(f"Using model {model.value}")
        return model

    # ------------------------------------------------------------------
    async def run(
        self,
        user_role: UserRole | None = None,
        task_type: str | None = None,
        *args,
        **kwargs,
    ) -> BaseModel:
        prompt = self.prompt(*args, **kwargs)
        if inspect.iscoroutine(prompt):
            prompt = await prompt

        model = await self.check_usage_and_select_model(prompt, user_role, task_type)
        if not self.usage.record():
            raise RuntimeError("Usage limit exceeded during execution")

        user_id = self.memory.add_entry(
            "user",
            prompt,
            protect=kwargs.get("protect_user_message", False),
        )

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

            self.memory.add_entry(
                "assistant",
                response.model_dump_json(),
                protect=kwargs.get("protect_response", False),
            )
            self._last_interaction = {"user_entry_id": user_id, "timestamp": time.time()}
            return response

        except Exception as e:
            if any(w in str(e).lower() for w in ("limit_exceed", "add credit", "payment")):
                return await self._run_fallback(messages, user_id, kwargs)
            self._logger.error({"error": str(e), "model": model.value})
            raise

    async def _run_fallback(
        self,
        messages: list[dict[str, str]],
        user_id: str,
        kwargs: dict[str, Any],
    ) -> BaseModel:
        model = self.fallback_for(self.select_model(messages[-1]["content"]))
        response = await self.client.structured_completion(
            messages=messages,
            output_model=self.output_model(),
            model=model.value,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 1024),
        )
        if response is None:
            raise ValueError("Fallback agent produced no output.")

        self.memory.add_entry(
            "assistant",
            f"[FALLBACK:{model.value}] {response.model_dump_json()}",
            protect=kwargs.get("protect_response", False),
        )
        return response

    # ------------------------------------------------------------------
    def usage_info(self) -> dict[str, int | str]:
        limits = self.usage.tier.value
        daily = self.usage.current("daily")
        monthly = self.usage.current("monthly")
        info = {
            "tier": self.usage.tier.name,
            "daily": f"{daily}/{limits['daily_limit']}",
            "monthly": f"{monthly}/{limits['monthly_limit']}",
        }
        self._logger.info(f"Usage {info}")
        return info
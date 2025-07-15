from abc import ABC, abstractmethod
from datetime import datetime
import time
from enum import Enum
from typing import Type, Dict, Any
from pydantic import BaseModel

from src.agents.openrouter_client import OpenRouterClient
from src.config import config_instance

from src.agents.memory import AgentMemoryStore


class ModelType(Enum):
    # Primary DeepSeek models (cost-effective)
    DEEPSEEK_CHAT = "deepseek/deepseek-chat"
    DEEPSEEK_REASONER = "deepseek/deepseek-reasoner"
    DEEPSEEK_V3 = "deepseek/deepseek-v3"
    DEEPSEEK_CODER = "deepseek/deepseek-coder"
    DEEPSEEK_CHIMERA_FREE = "tngtech/deepseek-r1t2-chimera:free"
    DEEPSEEK_R1_GWEN_FREE = "deepseek/deepseek-r1-0528-qwen3-8b:free"
    DEEPSEEK_R1_528_FREE = "deepseek/deepseek-r1-0528:free"
    
    # Fallback models (for when DeepSeek can't handle the task)
    GPT4 = "openai/gpt-4"
    CLAUDE = "anthropic/claude-3-haiku"  # Cheaper Claude variant

class UserRole(Enum):
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

class UsageTracker:
    def __init__(self, user_id: str, tier: UsageTier = UsageTier.FREE):
        self.user_id = user_id
        self.tier = tier
        self.usage_data = {}  # Store in Redis/DB in production
    
    def get_usage_key(self, period: str) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        return f"{self.user_id}:{period}:{today if period == 'daily' else month}"
    
    def get_current_usage(self, period: str) -> int:
        key = self.get_usage_key(period)
        return self.usage_data.get(key, 0)
    
    def increment_usage(self, period: str) -> None:
        key = self.get_usage_key(period)
        self.usage_data[key] = self.usage_data.get(key, 0) + 1
    
    def check_limit(self) -> bool:
        daily_usage = self.get_current_usage("daily")
        monthly_usage = self.get_current_usage("monthly")
        
        limits = self.tier.value
        return (daily_usage < limits["daily_limit"] and 
                monthly_usage < limits["monthly_limit"])

    def record_usage(self) -> bool:
        if self.check_limit():
            self.increment_usage("daily")
            self.increment_usage("monthly")
            return True
        return False

class BaseAgent(ABC):
    def __init__(self, user_id: str, usage_tier: UsageTier = UsageTier.FREE):
        self.user_id = user_id
        self.name = getattr(self, "name", self.__class__.__name__)
        self.memory = AgentMemoryStore(user_id, agent_name=self.name)
        self.usage_tracker = UsageTracker(user_id, usage_tier)
        self.hashnode_token = config_instance().HASHNODE_TOKEN
        self.openrouter_client = OpenRouterClient()
        self.logger = None
        self._last_interaction = {}


    @abstractmethod
    def system_prompt(self):
        ...

    @abstractmethod
    def prompt(self, *args, **kwargs) -> str:
        ...

    @abstractmethod
    def output_model(self) -> Type[BaseModel]:
        ...

    @staticmethod
    def select_model(user_prompt: str, user_role: UserRole = None, task_type: str = None, *args, **kwargs) -> ModelType:
        prompt_lower = user_prompt.lower()

        # Role-specific routing - primarily DeepSeek
        if user_role == UserRole.EMPLOYER:
            if any(word in prompt_lower for word in ["screening", "candidate evaluation", "shortlist"]):
                return ModelType.DEEPSEEK_REASONER
            elif any(word in prompt_lower for word in ["job posting", "job description", "requirements"]):
                return ModelType.DEEPSEEK_CHAT  # DeepSeek handles writing well
            elif any(word in prompt_lower for word in ["budget", "salary range", "compensation"]):
                return ModelType.DEEPSEEK_V3
            elif any(word in prompt_lower for word in ["company culture", "team fit", "onboarding"]):
                return ModelType.DEEPSEEK_CHAT
        
        elif user_role == UserRole.JOB_SEEKER:
            if any(word in prompt_lower for word in ["resume", "cv", "cover letter", "application"]):
                return ModelType.DEEPSEEK_CHAT  # Good at structured writing
            elif any(word in prompt_lower for word in ["job search", "job matching", "recommendations"]):
                return ModelType.DEEPSEEK_REASONER
            elif any(word in prompt_lower for word in ["interview prep", "mock interview", "questions"]):
                return ModelType.DEEPSEEK_CHAT  # Conversational
            elif any(word in prompt_lower for word in ["salary negotiation", "market rate", "compensation"]):
                return ModelType.DEEPSEEK_V3
            elif any(word in prompt_lower for word in ["career path", "skills development", "growth"]):
                return ModelType.DEEPSEEK_CHAT
        
        elif user_role == UserRole.HR_MANAGER:
            if any(word in prompt_lower for word in ["policy", "compliance", "legal", "documentation"]):
                return ModelType.DEEPSEEK_CHAT  # Good at formal writing
            elif any(word in prompt_lower for word in ["talent pipeline", "recruitment strategy", "hiring plan"]):
                return ModelType.DEEPSEEK_REASONER
            elif any(word in prompt_lower for word in ["employee engagement", "retention", "culture"]):
                return ModelType.DEEPSEEK_CHAT
            elif any(word in prompt_lower for word in ["performance review", "evaluation", "feedback"]):
                return ModelType.DEEPSEEK_V3
        
        elif user_role == UserRole.RECRUITER:
            if any(word in prompt_lower for word in ["sourcing", "candidate search", "talent acquisition"]):
                return ModelType.DEEPSEEK_REASONER
            elif any(word in prompt_lower for word in ["outreach", "messaging", "communication"]):
                return ModelType.DEEPSEEK_CHAT
            elif any(word in prompt_lower for word in ["pipeline management", "tracking", "metrics"]):
                return ModelType.DEEPSEEK_V3
        
        # Task-specific routing
        if task_type:
            if task_type == "matching":
                return ModelType.DEEPSEEK_REASONER
            elif task_type == "writing":
                return ModelType.DEEPSEEK_CHAT
            elif task_type == "analysis":
                return ModelType.DEEPSEEK_V3
            elif task_type == "conversation":
                return ModelType.DEEPSEEK_CHAT
            elif task_type == "coding":
                return ModelType.DEEPSEEK_CODER
        
        # General job-related content routing - DeepSeek first
        if any(word in prompt_lower for word in ["job matching", "recommend jobs", "find jobs", "job search", "match candidates"]):
            return ModelType.DEEPSEEK_REASONER
        
        elif any(word in prompt_lower for word in ["resume", "cv", "cover letter", "portfolio", "application"]):
            return ModelType.DEEPSEEK_CHAT
        
        elif any(word in prompt_lower for word in ["job description", "job posting", "requirements", "hiring"]):
            return ModelType.DEEPSEEK_CHAT
        
        elif any(word in prompt_lower for word in ["interview", "preparation", "questions", "practice", "mock"]):
            return ModelType.DEEPSEEK_CHAT
        
        elif any(word in prompt_lower for word in ["salary", "compensation", "pay", "benefits", "market rate"]):
            return ModelType.DEEPSEEK_V3
        
        elif any(word in prompt_lower for word in ["career advice", "guidance", "transition", "growth", "development"]):
            return ModelType.DEEPSEEK_CHAT
        
        elif any(word in prompt_lower for word in ["company research", "industry analysis", "trends", "insights"]):
            return ModelType.DEEPSEEK_V3
        
        elif any(word in prompt_lower for word in ["skills assessment", "evaluation", "competency", "proficiency"]):
            return ModelType.DEEPSEEK_REASONER
        
        elif any(word in prompt_lower for word in ["networking", "connections", "professional", "contacts"]):
            return ModelType.DEEPSEEK_CHAT
        
        elif any(word in prompt_lower for word in ["market analysis", "demand", "supply", "statistics"]):
            return ModelType.DEEPSEEK_V3
        
        elif any(word in prompt_lower for word in ["onboarding", "orientation", "training", "integration"]):
            return ModelType.DEEPSEEK_CHAT
        
        elif any(word in prompt_lower for word in ["performance", "productivity", "metrics", "kpi"]):
            return ModelType.DEEPSEEK_V3
        
        elif any(word in prompt_lower for word in ["diversity", "inclusion", "equity", "bias"]):
            return ModelType.DEEPSEEK_CHAT
        
        elif any(word in prompt_lower for word in ["remote work", "hybrid", "flexible", "work-life"]):
            return ModelType.DEEPSEEK_CHAT
        
        elif any(word in prompt_lower for word in ["contract", "freelance", "gig", "temporary"]):
            return ModelType.DEEPSEEK_REASONER
        
        elif any(word in prompt_lower for word in ["code", "programming", "technical", "development"]):
            return ModelType.DEEPSEEK_CHAT
        
        # Default to most cost-effective model
        return ModelType.DEEPSEEK_CHAT

    @staticmethod
    def get_fallback_model(selected_model: ModelType) -> ModelType:
        """Get cheaper fallback model when usage limits are exceeded"""
        if selected_model in [ModelType.DEEPSEEK_REASONER, ModelType.DEEPSEEK_V3]:
            return ModelType.DEEPSEEK_R1_528_FREE
        return ModelType.DEEPSEEK_CHIMERA_FREE

    async def check_usage_and_select_model(self, user_prompt: str, user_role: UserRole = None, task_type: str = None, *args, **kwargs) -> ModelType:
        """Check usage limits and select appropriate model"""
        selected_model = self.select_model(user_prompt, user_role, task_type, *args, **kwargs)
        
        # Check if user has exceeded limits
        if not self.usage_tracker.check_limit():
            # Use cheapest model or deny service
            if self.usage_tracker.tier == UsageTier.FREE:
                raise Exception("Daily/Monthly limit exceeded. Please upgrade your plan.")
            else:
                return self.get_fallback_model(selected_model)
        
        return selected_model

    def get_usage_info(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        daily_usage = self.usage_tracker.get_current_usage("daily")
        monthly_usage = self.usage_tracker.get_current_usage("monthly")
        limits = self.usage_tracker.tier.value
        
        return {
            "tier": self.usage_tracker.tier.name,
            "daily_usage": daily_usage,
            "daily_limit": limits["daily_limit"],
            "monthly_usage": monthly_usage,
            "monthly_limit": limits["monthly_limit"],
            "daily_remaining": limits["daily_limit"] - daily_usage,
            "monthly_remaining": limits["monthly_limit"] - monthly_usage
        }

    async def run(self, user_role: UserRole = None, task_type: str = None, *args, **kwargs) -> BaseModel:

        user_prompt = self.prompt(*args, **kwargs)
        system_prompt = self.system_prompt()

        # Select model with usage limits
        selected_model = await self.check_usage_and_select_model(
            user_prompt, user_role, task_type, *args, **kwargs
        )
        # Record usage
        if not self.usage_tracker.record_usage():
            raise Exception("Usage limit exceeded during execution")

        # Add user message to memory with protection option
        protect_user_msg = kwargs.get('protect_user_message', False)
        user_entry_id = self.memory.add_entry("user", user_prompt, protect=protect_user_msg)

        # Get memory in chat format with optional limit
        # memory_limit = kwargs.get('memory_limit', None)
        # chat_messages = self.memory.get_chat_messages(limit=memory_limit)

        # Build final message structure
        messages = [{"role": "system", "content": system_prompt}]

        try:
            self.openrouter_client.init_app()
            # Make API call with enhanced client
            output = await self.openrouter_client.structured_completion(
                messages=messages,
                output_model=self.output_model(),
                model=selected_model.value,
                temperature=kwargs.get('temperature', 0.7),
                max_tokens=kwargs.get('max_tokens', 1024)
            )
            # Add assistant response to memory
            protect_response = kwargs.get('protect_response', False)
            assistant_entry_id = self.memory.add_entry(
                "assistant", 
                output.model_dump_json(), 
                protect=protect_response
            )
            # Store entry IDs for potential future reference
            self._last_interaction = {
                "user_entry_id": user_entry_id,
                "assistant_entry_id": assistant_entry_id,
                "timestamp": time.time()
            }
            
            return output
            
        except Exception as e:
            # Enhanced error handling with memory context
            error_context = {
                "error": str(e),
                "model": selected_model.value if 'selected_model' in locals() else "unknown",
                "memory_stats": "",
                "user_prompt_preview": user_prompt[:100] + "..." if len(user_prompt) > 100 else user_prompt
            }
            
            # Handle rate limiting and model errors
            if "limit exceeded" in str(e).lower():
                try:
                    return await self.run_fallback_model(kwargs=kwargs, user_entry_id=user_entry_id,
                                                         selected_model=selected_model,
                                                         messages=messages)
                except Exception as e:
                    # Log both original and fallback errors
                    fallback_error = str(e)
                    error_context["fallback_error"] = str(fallback_error)
                    self._log_error(error_context)
                    raise fallback_error

            else:
                self._log_error(error_context)
                raise e

    async def run_fallback_model(self, kwargs, user_entry_id: str, selected_model: ModelType,
                                 messages: list[dict[str, str]]):

        # Will use a Fallback Model for the previous selected Model.
        fallback_model = self.get_fallback_model(selected_model=selected_model)

        output = await self.openrouter_client.structured_completion(
            messages=messages,
            output_model=self.output_model(),
            model=fallback_model.value,
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 1024)
        )
        error_context = dict(message=f"Fallback model Output: {output}",
                             method="run_fallback_model")
        self._log_error(error_context=error_context)

        # Add fallback response to memory with note
        fallback_response = output.model_dump_json()
        assistant_entry_id = self.memory.add_entry(
            "assistant",
            f"[FALLBACK_MODEL:{fallback_model.value}] {fallback_response}",
            protect=kwargs.get('protect_response', False)
        )

        self._last_interaction = {
            "user_entry_id": user_entry_id,
            "assistant_entry_id": assistant_entry_id,
            "fallback_used": True,
            "timestamp": time.time()
        }

        return output

    def delete_memory_entry(self, entry_id: str) -> bool:
        """Delete a specific memory entry."""
        return self.memory.delete_entry(entry_id)

    def delete_memory_entries(self, entry_ids: list[str]) -> dict[str, bool]:
        """Delete multiple memory entries."""
        return self.memory.delete_entries(entry_ids)

    def get_last_interaction(self) -> Dict:
        """Get details of the last interaction."""
        return getattr(self, '_last_interaction', {})

    def _log_error(self, error_context: dict[str, str]):
        """Log error with enhanced context."""
        # Implement your logging logic here
        from src.utils.route_helpers import get_service
        if not self.logger:
            __logger_name: str = f"Debug Logger: {self.__class__.__name__.lower()} : "
            self.logger = get_service('logger')()(__logger_name)
        self.logger.info(error_context)

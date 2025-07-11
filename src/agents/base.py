from typing import Type, Optional, Dict, Any
from abc import ABC, abstractmethod
from pydantic import BaseModel
from enum import Enum
import asyncio
from datetime import datetime, timedelta

class ModelType(Enum):
    # Primary DeepSeek models (cost-effective)
    DEEPSEEK_CHAT = "deepseek/deepseek-chat"
    DEEPSEEK_REASONER = "deepseek/deepseek-reasoner"
    DEEPSEEK_V3 = "deepseek/deepseek-v3"
    DEEPSEEK_CODER = "deepseek/deepseek-coder"
    
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
    
    def record_usage(self) -> None:
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

    @abstractmethod
    def prompt(self, *args, **kwargs) -> str:
        ...

    @abstractmethod
    def output_model(self) -> Type[BaseModel]:
        ...

    def select_model(self, user_prompt: str, user_role: UserRole = None, task_type: str = None, *args, **kwargs) -> ModelType:
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
            return ModelType.DEEPSEEK_CODER
        
        # Default to most cost-effective model
        return ModelType.DEEPSEEK_CHAT

    def get_fallback_model(self, selected_model: ModelType) -> ModelType:
        """Get cheaper fallback model when usage limits are exceeded"""
        if selected_model in [ModelType.DEEPSEEK_REASONER, ModelType.DEEPSEEK_V3]:
            return ModelType.DEEPSEEK_CHAT
        return ModelType.DEEPSEEK_CHAT

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

    async def run(self, user_role: UserRole = None, task_type: str = None, *args, **kwargs) -> BaseModel:
        try:
            user_prompt = self.prompt(*args, **kwargs)
            system_prompt = self.system_prompt()
            
            # Select model with usage limits
            selected_model = await self.check_usage_and_select_model(
                user_prompt, user_role, task_type, *args, **kwargs
            )
            
            # Record usage
            if not self.usage_tracker.record_usage():
                raise Exception("Usage limit exceeded during execution")
            
            self.memory.add_entry("user", user_prompt)
            memory_history = self.memory.get_history()
            messages = [{"role": "system", "content": system_prompt}] + memory_history

            output = await call_openrouter(
                messages=messages,
                output_model=self.output_model(),
                model=selected_model.value
            )

            self.memory.add_entry("assistant", output.json())
            return output
            
        except Exception as e:
            # Handle rate limiting, model errors, etc.
            if "limit exceeded" in str(e).lower():
                # Try with fallback model
                fallback_model = self.get_fallback_model(ModelType.DEEPSEEK_CHAT)
                output = await call_openrouter(
                    messages=messages,
                    output_model=self.output_model(),
                    model=fallback_model.value
                )
                self.memory.add_entry("assistant", output.json())
                return output
            else:
                raise e

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

# src/agents/base.py
from typing import Type
from abc import ABC, abstractmethod
from pydantic import BaseModel

from src.agents.memory import AgentMemoryStore
from src.agents.openrouter_client import call_openrouter
from src.config import config_instance


class BaseAgent(ABC):
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.name = getattr(self, "name", self.__class__.__name__)
        self.memory = AgentMemoryStore(user_id, agent_name=self.name)
        self.hashnode_token = config_instance().HASHNODE_TOKEN

    @abstractmethod
    def prompt(self, *args, **kwargs) -> str:
        ...

    @abstractmethod
    def output_model(self) -> Type[BaseModel]:
        ...

    def system_prompt(self) -> str:
        """Override in agents to define custom system behavior."""
        return "You are a helpful assistant. for jobfinders.site your task is to assist employers and job seekers"

    async def run(self, *args, **kwargs) -> BaseModel:
        user_prompt = self.prompt(*args, **kwargs)
        system_prompt = self.system_prompt()

        # Add user input to memory
        self.memory.add_entry("user", user_prompt)

        # Retrieve full memory
        memory_history = self.memory.get_history()

        # Prepend system prompt
        messages = [{"role": "system", "content": system_prompt}] + memory_history

        # Call OpenRouter with full message list
        output = await call_openrouter(
            messages=messages,
            output_model=self.output_model()
        )

        # Add assistant's response back to memory
        self.memory.add_entry("assistant", output.json())

        return output

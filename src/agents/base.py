# agents/base.py
from abc import ABC, abstractmethod
from typing import Any, Type
from pydantic import BaseModel
from src.agents.openrouter_client import call_openrouter
from src.agents.memory.local_memory import AgentMemoryStore

class BaseAgent(ABC):
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memory = AgentMemoryStore(user_id)


    @abstractmethod
    def prompt(self, *args, **kwargs) -> str:
        ...

    @abstractmethod
    def output_model(self) -> Type[BaseModel]:
        ...

    async def run(self, *args, **kwargs) -> BaseModel:
        prompt = self.prompt(*args, **kwargs)
        output = await call_openrouter(prompt, self.output_model())
        return output

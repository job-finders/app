# agents/base.py
from abc import ABC, abstractmethod
from typing import Any, Type

from src.config import config_instance
from pydantic import BaseModel
from src.agents.openrouter_client import call_openrouter


class BaseAgent(ABC):
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memory = AgentMemoryStore(user_id)
        self.hashnode_token = config_instance().HASHNODE_TOKEN


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

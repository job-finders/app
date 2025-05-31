# src/agents/base.py

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

    def system_prompt(self) -> str:
        """Override in agents to define custom system behavior."""
        return "You are a helpful assistant."

    async def run(self, *args, **kwargs) -> BaseModel:
        prompt = self.prompt(*args, **kwargs)
        system_prompt = self.system_prompt()
        output = await call_openrouter(prompt, self.output_model(), system_prompt)
        return output

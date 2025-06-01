import json
from typing import List, Dict
from src.config import config_instance
import redis


cfg = config_instance()


class AgentMemoryStore:
    def __init__(self, user_id: str, agent_name: str):
        self.user_id = user_id
        self.agent_name = agent_name
        self.key = f"agent_memory:{user_id}:{agent_name}"
        self.redis_store = redis.Redis(
            host=cfg.REDIS_HOST,
            port=cfg.REDIS_PORT,
            db=cfg.REDIS_DB,
            decode_responses=True
        )

    def add_entry(self, role: str, content: str):
        """Add an entry to the user's memory (stored as a JSON-encoded string)."""
        entry = json.dumps({"role": role, "content": content})
        self.redis_store.rpush(self.key, entry)

    def get_history(self) -> List[Dict[str, str]]:
        """Retrieve the full memory history."""
        raw_entries = self.redis_store.lrange(self.key, 0, -1)
        return [json.loads(entry) for entry in raw_entries]

    def clear(self):
        """Clear memory for this user-agent combo."""
        self.redis_store.delete(self.key)

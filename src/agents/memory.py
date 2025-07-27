import hashlib
import json
import pickle
import time
from typing import Any, List, Dict, Optional

from src.cache.cache_redis import agent_cache
from src.utils.route_helpers import get_service


class AgentMemoryStore:
    """
    Extended memory store to support both unstructured chat history and structured result caching.
    Compatible with existing Agent architecture.
    """

    def __init__(self, user_id: str, agent_name: str, max_entries: int = 100):
        self.user_id = user_id
        self.agent_name = agent_name
        self.max_entries = max_entries
        self.key = f"agent_memory:{user_id}:{agent_name}"
        self.protected_key = f"agent_memory_protected:{user_id}:{agent_name}"
        self.results_key = f"agent_results:{user_id}:{agent_name}"
        self._cache = agent_cache
        self._ttl = 365 * 24 * 60 * 60  # 1 year TTL

    def _load_list(self, key: str) -> List[Dict[str, Any]]:
        data = self._cache.get(key)
        return data if isinstance(data, list) else []

    def _save_list(self, key: str, items: List[Dict[str, Any]]) -> None:
        self._cache.set(key, items, ttl=self._ttl)

    @staticmethod
    def _create_entry(role: str, content: str, protected: bool = False) -> Dict[str, Any]:
        return {
            "id": f"{int(time.time() * 1000)}_{hash(content) % 10000}",
            "timestamp": time.time(),
            "role": role,
            "content": content,
            "protected": protected,
        }

    def add_entry(self, role: str, content: str, protect: bool = False) -> str:
        entry = self._create_entry(role, content, protect)
        history = self._load_list(self.key)
        history.append(entry)

        protected_ids = set(self._cache.get(self.protected_key) or [])
        while len(history) > self.max_entries:
            oldest = history.pop(0)
            if oldest["id"] in protected_ids:
                history.append(oldest)
                if len([h for h in history if h["id"] not in protected_ids]) == 0:
                    break

        self._save_list(self.key, history)

        if protect:
            protected_ids.add(entry["id"])
            self._cache.set(self.protected_key, list(protected_ids), ttl=self._ttl)

        return entry["id"]

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        history = self._load_list(self.key)
        return history[-limit:] if limit else history

    def get_chat_messages(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.get_history(limit)
        ]

    def delete_entry(self, entry_id: str) -> bool:
        history = self._load_list(self.key)
        new_history = [h for h in history if h["id"] != entry_id]
        if len(new_history) == len(history):
            return False
        self._save_list(self.key, new_history)
        protected_ids = set(self._cache.get(self.protected_key) or [])
        protected_ids.discard(entry_id)
        self._cache.set(self.protected_key, list(protected_ids), ttl=self._ttl)
        return True

    def delete_entries(self, entry_ids: List[str]) -> Dict[str, bool]:
        return {eid: self.delete_entry(eid) for eid in entry_ids}

    # ------------------------------------------------------------------
    # Structured result caching
    # ------------------------------------------------------------------

    @staticmethod
    def _args_to_key(*args: Any, **kwargs: Any) -> str:
        identifier = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return f"args:{hash(identifier)}"

    def get_result(self, *args: Any, **kwargs: Any) -> Optional[str]:
        results = self._cache.get(self.results_key) or {}
        return results.get(self._args_to_key(*args, **kwargs))

    def save_result(self, result: str, *args: Any, **kwargs: Any) -> None:
        results = self._cache.get(self.results_key) or {}
        results[self._args_to_key(*args, **kwargs)] = result
        self._cache.set(self.results_key, results, ttl=self._ttl)

    def add_result(self, prompt: str, result: Any) -> None:
        """
        Adds a structured result (typically a model output) to the cache.
        This is a convenience method.
        """
        self.store_cached_result(prompt, result)

    # Key prefix for structured cache entries
    def _structured_cache_key(self, prompt_hash: str) -> str:
        return f"{self.key}:structured:{prompt_hash}"

    @staticmethod
    def _hash_prompt(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def get_cached_result(self, prompt: str) -> Optional[Any]:
        """Check if a structured result already exists for this prompt."""
        prompt_hash = self._hash_prompt(prompt)
        raw = self._cache.get(self._structured_cache_key(prompt_hash))
        if raw is None:
            return None

        try:
            return pickle.loads(raw)
        except (pickle.PickleError, EOFError, AttributeError, ImportError, IndexError):
            return None  # corrupted or invalid

    def store_cached_result(self, prompt: str, result: Any) -> None:
        """Store the structured result for this prompt."""
        prompt_hash = self._hash_prompt(prompt)
        try:
            serialized = pickle.dumps(result)
            self._cache.set(self._structured_cache_key(prompt_hash), serialized, ttl=self._ttl)
        except Exception as e:
            # Failsafe logging – avoid crashing due to serialization issues
            logger = get_service("logger")()("AgentMemoryStore")
            logger.error(f"Failed to store structured result: {e}")

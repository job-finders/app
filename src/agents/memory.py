import json
import time
from typing import List, Dict, Optional

from src.cache.cache_redis import agent_cache


class AgentMemoryStore:
    """
    Memory backed by the RedisCache wrapper (no raw redis calls).
    """

    def __init__(self, user_id: str, agent_name: str, max_entries: int = 100):
        self.user_id = user_id
        self.agent_name = agent_name
        self.max_entries = max_entries

        # keys used inside the cache
        self.key = f"agent_memory:{user_id}:{agent_name}"
        self.protected_key = f"agent_memory_protected:{user_id}:{agent_name}"

        # the cache instance (RedisCache already configured)
        self._cache = agent_cache
        self._ttl = 365 * 24 * 60 * 60  # one year

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------
    def _load_list(self, key: str) -> List[Dict]:
        """Return list stored under key, or empty list if missing."""
        data = self._cache.get(key)
        return data if isinstance(data, list) else []

    def _save_list(self, key: str, items: List[Dict]) -> None:
        """Persist list via RedisCache (pickled)."""
        self._cache.set(key, items, ttl=self._ttl)

    def _create_entry(self, role: str, content: str, protected: bool = False) -> Dict:
        """Return a dict (not JSON string) ready to append."""
        return {
            "id": f"{int(time.time() * 1000)}_{hash(content) % 10000}",
            "timestamp": time.time(),
            "role": role,
            "content": content,
            "protected": protected,
        }

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def add_entry(self, role: str, content: str, protect: bool = False) -> str:
        """Add entry, trim oldest if > max_entries (skipping protected)."""
        entry = self._create_entry(role, content, protect)

        # load current history
        history = self._load_list(self.key)

        # add new entry
        history.append(entry)

        # trim old entries
        protected_ids = set(self._cache.get(self.protected_key) or [])
        while len(history) > self.max_entries:
            oldest = history.pop(0)
            if oldest["id"] in protected_ids:
                # re-add at end (skip this cycle)
                history.append(oldest)
                # prevent infinite loop if all protected
                if len([h for h in history if h["id"] not in protected_ids]) == 0:
                    break

        # persist
        self._save_list(self.key, history)

        if protect:
            protected_ids.add(entry["id"])
            self._cache.set(self.protected_key, list(protected_ids), ttl=self._ttl)

        return entry["id"]

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        history = self._load_list(self.key)
        if limit:
            history = history[-limit:]
        return history

    def get_chat_messages(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.get_history(limit)
        ]

    def delete_entry(self, entry_id: str) -> bool:
        history = self._load_list(self.key)
        new_history = [h for h in history if h["id"] != entry_id]
        if len(new_history) == len(history):
            return False  # id not found

        self._save_list(self.key, new_history)

        # also remove from protected set
        protected_ids = set(self._cache.get(self.protected_key) or [])
        protected_ids.discard(entry_id)
        self._cache.set(self.protected_key, list(protected_ids), ttl=self._ttl)
        return True

    def delete_entries(self, entry_ids: List[str]) -> Dict[str, bool]:
        return {eid: self.delete_entry(eid) for eid in entry_ids}

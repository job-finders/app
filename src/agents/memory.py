import json
import time
from typing import List, Dict, Optional, Set
from src.config import config_instance
import redis


cfg = config_instance()


class AgentMemoryStore:
    def __init__(self, user_id: str, agent_name: str, max_entries: int = 100):
        self.user_id = user_id
        self.agent_name = agent_name
        self.max_entries = max_entries
        self.key = f"agent_memory:{user_id}:{agent_name}"
        self.protected_key = f"agent_memory_protected:{user_id}:{agent_name}"
        self.redis_store = redis.Redis(
            host=cfg.REDIS_HOST,
            port=cfg.REDIS_PORT,
            db=cfg.REDIS_DB,
            decode_responses=True
        )

    def _create_entry(self, role: str, content: str) -> str:
        """Create a memory entry with timestamp and unique ID."""
        entry = {
            "id": f"{int(time.time() * 1000)}_{hash(content) % 10000}",
            "timestamp": time.time(),
            "role": role,
            "content": content,
            "protected": False
        }
        return json.dumps(entry)

    def add_entry(self, role: str, content: str, protect: bool = False) -> str:
        """Add an entry to memory with automatic cleanup."""
        entry_data = json.loads(self._create_entry(role, content))
        entry_data["protected"] = protect
        entry_json = json.dumps(entry_data)
        
        # Add to main memory
        self.redis_store.rpush(self.key, entry_json)
        
        # Add to protected set if needed
        if protect:
            self.redis_store.sadd(self.protected_key, entry_data["id"])
        
        # Cleanup old entries
        self._cleanup_old_entries()
        
        return entry_data["id"]

    def _cleanup_old_entries(self):
        """Remove oldest entries when max_entries is exceeded."""
        current_count = self.redis_store.llen(self.key)
        
        if current_count > self.max_entries:
            # Get protected IDs
            protected_ids = self.redis_store.smembers(self.protected_key)
            
            # Calculate how many to remove
            to_remove = current_count - self.max_entries
            removed_count = 0
            
            # Remove from the left (oldest first)
            while removed_count < to_remove:
                oldest_entry = self.redis_store.lindex(self.key, 0)
                if not oldest_entry:
                    break
                
                try:
                    entry_data = json.loads(oldest_entry)
                    entry_id = entry_data.get("id")
                    
                    # Skip protected entries
                    if entry_id not in protected_ids:
                        self.redis_store.lpop(self.key)
                        removed_count += 1
                    else:
                        # Move protected entry to end temporarily
                        self.redis_store.lpop(self.key)
                        self.redis_store.rpush(self.key, oldest_entry)
                        
                        # Check if we've cycled through all entries
                        if removed_count == 0:
                            break
                except json.JSONDecodeError:
                    # Remove malformed entries
                    self.redis_store.lpop(self.key)
                    removed_count += 1

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Retrieve memory history with optional limit."""
        if limit:
            raw_entries = self.redis_store.lrange(self.key, -limit, -1)
        else:
            raw_entries = self.redis_store.lrange(self.key, 0, -1)
        
        history = []
        for entry in raw_entries:
            try:
                parsed = json.loads(entry)
                history.append({
                    "id": parsed.get("id"),
                    "timestamp": parsed.get("timestamp"),
                    "role": parsed["role"],
                    "content": parsed["content"],
                    "protected": parsed.get("protected", False)
                })
            except json.JSONDecodeError:
                continue
        
        return history

    def get_chat_messages(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Get messages in chat format (role, content only)."""
        history = self.get_history(limit)
        return [{"role": msg["role"], "content": msg["content"]} for msg in history]

    def delete_entry(self, entry_id: str) -> bool:
        """Delete a specific entry by ID."""
        entries = self.redis_store.lrange(self.key, 0, -1)
        
        for i, entry in enumerate(entries):
            try:
                parsed = json.loads(entry)
                if parsed.get("id") == entry_id:
                    # Remove from main list
                    self.redis_store.lrem(self.key, 1, entry)
                    # Remove from protected set
                    self.redis_store.srem(self.protected_key, entry_id)
                    return True
            except json.JSONDecodeError:
                continue
        
        return False

    def delete_entries(self, entry_ids: List[str]) -> Dict[str, bool]:
        """Delete multiple entries by ID."""
        results = {}
        for entry_id in entry_ids:
            results[entry_id] = self.delete_entry(entry_id)
        return results

    def protect_entry(self, entry_id: str) -> bool:
        """Mark an entry as protected from automatic cleanup."""
        entries = self.redis_store.lrange(self.key, 0, -1)
        
        for i, entry in enumerate(entries):
            try:
                parsed = json.loads(entry)
                if parsed.get("id") == entry_id:
                    parsed["protected"] = True
                    updated_entry = json.dumps(parsed)
                    self.redis_store.lset(self.key, i, updated_entry)
                    self.redis_store.sadd(self.protected_key, entry_id)
                    return True
            except json.JSONDecodeError:
                continue
        
        return False

    def unprotect_entry(self, entry_id: str) -> bool:
        """Remove protection from an entry."""
        entries = self.redis_store.lrange(self.key, 0, -1)
        
        for i, entry in enumerate(entries):
            try:
                parsed = json.loads(entry)
                if parsed.get("id") == entry_id:
                    parsed["protected"] = False
                    updated_entry = json.dumps(parsed)
                    self.redis_store.lset(self.key, i, updated_entry)
                    self.redis_store.srem(self.protected_key, entry_id)
                    return True
            except json.JSONDecodeError:
                continue
        
        return False

    def get_protected_entries(self) -> List[Dict[str, str]]:
        """Get all protected entries."""
        protected_ids = self.redis_store.smembers(self.protected_key)
        history = self.get_history()
        return [entry for entry in history if entry.get("id") in protected_ids]

    def get_memory_stats(self) -> Dict[str, int]:
        """Get memory usage statistics."""
        total_entries = self.redis_store.llen(self.key)
        protected_count = self.redis_store.scard(self.protected_key)
        
        return {
            "total_entries": total_entries,
            "protected_entries": protected_count,
            "deletable_entries": total_entries - protected_count,
            "max_entries": self.max_entries,
            "remaining_capacity": max(0, self.max_entries - total_entries)
        }

    def clear(self, keep_protected: bool = False):
        """Clear memory with option to keep protected entries."""
        if keep_protected:
            # Keep only protected entries
            protected_ids = self.redis_store.smembers(self.protected_key)
            if protected_ids:
                all_entries = self.redis_store.lrange(self.key, 0, -1)
                self.redis_store.delete(self.key)
                
                for entry in all_entries:
                    try:
                        parsed = json.loads(entry)
                        if parsed.get("id") in protected_ids:
                            self.redis_store.rpush(self.key, entry)
                    except json.JSONDecodeError:
                        continue
            else:
                self.redis_store.delete(self.key)
        else:
            # Clear everything
            self.redis_store.delete(self.key)
            self.redis_store.delete(self.protected_key)

    def set_max_entries(self, max_entries: int):
        """Update maximum entries and trigger cleanup if needed."""
        self.max_entries = max_entries
        self._cleanup_old_entries()
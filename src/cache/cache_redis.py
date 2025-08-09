import inspect
import redis
import pickle
import functools
import hashlib
import re
from typing import Callable, Optional
from flask import has_request_context, g

# ------------------------------
# Cache Key Utilities
# ------------------------------
def generate_cache_key(func: Callable, args: tuple, kwargs: dict) -> str:
    """
    Generates a stable cache key from function and arguments.
    """
    try:
        # Remove 'self' or 'cls' from args for methods
        if inspect.ismethod(func) or (args and hasattr(args[0], func.__name__)):
            args = args[1:]
    except Exception:
        pass

    args_repr = ','.join(repr(a) for a in args)
    kwargs_repr = ','.join(f"{k}={repr(v)}" for k, v in sorted(kwargs.items()))

    user_id = ""
    if has_request_context():
        user_id = f"|user={getattr(getattr(g, 'user', None), 'uid', 'anon')}"

    base_key = f"{func.__module__}.{func.__qualname__}({args_repr}{',' if args and kwargs else ''}{kwargs_repr}){user_id}"
    hashed = hashlib.md5(base_key.encode()).hexdigest()
    return sanitize_cache_key(f"{func.__name__}_{hashed}")

def sanitize_cache_key(key: str) -> str:
    """Ensure Redis-safe key length and characters."""
    return re.sub(r'[^\w\-\.]', '_', key)[:250]

# ------------------------------
# Redis Cache Handler
# ------------------------------
class RedisCache:
    def __init__(self, prefix="jobfinders_cache:", default_ttl=30 * 60, **redis_kwargs):
        self.redis = redis.Redis(**redis_kwargs)
        self.prefix = prefix
        self.default_ttl = default_ttl

    def _prefixed(self, key: str) -> str:
        return f"{self.prefix}{key}"

    def get(self, key: str):
        try:
            data = self.redis.get(self._prefixed(key))
            return pickle.loads(data) if data else None
        except Exception as e:
            print(f"[Cache:get] Error: {e}")
            return None

    def get_many(self, keys: list) -> dict:
        """
        Retrieve multiple cached values at once.

        Args:
            keys (list): List of cache keys (without prefix).

        Returns:
            dict: Mapping from key to cached value (unpickled). Missing keys are excluded.
        """
        try:
            # Prefix all keys for redis
            prefixed_keys = [self._prefixed(k) for k in keys]

            # Bulk fetch using mget
            raw_values = self.redis.mget(prefixed_keys)

            # Map original keys to unpickled values, skipping missing
            result = {}
            for key, raw in zip(keys, raw_values):
                if raw is not None:
                    try:
                        result[key] = pickle.loads(raw)
                    except Exception as e:
                        print(f"[Cache:get_many] Unpickle error for key {key}: {e}")
                        # skip or set None if you want
            return result
        except Exception as e:
            print(f"[Cache:get_many] Error fetching multiple keys: {e}")
            return {}

    def set(self, key: str, value, ttl: Optional[int] = None):
        try:
            ttl = ttl or self.default_ttl
            self.redis.setex(self._prefixed(key), ttl, pickle.dumps(value))
        except Exception as e:
            print(f"[Cache:set] Error: {e}")

    def __contains__(self, key: str) -> bool:
        try:
            return self.redis.exists(self._prefixed(key)) == 1
        except Exception:
            return False

    def clear(self):
        try:
            cursor = 0
            pattern = self._prefixed("jobfinders_cache:")
            while True:
                cursor, keys = self.redis.scan(cursor=cursor, match=pattern)
                if keys:
                    self.redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            print(f"[Cache:clear] Error: {e}")

    def delete(self, key: str):
        try:
            self.redis.delete(self._prefixed(key))
        except Exception as e:
            print(f"[Cache:delete] Error: {e}")

    def keys(self):
        try:
            return [k.decode() for k in self.redis.keys(self._prefixed("*"))]
        except Exception:
            return []

    def __repr__(self):
        return f"<RedisCache prefix='{self.prefix}'>"

# ------------------------------
# Decorator: Cached
# ------------------------------
def cached(ttl: Optional[int] = None):
    """
    Usage:
        @cached()
        def my_func(...): ...

        @cached(ttl=60)
        async def my_async_func(...): ...
    """
    def decorator(func: Callable):
        is_async = inspect.iscoroutinefunction(func)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = generate_cache_key(func, args, kwargs)
            if (result := route_cache.get(key)) is not None:
                return result
            result = func(*args, **kwargs)
            route_cache.set(key, result, ttl)
            return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            key = generate_cache_key(func, args, kwargs)
            if (result := route_cache.get(key)) is not None:
                return result
            result = await func(*args, **kwargs)
            route_cache.set(key, result, ttl)
            return result

        return async_wrapper if is_async else sync_wrapper

    return decorator

# ------------------------------
# Instantiate Global Cache
# ------------------------------
route_cache = RedisCache(prefix="jobfinders_route_cache:")
cache = RedisCache(prefix="jobfinders_cache:", default_ttl=60 * 60, host="localhost", port=6379, db=0)
agent_cache = RedisCache(prefix="jobfinders_agent_cache:", default_ttl=60 * 60, host="localhost", port=6379, db=0)

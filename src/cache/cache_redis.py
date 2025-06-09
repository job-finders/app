import inspect
from typing import Callable
import redis
import pickle
import functools
from src.utils import generate_cache_key


class RedisCache:
    """Redis-based caching implementation with TTL support."""
    
    def __init__(self, prefix="jobfinders_route_cache:", default_ttl=12 * 60 * 60, **redis_kwargs):
        """
        Initialize Redis cache.
        
        :param prefix: Optional prefix for all cache keys
        :param default_ttl: Default TTL in seconds (12 hours by default)
        :param redis_kwargs: Redis connection parameters (host, port, db, etc.)
        """
        self.redis = redis.Redis(**redis_kwargs)
        self.prefix = prefix
        self.default_ttl = default_ttl

    def _prefixed(self, key):
        """Add prefix to key for Redis namespace separation."""
        return f"{self.prefix}{key}"

    def get(self, key):
        """Retrieve item from cache."""
        value_data = self.redis.get(self._prefixed(key))
        return pickle.loads(value_data) if value_data else None

    def set(self, key, value, ttl=None):
        """Store item in cache with optional TTL."""
        ttl = ttl if ttl is not None else self.default_ttl
        self.redis.setex(
            self._prefixed(key),
            ttl,
            pickle.dumps(value)
        )

    def __contains__(self, key):
        """Check if key exists in cache (may return True for expired keys)."""
        return self.redis.exists(self._prefixed(key)) == 1

    def clear(self):
        """Clear all cached items with current prefix."""
        cursor = '0'
        pattern = self._prefixed("*")
        while cursor != 0:
            cursor, keys = self.redis.scan(cursor=cursor, match=pattern)
            if keys:
                self.redis.delete(*keys)

    def __delitem__(self, key):
        """Remove specific key from cache."""
        self.redis.delete(self._prefixed(key))

    def __len__(self):
        """Get approximate number of cached items."""
        return len(self.redis.keys(self._prefixed("*")))

    def __iter__(self):
        """Iterate through all cache keys (without prefix)."""
        prefix_len = len(self.prefix)
        cursor = '0'
        while True:
            cursor, keys = self.redis.scan(cursor=cursor, match=self._prefixed("*"))
            for key in keys:
                yield key.decode()[prefix_len:]
            if cursor == 0:
                break

    def __repr__(self):
        return f"RedisCache(prefix='{self.prefix}', default_ttl={self.default_ttl})"


# Initialize with default Redis connection (localhost:6379)
route_cache = RedisCache(prefix="jobfinders_route_cache:")

def cached(f: Callable) -> Callable:
    """Decorator to cache sync or async function results in Redis."""
    @functools.wraps(f)
    def sync_wrapper(*args, **kwargs):
        cache_key = sanitize_cache_key(generate_cache_key(f, *args, **kwargs))
        if (cached_result := route_cache.get(cache_key)) is not None:
            return cached_result
        
        result = f(*args, **kwargs)
        route_cache.set(cache_key, result)
        return result

    @functools.wraps(f)
    async def async_wrapper(*args, **kwargs):
        cache_key = sanitize_cache_key(generate_cache_key(f, *args, **kwargs))
        if (cached_result := route_cache.get(cache_key)) is not None:
            return cached_result

        result = await f(*args, **kwargs)
        route_cache.set(cache_key, result)
        return result

    return async_wrapper if inspect.iscoroutinefunction(f) else sync_wrapper

# src/utils/caching.py
from flask import current_app, request
from functools import wraps
import hashlib


def cache_response(ttl=60):
    """Decorator for response caching"""

    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{request.endpoint}:{hashlib.md5(request.data).hexdigest()}"

            # Try to get cached response
            if cached := current_app.cache.get(cache_key):
                return cached

            # Execute and cache
            response = await f(*args, **kwargs)
            current_app.cache.set(cache_key, response, ttl)
            return response

        return wrapper

    return decorator

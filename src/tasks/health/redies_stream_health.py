import redis
from src.config import config_instance

def check_redis_stream_health(stream_name="email:queue", min_length_warning=1):
    """
    Performs a basic health check on a Redis Stream.

    - Confirms Redis is reachable
    - Confirms the stream exists (has messages or was created)
    - Warns if there's a large backlog (optional)

    Returns a dict with health status.
    """
    settings = config_instance().REDIS_SETTINGS
    redis_client = redis.Redis.from_url(settings.URL)

    health = {"reachable": False, "stream_exists": False, "length": 0, "ok": False}

    try:
        redis_client.ping()
        health["reachable"] = True

        if redis_client.exists(stream_name):
            stream_length = redis_client.xlen(stream_name)
            health["stream_exists"] = True
            health["length"] = stream_length
            health["ok"] = stream_length <= min_length_warning
        else:
            # Even if it doesn't exist, maybe that's okay (no emails yet)
            health["ok"] = True

    except redis.ConnectionError as e:
        health["error"] = f"Redis unreachable: {str(e)}"
    except Exception as e:
        health["error"] = f"Unexpected error: {str(e)}"

    return health

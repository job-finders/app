import redis
import json  # For serialization
from typing import Optional, Dict, Any

class RedisClientFactory:
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        decode_responses: bool = True,
        max_connections: int = 20,
        **kwargs
    ):
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            decode_responses=decode_responses,
            max_connections=max_connections,
            **kwargs
        )
    
    def get_client(self) -> redis.Redis:
        return redis.Redis(connection_pool=self.pool)

class BaseRedisQueue(RedisClientFactory):
    def __init__(self, queue_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = self.get_client()  # Consistent naming
        self._queue_name = queue_name

    def send_to_queue(self, item: Dict[str, Any]):
        # Serialize dictionary to JSON string
        serialized_item = json.dumps(item)
        self._client.rpush(self._queue_name, serialized_item)

    def get_from_queue(self) -> Optional[Dict[str, Any]]:
        # Returns tuple (list_name, data) or None
        result = self._client.blpop(self._queue_name, timeout=30)
        if result is None:
            return None
        # Deserialize the JSON string
        return json.loads(result[1])

class EmailQueueFactory(BaseRedisQueue):
    def __init__(self, *args, **kwargs):
        # Set default queue name if not provided
        kwargs.setdefault('queue_name', 'email_queue')
        super().__init__(*args, **kwargs)

class EventsQueueFactory(BaseRedisQueue):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('queue_name', 'events_queue')
        super().__init__(*args, **kwargs)

# Usage
email_queue = EmailQueueFactory(host='localhost', db=1)
events_queue = EventsQueueFactory(host='localhost', db=1)

import redis, json

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def enqueue_realtime_event(event_data: dict):
    stream_key = "billing:realtime_events"
    redis_client.xadd(stream_key, {"data": json.dumps(event_data)})


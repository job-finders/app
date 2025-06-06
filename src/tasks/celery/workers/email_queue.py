import json
import redis
from src.emailer import EmailModel

# Initialize Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def enqueue_email(email: EmailModel):
    stream_key = "email:send"
    email_data = email.model_dump()
    redis_client.xadd(stream_key, {"data": json.dumps(email_data)})

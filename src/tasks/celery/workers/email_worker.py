import asyncio
from pydantic import BaseModel, Field
import json
import redis.asyncio as aioredis

STREAM_KEY = "email:send"
CONSUMER_GROUP = "email-workers"
CONSUMER_NAME = "worker-1"

class EmailModel(BaseModel):
    from_: str | None = Field(default=None)
    to_: str | None = Field(default=None)
    subject_: str
    html_: str

def get_logger():
    import logging
    logger = logging.getLogger("email_worker")
    logging.basicConfig(level=logging.INFO)
    return logger

logger = get_logger()

async def ensure_consumer_group(redis_conn):
    try:
        await redis_conn.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id='0', mkstream=True)
        logger.info("Consumer group created.")
    except aioredis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info("Consumer group already exists.")
        else:
            raise

async def email_worker():
    from src.emailer import SendMail
    mailer = SendMail()  # instead of get_service("send_mail")()

    redis_conn = aioredis.Redis(host="localhost", port=6379, decode_responses=True)
    await ensure_consumer_group(redis_conn)
    while True:
        try:
            resp = await redis_conn.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={STREAM_KEY: '>'},
                count=5,
                block=5000  # 5 seconds
            )

            for stream, messages in resp:
                for msg_id, msg in messages:
                    try:
                        payload = json.loads(msg["data"])
                        email = EmailModel(**payload)

                        logger.info(f"Sending email to: {email.to_}")
                        await mailer.send_mail_resend(email=email, direct_send=True)

                        await redis_conn.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
                        logger.info(f"Acked message {msg_id}")

                    except Exception as e:
                        logger.error(f"Failed to process message {msg_id}: {e}")

        except Exception as e:
            logger.error(f"Redis error: {e}")
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(email_worker())

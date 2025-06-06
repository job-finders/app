import asyncio
from pydantic import BaseModel, Field
import json
import redis.asyncio as aioredis
import logging
import signal
import sys
import time

# Constants
STREAM_KEY = "email:send"
CONSUMER_GROUP = "email-workers"
CONSUMER_NAME = "worker-1"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
BLOCK_TIMEOUT_MS = 5000  # 5 seconds

# Email schema
class EmailModel(BaseModel):
    from_: str | None = Field(default=None)
    to_: str | None = Field(default=None)
    subject_: str
    html_: str

# Logger setup
def get_logger():
    logger = logging.getLogger("email_worker")
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

logger = get_logger()

# Redis group init
async def ensure_consumer_group(redis_conn):
    try:
        await redis_conn.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id='0', mkstream=True)
        logger.info("Consumer group created.")
    except aioredis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info("Consumer group already exists.")
        else:
            raise

# Email worker core loop
async def email_worker():
    from src.emailer import SendMail
    mailer = SendMail()

    redis_conn = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    await ensure_consumer_group(redis_conn)

    async def shutdown_handler():
        logger.info("Shutting down email worker...")
        await redis_conn.close()
        await redis_conn.connection_pool.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGTERM, lambda *_: asyncio.create_task(shutdown_handler()))
    signal.signal(signal.SIGINT, lambda *_: asyncio.create_task(shutdown_handler()))

    logger.info("Email worker is running...")

    while True:
        try:
            resp = await redis_conn.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={STREAM_KEY: '>'},
                count=5,
                block=BLOCK_TIMEOUT_MS
            )

            if not resp:
                continue

            for stream, messages in resp:
                for msg_id, msg in messages:
                    start = time.time()
                    try:
                        payload = json.loads(msg["data"])
                        email = EmailModel(**payload)

                        logger.info(f"[{msg_id}] Sending to: {email.to_}")
                        await mailer.send_mail_resend(email=email, direct_send=True)

                        await redis_conn.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
                        logger.info(f"[{msg_id}] Sent and acked in {time.time() - start:.2f}s")

                    except Exception as e:
                        logger.exception(f"[{msg_id}] Failed to process email: {e}")

        except Exception as e:
            logger.exception(f"Redis error or unexpected crash: {e}")
            await asyncio.sleep(2)  # Backoff

# Entrypoint
if __name__ == "__main__":
    try:
        asyncio.run(email_worker())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")

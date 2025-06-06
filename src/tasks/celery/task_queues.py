import asyncio

from src.utils.route_helpers import get_service
from src.emailer import EmailModel

def create_task_queues(celery_app):
    @celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
    def celery_send_email(self, email_data: dict):
        logger = get_service("logger")()("CELERY: Email Task")
        try:
            email = EmailModel(**email_data)
            mailer = get_service("send_mail")()

            async def send():
                _mailer = get_service("send_mail")()
                return await _mailer.send_mail_resend(email=email)

            result = asyncio.run(send())  # Run the async function
            logger.info(f"Sent email: {email.to_} | Subject: {email.subject_}")
            return result
        except Exception as e:
            logger.error(f"Email send failed, retrying: {e}")
            raise self.retry(exc=e)

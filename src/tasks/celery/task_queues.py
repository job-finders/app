import asyncio

from src.utils.route_helpers import get_service
from src.emailer import EmailModel

def create_task_queues(celery_app):
    @celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
    def celery_send_email(self, email_data: dict):
        pass


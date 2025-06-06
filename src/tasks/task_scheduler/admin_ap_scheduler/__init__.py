import asyncio

from src.utils.route_helpers import get_controller, get_service

def schedule_company_tasks(scheduler, app):
    """Schedule periodic company-related background tasks"""

    logger = get_service("logger")()("company_tasks")
    logger.info("###### Initializing company background ######")
    company_controller = get_controller("company")

    def async_job_wrapper(coro):
        def wrapper():
            with app.app_context():
                try:
                    logger.info("Running auto document verification job")
                    asyncio.run(coro())
                except Exception as e:
                    logger.error(f"Document verification job failed: {e}", exc_info=True)
        return wrapper

    """
        This task may run in celery or task scheduler.
        fetch documents that have not been reviewed or without recommendations -
        check if company profiles have been properlu completed and verified.
        send the documents to a company agent document verifier.
    """
    scheduler.add_job(
        async_job_wrapper(company_controller.auto_verify_company_documents),
        'interval',
        minutes=30,
        id='document_verification',
        replace_existing=True
    )
    logger.info("Scheduled: document_verification every 30 Minutes")

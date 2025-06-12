import asyncio
from src.utils.route_helpers import get_controller, get_service

def schedule_app_tasks(scheduler, app):
    """Schedule all periodic tasks that need Flask context."""

    with app.app_context():
        admin_controller = get_controller("admin_controller")
        company_controller = get_controller("company")
        billing_controller = get_controller("billing")

        logger = get_service("logger")()("app_scheduler")
        logger.info("###### Initializing App Scheduler ######")

        def async_job_wrapper(job_name, func):
            def wrapper():
                with app.app_context():
                    try:
                        logger.info(f"Running scheduled job: {job_name}")
                        # Check if function is async
                        if asyncio.iscoroutinefunction(func):
                            asyncio.run(func())
                        else:
                            func()  # Run synchronous functions directly
                    except Exception as e:
                        logger.error(f"Job '{job_name}' failed: {e}", exc_info=True)
            return wrapper

        # === Company Jobs ===
        scheduler.add_job(
            async_job_wrapper("document_verification", company_controller.auto_verify_company_documents),
            trigger='interval',
            minutes=30,
            id='document_verification',
            replace_existing=True
        )

        # === Former Celery Beat Jobs ===
        scheduler.add_job(
            async_job_wrapper("clean_up_old_job_approvals", admin_controller.cleanup_old_approvals),
            trigger='cron',
            day_of_week='sun',
            hour=1,
            minute=0,
            id='clean_up_old_job_approvals',
            replace_existing=True
        )

        scheduler.add_job(
            async_job_wrapper("approve_jobs", admin_controller.approve_jobs),
            trigger='interval',
            minutes=30,
            id='approve_jobs',
            replace_existing=True
        )

        scheduler.add_job(
            async_job_wrapper("send_job_alerts", admin_controller.send_job_alerts_to_users),
            trigger='cron',
            minute=0,
            hour=7,
            id='send_job_alerts',
            replace_existing=True
        )

        # Flagging suspicious activity
        scheduler.add_job(
            async_job_wrapper("flag_unusual_user_activity", admin_controller.flag_unusual_user_activity),
            trigger='cron',
            hour=2,
            minute=0,
            id='flag_unusual_user_activity',
            replace_existing=True
        )

        # Evaluate risks based on that flag
        scheduler.add_job(
            async_job_wrapper("evaluate_user_risks", admin_controller.evaluate_user_risks),
            trigger='cron',
            hour=2,
            minute=30,
            id='evaluate_user_risks',
            replace_existing=True
        )

        scheduler.add_job(
            async_job_wrapper("detect_anomalous_jobs", admin_controller.detect_anomalous_job_postings),
            trigger='cron',
            hour=3,
            minute=0,
            id='detect_anomalous_jobs',
            replace_existing=True
        )
        scheduler.add_job(
            async_job_wrapper("update_subscriptions", billing_controller.cron_update_subscription_states),
            trigger='cron',
            hour=3,
            minute=0,
            timezone='UTC',
            id='update_billing_subscriptions',
            replace_existing=True
        )
        scheduler.add_job(
            async_job_wrapper("billing_cron_jobs", billing_controller.cron_billing),
            trigger='interval',
            minutes=120,
            id='billing_cronjob',
            replace_existing=True
        )

        logger.info("Scheduled: All tasks initialized in app scheduler.")

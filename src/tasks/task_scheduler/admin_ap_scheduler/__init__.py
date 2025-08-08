import asyncio
import time
from psutil import cpu_percent
from redis.lock import Lock

from src.utils.route_helpers import get_controller, get_service
from redis import Redis


def schedule_app_tasks(scheduler, app):
    """Schedule all periodic tasks that need Flask context."""

    with app.app_context():
        admin_controller = get_controller("admin_controller")
        company_controller = get_controller("company")
        billing_controller = get_controller("billing")

        # ---------- inside schedule_app_tasks ----------
        # after the existing scheduler setup
        blog_controller = get_controller("blog_agent_controller")

        # Configure job defaults to prevent overlapping runs
        scheduler.add_jobstore('sqlalchemy', url=app.config['SQLALCHEMY_DATABASE_URI'])
        scheduler.add_executor('threadpool', max_workers=5)  # Limit concurrent jobs
        
        job_defaults = {
            'coalesce': True,  # Combine multiple pending runs
            'max_instances': 1,  # Only 1 instance per job
            'misfire_grace_time': 3600  # 1 hour grace period
        }
        scheduler.configure(job_defaults=job_defaults)

        logger = get_service("logger")()("app_scheduler")
        logger.info("###### Initializing App Scheduler ######")

        def log_job_run(job_name: str, duration: float, success: bool):
            """
            Logs the result of a scheduled job run.

            :param job_name: Name of the job
            :param duration: Duration in seconds
            :param success: Whether the job succeeded
            :return:
            """
            status = "SUCCESS" if success else "FAILURE"
            logger.info(f"Job '{job_name}' finished with status: {status} in {duration:.2f} seconds")

        def async_job_wrapper(job_name, func):
            def wrapper():
                # Redis Lock helps lockout same jobs from executing at once
                with Lock(Redis(), "job_lock:" + job_name):
                    if cpu_percent() > 80:
                        logger.warning("Delaying job due to high CPU")
                        time.sleep(300)
                    with app.app_context():
                        try:
                            success = True
                            logger.info(f"Running scheduled job: {job_name}")
                            # Check if function is async
                            if asyncio.iscoroutinefunction(func):
                                start = time.monotonic()
                                asyncio.run(func())
                            else:
                                start = time.monotonic()
                                func()  # Run synchronous functions directly
                        except Exception as e:
                            success = False
                            logger.error(f"Job '{job_name}' failed: {str(e)}", exc_info=True)
                        finally:
                            duration = time.monotonic() - start
                            log_job_run(job_name, duration, success=success)
            return wrapper

        # === Company Jobs ===
        # Verifies Company Documents based on AI Agents.
        scheduler.add_job(
            async_job_wrapper("document_verification", company_controller.auto_verify_company_documents),
            trigger='cron',
            hour=5,
            minute=30,
            id='document_verification',
            jitter=300,
            replace_existing=True)

        # === Former Celery Beat Jobs ===
        scheduler.add_job(
            async_job_wrapper("clean_up_old_job_approvals", admin_controller.cleanup_old_approvals),
            trigger='cron',
            day_of_week='sun',
            hour=1,
            minute=0,
            id='clean_up_old_job_approvals',
            jitter=300,
            replace_existing=True)
        # Approve Job Schedule must run every 30 minutes
        scheduler.add_job(
            async_job_wrapper("approve_jobs", admin_controller.approve_jobs),
            trigger='interval',
            minutes=5,
            id='approve_jobs',
            jitter=300,
            replace_existing=True)
        # cron hour 7
        scheduler.add_job(
            async_job_wrapper("send_job_alerts", admin_controller.send_job_alerts_to_users),
            trigger='cron',
            minute=0,
            hour=7,
            id='send_job_alerts',
            jitter=300,
            replace_existing=True)

        # Flagging suspicious activity
        # cron hour 2
        scheduler.add_job(
            async_job_wrapper("flag_unusual_user_activity", admin_controller.flag_unusual_user_activity),
            trigger='cron',
            minute=5,
            hour=2,
            id='flag_unusual_user_activity',
            jitter=300,
            replace_existing=True)

        # Evaluate risks based on that flag
        # cron hour 2 , minute 45
        scheduler.add_job(
            async_job_wrapper("evaluate_user_risks", admin_controller.evaluate_user_risks),
            trigger='cron',
            minute=2,
            hour=2,
            id='evaluate_user_risks',
            jitter=300,
            replace_existing=True)
        # This will detect anomalous job postings
        # CRON hour 3
        scheduler.add_job(
            async_job_wrapper("detect_anomalous_jobs", admin_controller.detect_anomalous_job_postings),
            trigger='cron',
            minute=3,
            hour=3,
            id='detect_anomalous_jobs',
            jitter=300,
            replace_existing=True)
        # cron hour 4 TODO - standardize Update Subscription and Billing
        scheduler.add_job(
            async_job_wrapper("update_subscriptions", billing_controller.cron_update_subscription_states),
            trigger='cron',
            hour=4,
            minute=4,
            timezone='UTC',
            id='update_billing_subscriptions',
            jitter=300,
            replace_existing=True)
        # interval every 2 hours
        scheduler.add_job(
            async_job_wrapper("billing_cron_jobs", billing_controller.cron_billing),
            trigger='interval',
            minutes=1,
            hours=2,
            id='billing_cron_jobs',
            jitter=300,
            replace_existing=True)

        # ---- blog pipeline (no overlap with existing jobs) ----
        scheduler.add_job(
            async_job_wrapper("blog_topic_generator", blog_controller.cron_topic_generator),
            trigger='cron',
            hour=0, minute=5,  # 00:05 UTC
            id='blog_topic_generator',
            jitter=300, replace_existing=True
        )

        scheduler.add_job(
            async_job_wrapper("blog_article_creator", blog_controller.cron_article_creator),
            trigger='cron',
            hour=2, minute=0,  # 02:00 UTC
            id='blog_article_creator',
            jitter=300, replace_existing=True
        )

        scheduler.add_job(
            async_job_wrapper("blog_draft_scheduler", blog_controller.cron_draft_scheduler),
            trigger='cron',
            hour=3, minute=0,  # 03:00 UTC
            id='blog_draft_scheduler',
            jitter=300, replace_existing=True
        )

        scheduler.add_job(
            async_job_wrapper("blog_feedback_gatherer", blog_controller.cron_feedback_gatherer),
            trigger='cron',
            hour=9, minute=0,  # 09:00 UTC
            id='blog_feedback_gatherer',
            jitter=300, replace_existing=True
        )

        logger.info("Scheduled: All tasks initialized in app scheduler.")

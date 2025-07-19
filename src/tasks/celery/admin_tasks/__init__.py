from asgiref.sync import async_to_sync

from src.utils.route_helpers import get_service, get_controller
from src.tasks.celery import celery_app


def obtain_admin_user():
    admin_controller = get_controller("admin_controller")
    logger_service = get_service("logger")()("CELERY: Clean Up Old Applications")
    # Obtaining System Admin User in order to execute system command
    admin_user_results = admin_controller.get_system_admin()
    logger_service.info(admin_user_results)

    if admin_user_results.success:
        return admin_user_results.data
    return None


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 5, 'countdown': 60}, retry_backoff=True)
def celery_clean_up_old_job_approvals(self):
    """Celery task to clean up old job approvals"""
    logger_service = get_service("logger")()("CELERY: Clean Up Old Applications")
    try:
        admin_controller = get_controller("admin_controller")
        results = async_to_sync(admin_controller.cleanup_old_approvals())
        logger_service.info(results.model_dump())
        return results
    except Exception as e:
        logger_service.error(f"Retrying after failure: {e}")
        raise self.retry(exc=e)

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 5, 'countdown': 60}, retry_backoff=True)
def celery_detect_anomalous_job_postings(self):
    """
        Identify suspicious jobs using multi-factor analysis.
        Output: List of anomalous job postings.
    :return:
    """
    logger_service = get_service("logger")()("CELERY: Clean Up Old Applications")
    try:
        admin_controller = get_controller("admin_controller")
        results = async_to_sync(admin_controller.detect_anomalous_job_postings())
        logger_service.info(results.model_dump())
        return results
    except Exception as e:
        logger_service.error(f"Retrying after failure: {e}")
        raise self.retry(exc=e)

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 5, 'countdown': 60}, retry_backoff=True)
def celery_flag_unusual_user_activity(self):
    """

    :return:
    """
    logger_service = get_service("logger")()("CELERY: Clean Up Old Applications")
    try:
        admin_controller = get_controller("admin_controller")
        admin_user = obtain_admin_user()

        action_results = async_to_sync(admin_controller.flag_unusual_user_activity(admin_uid=admin_user.admin_uid))
        logger_service.info(action_results)
        return action_results
    except Exception as e:
        logger_service.error(f"Retrying after failure: {e}")
        raise self.retry(exc=e)

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 5, 'countdown': 60}, retry_backoff=True)
def celery_evaluate_user_risks(self):
    """
        Run risk evaluations on flagged users and log admin recommendations.
    :return:
    """
    logger_service = get_service("logger")()("CELERY: Clean Up Old Applications")
    try:
        admin_controller = get_controller("admin_controller")

        admin_user = obtain_admin_user()

        # Run risk evaluations on flagged users and log admin recommendations.
        action_results = async_to_sync(admin_controller.evaluate_user_risks(admin_uid=admin_user.admin_uid))
        logger_service.info(action_results)
        return action_results
    except Exception as e:
        logger_service.error(f"Retrying after failure: {e}")
        raise self.retry(exc=e)

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 5, 'countdown': 60}, retry_backoff=True)
def celery_send_job_alerts_to_users(self):
    """
        Send job alerts to users based on their preferences
    :return:
    """
    logger_service = get_service("logger")()("CELERY: Clean Up Old Applications")
    try:
        admin_controller = get_controller("admin_controller")
        # Send job alerts to users based on their preferences
        action_results = async_to_sync(admin_controller.send_job_alerts_to_users())
        logger_service.info(action_results)
        return action_results
    except Exception as e:
        logger_service.error(f"Retrying after failure: {e}")
        raise self.retry(exc=e)




from celery import Celery

def make_celery_app():
    celery_app = Celery("jobfinders")

    celery_app.conf.broker_url = "redis://localhost:6379/0"
    celery_app.conf.result_backend = "redis://localhost:6379/1"

    celery_app.conf.beat_scheduler = "celery.beat:PersistentScheduler"
    celery_app.conf.beat_schedule_filename = "celerybeat-schedule"
    celery_app.conf.timezone = "UTC"
    return celery_app

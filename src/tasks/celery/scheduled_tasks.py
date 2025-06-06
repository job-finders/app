from celery.schedules import crontab

def schedule_celery_tasks(celery_app):
    celery_app.conf.beat_schedule = {
        'clean-up-old-job-approvals-every-hour': {
            'task': 'src.tasks.celery.admin_tasks.celery_clean_up_old_job_approvals',
            'schedule': crontab(minute=0, hour='*'),  # every hour
        },
        'send-job-alerts-daily': {
            'task': 'src.tasks.celery.admin_tasks.celery_send_job_alerts_to_users',
            'schedule': crontab(minute=0, hour=9),  # every day at 9 AM
        },
    }

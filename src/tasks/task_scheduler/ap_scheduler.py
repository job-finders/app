# In your app initialization
from apscheduler.schedulers.background import BackgroundScheduler




def create_scheduler(app):
    scheduler = BackgroundScheduler()

    def shutdown_scheduler(exc=None):
        scheduler.shutdown()
    return scheduler



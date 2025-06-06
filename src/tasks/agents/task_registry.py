# agents/task_registry.py
from tasks.celery.scheduled_tasks import sync_hashnode_posts

class PeriodicAgentTaskRegistry:
    def __init__(self):
        self.commands = {
            "trigger_hashnode_sync": {
                "fn": sync_hashnode_posts.delay,
                "description": "Trigger a Hashnode sync task",
                "input_model": None,
            },
        }

    def get_commands(self):
        return self.commands

# Initialization - typically in app factory or startup script
# from tasks.scheduled_tasks import sync_hashnode_posts
# sync_hashnode_posts.delay()  # Optional: trigger on startup for warmup

# Start workers:
# celery -A tasks.celery_app.celery_app worker --loglevel=info
# celery -A tasks.celery_app.celery_app beat --loglevel=info
from datetime import datetime

from src.controllers.controller import Controllers, error_handler
from src.logger import init_logger
from src.database.sql.blog_learning import BlogFeedback, BlogPrompt
from src.database.models.feedback_analysis import BlogFeedbackInput, BlogFeedbackOutput


class BlogWorkFlowController(Controllers):
    """sumary_line
    
    Keyword arguments:
    argument -- description
    Return: return_description
    """

    def __init__(self, factory):
        super().__init__(factory)
        # Job search specific initialization
        # self.cache = CacheManager()

    def init_app(self, app):
        super().init_app(app)
        # App-specific initialization
        # self.cache.init_app(app)
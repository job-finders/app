from datetime import datetime

from flask import Flask

from src.controllers.controller import Controllers, error_handler
from src.logger import init_logger
from src.database import PerformanceORM

class BlogFeedbackController(Controllers):
    """
    Controller that **copies** Hashnode analytics into a local
    PerformanceORM row and optionally computes a feedback score.
    """

    def __init__(self, factory):
        super().__init__(factory)
        self.logger = init_logger("BlogFeedbackController")

    def init_app(self, app: Flask):
        super().init_app(app=app)
        if self.logger:
            self.logger.info("Initialized Feedback Controller")

    # ---------- helpers ----------
    @staticmethod
    def calculate_feedback_score(perf: PerformanceORM) -> float:
        """
        Simple composite: (reactions * 2 + comments * 3) / max(views, 1)
        """
        return round((perf.reactions * 2 + perf.comments * 3) / max(perf.views, 1), 4)

    # ---------- main entry ----------
    @error_handler
    async def ingest_performance(
            self, performance_data: dict
    ) -> str:  # returns record id
        """
        Store analytics pulled from Hashnode into PerformanceORM.

        `performance_data` = {
            "article_id": "...",
            "views": 123,
            "read_time": 2.3,
            "reactions": 45,
            "comments": 12,
            "shares": 7,
            "collected_at": "2024-07-25T14:00:00Z"
        }
        """
        with self.get_session() as session:
            record = PerformanceORM(
                article_id=performance_data["article_id"],
                views=performance_data.get("views", 0),
                read_time=performance_data.get("read_time", 0.0),
                reactions=performance_data.get("reactions", 0),
                comments=performance_data.get("comments", 0),
                shares=performance_data.get("shares", 0),
                collected_at=datetime.fromisoformat(performance_data["collected_at"]),
            )
            record.feedback_score = self.calculate_feedback_score(record)
            session.add(record)
            session.flush()
            return record.id

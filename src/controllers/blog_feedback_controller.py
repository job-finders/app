from datetime import datetime

from src.controllers.controller import Controllers, error_handler
from src.logger import init_logger
from src.database.sql.blog_learning import BlogFeedback, BlogPrompt
from src.database.models.feedback_analysis import BlogFeedbackInput, BlogFeedbackOutput


class BlogFeedbackController(Controllers):
    def __init__(self):
        super().__init__()
        self.logger = init_logger("BlogFeedbackController")

    @staticmethod
    def calculate_feedback_score(views: int, likes: int, comments: int) -> float:
        if views == 0:
            return 0.0
        return round((likes * 2 + comments * 3) / views, 4)

    @error_handler
    async def submit_feedback(self, feedback_in: BlogFeedbackInput) -> BlogFeedbackOutput:
        with self.get_session() as session:
            feedback = session.query(BlogFeedback).filter(
                BlogFeedback.prompt_id == feedback_in.prompt_id
            ).first()

            if feedback is None:
                feedback = BlogFeedback(
                    prompt_id=feedback_in.prompt_id,
                    views=feedback_in.views,
                    likes=feedback_in.likes,
                    comments=feedback_in.comments,
                    submitted_at=datetime.utcnow()
                )
                session.add(feedback)
            else:
                feedback.views = feedback_in.views
                feedback.likes = feedback_in.likes
                feedback.comments = feedback_in.comments
                feedback.submitted_at = datetime.utcnow()

            feedback.feedback_score = self.calculate_feedback_score(
                feedback.views, feedback.likes, feedback.comments
            )

            prompt = session.query(BlogPrompt).filter(BlogPrompt.id == feedback_in.prompt_id).first()
            if prompt:
                prompt.feedback_score = feedback.feedback_score

            session.commit()

            return BlogFeedbackOutput(
                prompt_id=feedback.prompt_id,
                feedback_score=feedback.feedback_score,
                views=feedback.views,
                likes=feedback.likes,
                comments=feedback.comments,
                submitted_at=feedback.submitted_at.isoformat()
            )

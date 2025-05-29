from datetime import datetime

from src.controllers.controller import Controllers, error_handler
from src.logger import init_logger
from src.database.sql.blog_learning import BlogFeedback, BlogPrompt
from src.database.models.feedback_analysis import BlogFeedbackInput, BlogFeedbackOutput


class BlogFeedbackController(Controllers):
    """
    Controller for handling user interaction feedback (views, likes, comments) on blog prompts.
    Responsible for calculating feedback scores and updating both feedback and prompt records.
    """

    def __init__(self):
        super().__init__()
        self.logger = init_logger("BlogFeedbackController")

    @staticmethod
    def calculate_feedback_score(views: int, likes: int, comments: int) -> float:
        """
        Calculate a feedback score based on the number of views, likes, and comments.

        The formula used is: (likes * 2 + comments * 3) / views

        Args:
            views (int): Number of views.
            likes (int): Number of likes.
            comments (int): Number of comments.

        Returns:
            float: A normalized feedback score, rounded to 4 decimal places.
        """
        if views == 0:
            return 0.0
        return round((likes * 2 + comments * 3) / views, 4)

    @error_handler
    async def submit_feedback(self, feedback_in: BlogFeedbackInput) -> BlogFeedbackOutput:
        """
        Submit or update feedback for a given blog prompt. If feedback exists, it is updated;
        otherwise, a new record is created. The feedback score is recalculated and synced to the
        related BlogPrompt record.

        Args:
            feedback_in (BlogFeedbackInput): Feedback data including prompt ID, views, likes, and comments.

        Returns:
            BlogFeedbackOutput: The updated feedback data, including the calculated score and timestamp.

        Raises:
            ValueError: If the database operation fails (handled by the @error_handler decorator).
        """
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

            # Update the associated BlogPrompt with the new feedback score
            prompt = session.query(BlogPrompt).filter(BlogPrompt.id == feedback_in.prompt_id).first()
            if prompt:
                prompt.feedback_score = feedback.feedback_score

            # controller will auto commit on exit

            # session.commit()

            return BlogFeedbackOutput(
                prompt_id=feedback.prompt_id,
                feedback_score=feedback.feedback_score,
                views=feedback.views,
                likes=feedback.likes,
                comments=feedback.comments,
                submitted_at=feedback.submitted_at.isoformat()
            )

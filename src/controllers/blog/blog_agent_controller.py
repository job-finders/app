from datetime import datetime, timezone
from typing import List

from src.controllers.controller import Controllers, error_handler
from src.logger import init_logger
from src.database import BlogPromptORM, BlogFeedbackResulORM, BlogTopicORM
from src.database.models import BlogFeedbackInput, BlogFeedbackOutput, BlogTopic

class BlogAgentController(Controllers):
    """
    Controller for managing blog generation agents. Handles creation of blog topics,
    association of prompts with topics, retrieval of prompts, and updating feedback scores
    using logic delegated to the BlogFeedbackController.
    """

    def __init__(self, factory):
        super().__init__(factory)
        self.logger = init_logger("BlogAgentController")

    def init_app(self, app):
        super().init_app(app)
        # App-specific initialization
        # self.cache.init_app(app)

    @error_handler
    async def create_blog_topic(self, topic_in: BlogTopic) -> BlogTopic:
        """
        Create a new blog topic if it does not already exist.

        Args:
            topic_in (BlogTopic): The blog topic data containing the title.

        Returns:
            BlogTopic: The original input object on success.

        Raises:
            ValueError: If a topic with the same title already exists.
        """
        with self.get_session() as session:
            existing = session.query(BlogTopic).filter(BlogTopic.title == topic_in.title).first()
            if existing:
                raise ValueError(f"Blog topic '{topic_in.title}' already exists")

            topic = BlogTopic(title=topic_in.title, created_at=datetime.utcnow())
            session.add(topic)
            self.logger.info(f"Created new blog topic '{topic_in.title}' with id {topic.id}")
            return topic_in

    @error_handler
    async def add_blog_prompt(self, prompt_in: BlogPromptORM) -> BlogPromptORM:
        """
        Add a new blog prompt under a specific topic.

        Args:
            prompt_in (BlogPromptORM): The prompt data including content and topic_id.

        Returns:
            BlogPromptORM: The original input object on success.

        Raises:
            ValueError: If the specified topic does not exist.
        """
        with self.get_session() as session:
            topic = session.query(BlogTopicORM).filter(BlogTopic.topic_id == prompt_in.topic_id).first()
            if not topic:
                raise ValueError(f"Blog topic id {prompt_in.topic_id} not found")

            prompt = BlogPromptORM(
                content=prompt_in.content,
                topic_id=prompt_in.topic_id,
                created_at=datetime.now(timezone.utc),
                feedback_score=0.0,
            )
            session.add(prompt)
            self.logger.info(f"Added prompt to topic {prompt_in.topic_id} with prompt id {prompt.id}")
            return prompt_in

    @error_handler
    async def get_prompts_for_topic(self, topic_id: int) -> List[BlogPromptORM]:
        """
        Retrieve all prompts associated with a given topic.

        Args:
            topic_id (int): The ID of the blog topic.

        Returns:
            List[BlogPromptORM]: A list of prompts under the specified topic.
        """
        with self.get_session() as session:
            prompts = session.query(BlogPromptORM).filter(BlogPromptORM.topic_id == topic_id).all()
            return [BlogPromptORM(id=p.id, content=p.content, topic_id=p.topic_id) for p in prompts]

    @error_handler
    async def update_feedback_score(self, feedback_in: BlogFeedbackInput) -> BlogFeedbackOutput:
        """
        Update the feedback score for a specific blog prompt using
        the BlogFeedbackController's logic.

        Args:
            feedback_in (BlogFeedbackInput): Feedback data including views, likes, comments, and prompt_id.

        Returns:
            BlogFeedbackOutput: The updated feedback output including calculated score.
        """
        from src.controllers.blog.blog_feedback_controller import BlogFeedbackController
        feedback_controller = BlogFeedbackController()
        return await feedback_controller.submit_feedback(feedback_in)

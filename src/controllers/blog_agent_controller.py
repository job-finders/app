from datetime import datetime
from typing import List, Optional

from src.controllers.controller import Controllers, error_handler
from src.logger import init_logger
from src.database.sql.blog_learning import BlogTopic, BlogPrompt, BlogFeedback
from src.database.models.feedback_analysis import  BlogFeedbackInput, BlogFeedbackOutput

class BlogAgentController(Controllers):
    def __init__(self):
        super().__init__()
        self.logger = init_logger("BlogAgentController")

    @error_handler
    async def create_blog_topic(self, topic_in: BlogTopic) -> BlogTopic:
        with self.get_session() as session:
            existing = session.query(BlogTopic).filter(BlogTopic.title == topic_in.title).first()
            if existing:
                raise ValueError(f"Blog topic '{topic_in.title}' already exists")

            topic = BlogTopic(title=topic_in.title, created_at=datetime.utcnow())
            session.add(topic)
            session.commit()
            self.logger.info(f"Created new blog topic '{topic_in.title}' with id {topic.id}")
            return topic_in

    @error_handler
    async def add_blog_prompt(self, prompt_in: BlogPrompt) -> BlogPrompt:
        with self.get_session() as session:
            topic = session.query(BlogTopic).filter(BlogTopic.id == prompt_in.topic_id).first()
            if not topic:
                raise ValueError(f"Blog topic id {prompt_in.topic_id} not found")

            prompt = BlogPrompt(
                content=prompt_in.content,
                topic_id=prompt_in.topic_id,
                created_at=datetime.utcnow(),
                feedback_score=0.0,
            )
            session.add(prompt)
            session.commit()
            self.logger.info(f"Added prompt to topic {prompt_in.topic_id} with prompt id {prompt.id}")
            return prompt_in

    @error_handler
    async def get_prompts_for_topic(self, topic_id: int) -> List[BlogPrompt]:
        with self.get_session() as session:
            prompts = session.query(BlogPrompt).filter(BlogPrompt.topic_id == topic_id).all()
            return [BlogPrompt(id=p.id, content=p.content, topic_id=p.topic_id) for p in prompts]

    @error_handler
    async def update_feedback_score(self, feedback_in: BlogFeedbackInput) -> BlogFeedbackOutput:
        # This method could reuse the logic from BlogFeedbackController or call it internally
        from src.controllers.blog_feedback_controller import BlogFeedbackController
        feedback_controller = BlogFeedbackController()
        return await feedback_controller.submit_feedback(feedback_in)

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from src.database.constants import ID_LEN
from src.database.constants import utc_time
from src.database.sql import Base


class BlogTopicORM(Base):
    """this ORM MOdels are for generating blog topics and prompts for the blog learning module"""
    __tablename__ = "blog_topics"

    blog_topic_id = Column(String(ID_LEN), primary_key=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_time)
    prompts = relationship("BlogPromptORM", back_populates="topic")

class BlogPromptORM(Base):
    __tablename__ = "blog_prompts"

    blog_prompt_id = Column(String(ID_LEN), primary_key=True)
    content = Column(Text, nullable=False)
    topic_id = Column(String(ID_LEN), ForeignKey("blog_topics.blog_topic_id"))
    created_at = Column(DateTime(timezone=True), default=utc_time)
    feedback_score = Column(Float, default=0.0)
    topic = relationship("BlogTopicORM", back_populates="prompts")


class BlogFeedbackResulORM(Base):
    __tablename__ = "blog_feedback_results"

    blog_feedback_id = Column(String(ID_LEN), primary_key=True)
    prompt_id = Column(String(ID_LEN), ForeignKey("blog_prompts.blog_prompt_id"))
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    feedback_score = Column(Float)
    submitted_at = Column(DateTime(timezone=True), default=utc_time)
    prompt = relationship("BlogPromptORM")

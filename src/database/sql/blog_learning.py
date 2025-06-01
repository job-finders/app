import datetime

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from src.database.sql import Base


class BlogTopic(Base):
    __tablename__ = "blog_topics"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    prompts = relationship("BlogPrompt", back_populates="topic")

class BlogPrompt(Base):
    __tablename__ = "blog_prompts"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    topic_id = Column(Integer, ForeignKey("blog_topics.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    feedback_score = Column(Float, default=0.0)
    topic = relationship("BlogTopic", back_populates="prompts")

class BlogFeedback(Base):
    __tablename__ = "blog_feedback"

    id = Column(Integer, primary_key=True)
    prompt_id = Column(Integer, ForeignKey("blog_prompts.id"))
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    feedback_score = Column(Float)
    submitted_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)

    prompt = relationship("BlogPrompt")

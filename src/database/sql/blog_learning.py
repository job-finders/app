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


class TopicORM(Base):
    __tablename__ = "topics"
    id          = Column(Integer, primary_key=True)
    title       = Column(String, unique=True)
    keywords    = Column(JSON)          # list[str]
    created_at  = Column(DateTime, default=datetime.utcnow)

class ArticleORM(Base):
    __tablename__ = "articles"
    id          = Column(Integer, primary_key=True)
    topic_id    = Column(Integer, ForeignKey("topics.id"))
    title       = Column(String)
    markdown    = Column(Text)
    draft_hashnode_id = Column(String, nullable=True)  # created but not yet scheduled
    created_at  = Column(DateTime, default=datetime.utcnow)

class ScheduledPostORM(Base):
    __tablename__ = "scheduled_posts"
    id          = Column(Integer, primary_key=True)
    article_id  = Column(Integer, ForeignKey("articles.id"))
    scheduled_at = Column(DateTime, index=True)
    hashnode_post_id = Column(String, nullable=True)  # after creation
    status      = Column(String, default="pending")   # pending | live
    created_at  = Column(DateTime, default=datetime.utcnow)

class PerformanceORM(Base):
    __tablename__ = "performance"
    id          = Column(Integer, primary_key=True)
    article_id  = Column(Integer, ForeignKey("articles.id"))
    views       = Column(Integer, default=0)
    reactions   = Column(Integer, default=0)
    read_time   = Column(Float, default=0.0)
    collected_at = Column(DateTime, default=datetime.utcnow)


class PromptORM(Base):
    __tablename__ = "prompts"

    id              = Column(Integer, primary_key=True)
    agent_name      = Column(String(64), nullable=False, index=True)
    version         = Column(Integer, nullable=False, default=1)
    system_prompt   = Column(Text, nullable=False)   # full system prompt text
    prompt          = Column(Text, nullable=False)   # full user prompt text (Jinja2)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)


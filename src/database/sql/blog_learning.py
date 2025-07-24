from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from src.database.constants import ID_LEN, utc_time, NAME_LEN
from src.database.sql import Base


# ---------- Blog Topics ----------
class BlogTopicORM(Base):
    __tablename__ = "blog_topics"
    id = Column(String(ID_LEN), primary_key=True)
    title = Column(String(255), nullable=False)
    keywords = Column(JSON, default=list)  # list[str]
    created_at = Column(DateTime(timezone=True), default=utc_time)

    prompts = relationship("BlogPromptORM", back_populates="topic")
    articles = relationship("ArticleORM", back_populates="topic")


# ---------- Prompts (used by any agent) ----------
class PromptORM(Base):
    __tablename__ = "prompts"
    id = Column(Integer, primary_key=True)
    agent_name = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    system_prompt = Column(Text, nullable=False)
    prompt = Column(Text, nullable=False)  # user prompt (Jinja2)
    created_at = Column(DateTime(timezone=True), default=utc_time)


# ---------- Prompt Mutation Log ----------
class PromptMutationLogORM(Base):
    __tablename__ = "prompt_mutation_log"
    id = Column(Integer, primary_key=True)
    agent_name = Column(String(64), nullable=False, index=True)
    old_prompt_id = Column(Integer, ForeignKey("prompts.id"))
    new_prompt_id = Column(Integer, ForeignKey("prompts.id"))
    mutation_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utc_time)


# ---------- Articles ----------
class ArticleORM(Base):
    __tablename__ = "articles"
    id = Column(String(ID_LEN), primary_key=True)
    topic_id = Column(String(ID_LEN), ForeignKey("blog_topics.id"))
    title = Column(String, nullable=False)
    markdown = Column(Text, nullable=False)
    draft_hashnode_id = Column(String(ID_LEN), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_time)

    topic = relationship("BlogTopicORM", back_populates="articles")
    scheduled_posts = relationship("ScheduledPostORM", back_populates="article")
    performance = relationship("PerformanceORM", back_populates="article")


# ---------- Scheduled Posts (Hashnode scheduling) ----------
class ScheduledPostORM(Base):
    __tablename__ = "scheduled_posts"
    id = Column(String(ID_LEN), primary_key=True)
    article_id = Column(String(ID_LEN), ForeignKey("articles.id"))
    scheduled_at = Column(DateTime(timezone=True), index=True)
    hashnode_post_id = Column(String(ID_LEN), nullable=True)
    status = Column(String(16), default="pending")  # pending | live
    created_at = Column(DateTime(timezone=True), default=utc_time)

    article = relationship("ArticleORM", back_populates="scheduled_posts")


# ---------- Detailed Performance ----------
class PerformanceORM(Base):
    __tablename__ = "performance"
    id = Column(String(ID_LEN), primary_key=True)
    article_id = Column(String(ID_LEN), ForeignKey("articles.id"))
    views = Column(Integer, default=0)
    read_time = Column(Float, default=0.0)
    reactions = Column(Integer, default=0)
    comments = Column(Integer, default=0)  # ← integer, not JSON
    shares = Column(Integer, default=0)
    collected_at = Column(DateTime(timezone=True), default=utc_time)

    article = relationship("ArticleORM", back_populates="performance")


# ---------- Legacy Prompts (keep for backward-compatibility) ----------
class BlogPromptORM(Base):
    __tablename__ = "blog_prompts"
    id = Column(String(ID_LEN), primary_key=True)
    topic_id = Column(String(ID_LEN), ForeignKey("blog_topics.id"))
    agent_name = Column(String(NAME_LEN), index=True)
    version = Column(Integer, index=True)
    system_prompt = Column(Text, nullable=False)
    prompt = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_time)
    feedback_score = Column(Float, default=0.0)
    topic = relationship("BlogTopicORM", back_populates="prompts")

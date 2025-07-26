from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, JSON, inspect
from sqlalchemy.orm import relationship
from src.database.constants import ID_LEN, utc_time, NAME_LEN
from src.database.sql import Base, engine


# ---------- Blog Topics ----------
class BlogTopicORM(Base):
    __tablename__ = "blog_topics"
    id = Column(String(ID_LEN), primary_key=True)
    title = Column(String(NAME_LEN), nullable=False)
    keywords = Column(JSON, default=list)  # list[str]
    created_at = Column(DateTime(timezone=True), default=utc_time)

    prompts = relationship("BlogPromptORM", back_populates="topic")
    articles = relationship("ArticleORM", back_populates="topic")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)


# ---------- Prompt Mutation Log ----------
class PromptMutationLogORM(Base):
    __tablename__ = "prompt_mutation_log"
    id = Column(String(ID_LEN), primary_key=True)
    agent_name = Column(String(64), nullable=False, index=True)
    old_prompt_id = Column(String(ID_LEN), ForeignKey("blog_prompts.id"))
    new_prompt_id = Column(String(ID_LEN), ForeignKey("blog_prompts.id"))
    mutation_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utc_time)

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

# ---------- Articles ----------
class ArticleORM(Base):
    __tablename__ = "articles"
    id = Column(String(ID_LEN), primary_key=True)
    topic_id = Column(String(ID_LEN), ForeignKey("blog_topics.id"))
    title = Column(String(NAME_LEN), nullable=False)
    markdown = Column(Text, nullable=False)
    draft_hashnode_id = Column(String(ID_LEN), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_time)

    topic = relationship("BlogTopicORM", back_populates="articles")
    scheduled_posts = relationship("ScheduledPostORM", back_populates="article")
    performance = relationship("PerformanceORM", back_populates="article")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

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

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

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

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

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

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

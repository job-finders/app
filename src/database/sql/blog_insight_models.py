# /models/blog_insight_models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, func

from src.database.constants import ID_LEN
from src.database.sql import Base

class BlogFeedbackORM(Base):
    __tablename__ = "blog_feedback"

    blog_feedback_id = Column(String(ID_LEN), primary_key=True)
    article_id = Column(String(ID_LEN), nullable=False)
    feedback_score = Column(Integer, nullable=False)
    comments = Column(Text)
    submitted_at = Column(DateTime, server_default=func.now())


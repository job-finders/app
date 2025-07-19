# /schemas/feedback_analysis.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ArticleFeedbackEntry(BaseModel):
    article_id: str
    feedback_score: int
    comments: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class FeedbackAnalysisSummary(BaseModel):
    high_performing_topics: List[str]
    underperforming_topics: List[str]
    average_score: float
    insights: List[str]
    new_prompt_ideas: List[str]
    model_config = ConfigDict(from_attributes=True)



class BlogFeedbackInput(BaseModel):
    prompt_id: int
    views: int = 0
    likes: int = 0
    comments: int = 0
    model_config = ConfigDict(from_attributes=True)

class BlogFeedbackOutput(BaseModel):
    prompt_id: int
    feedback_score: float
    views: int
    likes: int
    comments: int
    submitted_at: str
    model_config = ConfigDict(from_attributes=True)


class BlogPrompt(BaseModel):
    blog_prompt_id: str
    content: str
    topic_id: str
    created_at: datetime
    feedback_score: int
    topic: Optional['BlogTopic']


class BlogTopic(BaseModel):
    blog_topic_id: str
    title: str
    created_at: datetime
    prompts: list[BlogPrompt]
    description: str

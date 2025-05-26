# /schemas/feedback_analysis.py
from pydantic import BaseModel
from typing import List, Optional

class ArticleFeedbackEntry(BaseModel):
    article_id: str
    feedback_score: int
    comments: Optional[str] = None

class FeedbackAnalysisSummary(BaseModel):
    high_performing_topics: List[str]
    underperforming_topics: List[str]
    average_score: float
    insights: List[str]
    new_prompt_ideas: List[str]



class BlogFeedbackInput(BaseModel):
    prompt_id: int
    views: int = 0
    likes: int = 0
    comments: int = 0

class BlogFeedbackOutput(BaseModel):
    prompt_id: int
    feedback_score: float
    views: int
    likes: int
    comments: int
    submitted_at: str

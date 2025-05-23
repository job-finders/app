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

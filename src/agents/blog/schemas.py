from pydantic import BaseModel, Field


class Topic(BaseModel):
    id: str = Field(..., description="unique slug")
    section: str
    title: str
    keywords: list[str]
    search_volume: int
    competition: float


#--------------------------------------------------
#------------ Article Outline Schema ------------


class ArticleOutline(BaseModel):
    slug: str
    topic_id: str
    headline: str
    subheadings: list[str]
    target_keywords: list[str]
    estimated_reading_time: int



#--------------------------------------------------
#------------ Performance Monitoring ------------
#--------------------------------------------------

class PerformanceMetrics(BaseModel):
    slug: str
    views: int
    avg_read_time: float
    shares: int
    backlinks: int
    ctr: float

#--------------------------------------------------
#------------ Refinement Instructions ------------
#--------------------------------------------------

class RefinementInstructions(BaseModel):
    slug: str
    action: str               # "rewrite_outline" | "drop_topic" | "expand_keywords"
    new_outline: ArticleOutline | None = None
    reason: str

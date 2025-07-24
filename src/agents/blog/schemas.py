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

    
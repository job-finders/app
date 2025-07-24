from pydantic import BaseModel, Field


class Topic(BaseModel):
    id: str = Field(..., description="unique slug")
    section: str
    title: str
    keywords: list[str]
    search_volume: int
    competition: float
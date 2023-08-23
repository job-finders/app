from pydantic import BaseModel


class SEO(BaseModel):
    title: str
    description: str
    keywords: str

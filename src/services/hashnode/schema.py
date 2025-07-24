

from pydantic import BaseModel, Field



# ------------------------------------------------------------------
# Pydantic models (inputs & outputs)
# ------------------------------------------------------------------
class CreatePostInput(BaseModel):
    publication_id: str
    title: str
    content_markdown: str
    slug: Optional[str] = None
    is_draft: bool = True
    cover_image_url: Optional[str] = None   # header image
    social_image_url: Optional[str] = None  # OG/Twitter card


class UpdatePostInput(BaseModel):
    post_id: str
    title: str
    content_markdown: str
    cover_image_url: Optional[str] = None
    social_image_url: Optional[str] = None


class DeletePostInput(BaseModel):
    post_id: str


class SchedulePostInput(BaseModel):
    post_id: str
    scheduled_at: datetime


class AddTagsInput(BaseModel):
    post_id: str
    tags: List[str]


class CreateSeriesInput(BaseModel):
    name: str
    description: str
    cover_image_url: Optional[str] = None


class AddPostToSeriesInput(BaseModel):
    post_id: str
    series_slug: str


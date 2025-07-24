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

#--------------------------------------------------
#------------ Article Markdown Schema ------------
#--------------------------------------------------

class ArticleMarkdown(BaseModel):
    slug: str
    title: str
    markdown: str
    estimated_reading_time: int = Field(ge=1)

#--------------------------------------------------
#------------ SEO Score Report Schema ------------
#--------------------------------------------------


class SEOScoreReport(BaseModel):
    slug: str
    overall_score: float = Field(ge=0.0, le=1.0)
    keyword_density: dict[str, float]
    meta_title_length: int
    meta_description_length: int
    h1_h2_h3_counts: dict[str, int]
    internal_link_suggestions: list[str]
    image_alt_missing: int
    readability_score: float

#--------------------------------------------------
#------------ Publish Decision Schema ------------
#--------------------------------------------------


class PublishDecision(BaseModel):
    slug: str
    action: str  # "publish", "revise", "hold"
    reasoning: str


#--------------------------------------------------
#------------ Social Copy Set Schema ------------
#--------------------------------------------------

class SocialCopySet(BaseModel):
    slug: str
    twitter: str = Field(max_length=280)
    linkedin: str = Field(max_length=3000)
    hashtags: list[str]

#--------------------------------------------------
#------------ AB Testing Variants Schema ------------
#--------------------------------------------------

class ABVariants(BaseModel):
    slug: str
    variants: list[str] = Field(min_items=2, max_items=5)

#--------------------------------------------------
#------------ Archive Actions Schema ------------
#--------------------------------------------------


class ArchiveActions(BaseModel):
    slugs: list[str]
    action: str  # "repurpose", "update", "merge", "delete"
    justification: str
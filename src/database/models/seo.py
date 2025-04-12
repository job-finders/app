from pydantic import BaseModel

from src.database.models import Job
from src.utils import format_title


class SEO(BaseModel):
    title: str
    description: str
    keywords: str
    og_title: str | None = None
    og_description: str | None = None
    twitter_title: str | None = None
    twitter_description: str | None = None


async def create_tags(search_term: str) -> SEO:
    """

    :param search_term:
    :return:
    """

    title = f"{search_term} Jobs" if "jobs" not in search_term else search_term
    description = f"jobfinders.site {title}"
    term_words = ",".join(format_title(search_term).split(" "))
    keywords = f"JobFinders, {term_words}"
    seo_dict = dict(title=title, description=description, keywords=keywords)
    return SEO(**seo_dict)


async def create_seo_tags_for_job(job: Job) -> SEO:
    """
    Generate SEO tags from a Job object.
    """
    # Generate a keyword list using job title, company, location, and search term
    keyword_base = f"{job.title}, {job.company_name}, {job.location}, {job.search_term}"
    keywords = ", ".join(sorted(set(keyword_base.lower().replace(",", "").split())))

    # Construct the main SEO title and description
    title = f"{job.title} at {job.company_name} in {job.location} | JobFinders"
    description = (
        f"Apply now for the position of {job.title} at {job.company_name} "
        f"in {job.location}. Updated {job.updated_time}. "
        f"Find more jobs like this on JobFinders."
    )

    # Social-friendly, shorter metadata
    og_title = f"{job.title} - {job.company_name} | JobFinders"
    og_description = f"{job.title} available at {job.company_name} in {job.location}. Apply today!"

    # Twitter can reuse OG tags
    twitter_title = og_title
    twitter_description = og_description

    return SEO(
        title=title,
        description=description,
        keywords=keywords,
        og_title=og_title,
        og_description=og_description,
        twitter_title=twitter_title,
        twitter_description=twitter_description
    )


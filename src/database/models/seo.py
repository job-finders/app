from pydantic import BaseModel

from src.utils import format_title


class SEO(BaseModel):
    title: str
    description: str
    keywords: str


async def create_tags(search_term: str) -> SEO:
    """

    :param search_term:
    :return:
    """
    title = f"{search_term} Jobs"
    description = f"jobfinders.site {search_term} Jobs"
    term_words = ",".join(format_title(search_term).split(" "))
    keywords = f"JobFinders, {term_words}"
    seo_dict = dict(title=title, description=description, keywords=keywords)
    return SEO(**seo_dict)

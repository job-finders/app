from typing import List
from src.models.job import Job
from src.database.models.company_ats import KeywordSource

from .corpora import (
    industry_taxonomy_extract,
    peer_jobs_extract,
    parsed_cvs_extract,
)


def build_keyword_intelligence(job: Job) -> List[KeywordSource]:
    """
    Aggregate keyword intelligence from all available corpora for a given job.
    """
    sources: List[KeywordSource] = []
    sources.extend(industry_taxonomy_extract(job))
    sources.extend(peer_jobs_extract(job))
    sources.extend(parsed_cvs_extract(job))
    return sources
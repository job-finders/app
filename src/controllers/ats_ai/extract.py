from typing import List
from .corpora import industry_taxonomy, peer_jobs, parsed_cvs
from .models import KeywordSource


def build_keyword_intelligence(job: Job) -> List[KeywordSource]:
    """
    Returns a unified list of KeywordSource objects for a given Job.
    """
    sources = []
    sources.extend(industry_taxonomy.extract(job))
    sources.extend(peer_jobs.extract(job))
    sources.extend(parsed_cvs.extract(job))
    return sources

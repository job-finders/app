from typing import List
from src.models.job import Job
from src.database.models.company_ats import KeywordSource

def extract(job: Job) -> List[KeywordSource]:
    """
    Mine keywords from similar live job postings (DB or external API).
    """
    # stub
    peer_keywords = {
        "fastapi": 70,
        "docker": 85,
        "kubernetes": 60,
    }
    return [
        KeywordSource(
            keyword=kw,
            frequency=freq,
            source_type="peer_jobs",
            weight=0.75,
        )
        for kw, freq in peer_keywords.items()
    ]
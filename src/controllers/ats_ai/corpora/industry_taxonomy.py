from typing import List
from src.models.job import Job
from src.database.models.company_ats import KeywordSource

def extract(job: Job) -> List[KeywordSource]:
    """
    Return high-value keywords from O*NET / ESCO / internal taxonomy.
    Stub implementation – swap for a service call or DB query.
    """
    # Example: derive taxonomy keywords from job title + skills
    taxonomy_keywords = {
        "python": 120,
        "django": 110,
        "postgresql": 95,
        "rest api": 90,
    }

    return [
        KeywordSource(
            keyword=kw,
            frequency=freq,
            source_type="industry_taxonomy",
            weight=0.9,
        )
        for kw, freq in taxonomy_keywords.items()
    ]
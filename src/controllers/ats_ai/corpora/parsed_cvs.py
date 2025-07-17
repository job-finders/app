from typing import List
from src.models.job import Job
from src.database.models.company_ats import KeywordSource

def extract(job: Job) -> List[KeywordSource]:
    """
    Derive keywords from anonymised CVs that successfully matched similar roles.
    """
    # stub
    cv_keywords = {
        "aws": 50,
        "ci/cd": 40,
        "redis": 35,
    }
    return [
        KeywordSource(
            keyword=kw,
            frequency=freq,
            source_type="parsed_cvs",
            weight=0.7,
        )
        for kw, freq in cv_keywords.items()
    ]
    
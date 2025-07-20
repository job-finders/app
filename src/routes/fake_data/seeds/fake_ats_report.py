import uuid
import random
from src.database.models import ATSReport  # Adjust the import path as needed


def generate_fake_ats_report(job_id: str, cv_id: str = None) -> ATSReport:
    """Create a fake ATS report for testing."""
    cv_id = cv_id or f"fake-cv-{uuid.uuid4()}"
    score = round(random.uniform(40.0, 95.0), 2)
    matched_keywords = random.sample(["react", "django", "sql", "aws", "docker", "rest"], k=random.randint(1, 4))
    # noinspection PySetFunctionToLiteral
    missing_keywords = list(set(["kubernetes", "flask", "typescript", "microservices"]) - set(matched_keywords))

    return ATSReport(
        job_id=job_id,
        cv_id=cv_id,
        score=score,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        feedback="Great keyword match, but a few key terms are missing."
    )

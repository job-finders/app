import uuid
import random
from datetime import timedelta

from src.database.constants import utc_time
from src.database.models import JobApplication, JobApplicationStatusEnum

from .fake_ats_report import generate_fake_ats_report
from .fake_resume import generate_fake_cv


def generate_fake_job_application(job_id: str, user_id: str = None, stage: str = None) -> JobApplication:
    """
    Generate a fake JobApplication with a realistic CV and an ATS Report.
    """
    user_id = user_id or f"test-user-{str(uuid.uuid4())[:8]}"

    # Generate a fake CV and get its ID
    fake_cv = generate_fake_cv(user_uid=user_id)
    cv_id = fake_cv.cv_id

    # Generate ATS Report for that CV
    ats_report = generate_fake_ats_report(job_id=job_id, cv_id=cv_id)

    # Calculate applied date
    applied_days_ago = random.randint(1, 10)
    application_stage = stage or random.choice(list(JobApplicationStatusEnum.__members__.values())).value

    return JobApplication(
        application_id=str(uuid.uuid4()),
        user_id=user_id,
        job_id=job_id,
        cv_id=cv_id,
        ats_report_id=ats_report.ats_report_id,
        ats_report=ats_report,
        applied_date=utc_time() - timedelta(days=applied_days_ago),
        updated_at=utc_time(),
        application_stage=application_stage,
        expected_salary=random.randint(60000, 120000),
        preferred_location=random.choice(["Remote", "New York", "Berlin", "Toronto", None]),
        required_documents=random.sample(["resume", "cover_letter", "portfolio"], k=random.randint(1, 2)),
        questionnaire_answers={
            "q1": [random.choice(["Yes", "No"])],
            "q2": [random.choice(["Yes", "No"])]
        },
        validation_score=random.randint(40, 100),
        review_summary=random.choice([
            "Excellent React developer",
            "Strong backend profile",
            "Junior-level candidate",
            "Limited experience but promising"
        ]),
        cover_letter=random.choice([
            "I'm very interested in this opportunity.",
            "Excited to contribute to your team!",
            None
        ])
    )

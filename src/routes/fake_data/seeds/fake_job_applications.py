from src.database.constants import utc_time
from src.database.models import JobApplication, JobApplicationStatusEnum
import uuid
import random
from datetime import timedelta

def generate_fake_job_application(job_id: str, user_id: str = None, stage: str = None) -> JobApplication:
    """
    Generate a fake JobApplication with a realistic CV and an ATS Report.
    If no user_id is provided, a new JobSeekerProfile will be created.
    """
    from .fake_jobseeker_profile import generate_fake_jobseeker_profile
    from .fake_resume import generate_fake_cv
    from .fake_ats_report import generate_fake_ats_report

    profile = None
    fake_cv = None

    # Create or load a fake JobSeekerProfile
    if not user_id:
        profile = generate_fake_jobseeker_profile()
        user_id = profile.user_uid
    else:
        # If a user_id is provided but no profile, you might want to retrieve one here in real scenarios.
        profile = None  # Placeholder — fetch logic if needed

    # Generate or reuse a fake CV
    if not profile or not profile.resumes_list:
        fake_cv = generate_fake_cv(user_uid=user_id)
    else:
        fake_cv = profile.resumes_list[-1]

    cv_id = fake_cv.cv_id

    # Generate ATS Report for the selected CV
    ats_report = generate_fake_ats_report(job_id=job_id, cv_id=cv_id)

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
        ]),
        jobseeker_profile=profile  # ✅ Include the full profile
    )

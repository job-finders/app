# src/controllers/fake_data/seeds.py

import uuid
from datetime import datetime
from src.database.models import Job, Company, JobSeekerCV, ATSReport, JobApplication, JobSeekerProfile
from src.routes.fake_data import store


def generate_fake_application_pipeline(job_id: str = None):
    company_id = str(uuid.uuid4())
    job_id = job_id or str(uuid.uuid4())
    user_uid = str(uuid.uuid4())
    cv_id = str(uuid.uuid4())
    ats_id = str(uuid.uuid4())
    application_id = str(uuid.uuid4())

    company = Company(company_id=company_id, name="FakeCorp")
    job = Job(job_id=job_id, company_id=company_id, title="Software Engineer", location="Remote")
    profile = JobSeekerProfile(user_uid=user_uid, full_names="Jane Doe", email="jane@example.com")
    resume = JobSeekerCV(cv_id=cv_id, user_uid=user_uid, content="Fake CV content for Jane.")
    ats = ATSReport(ats_report_id=ats_id, score=88, keywords_matched=14, missing_keywords=3,
                    summary="Good match overall.")
    application = JobApplication(
        application_id=application_id,
        job_id=job_id,
        user_id=user_uid,
        cv_id=cv_id,
        ats_report=ats,
        jobseeker_profile=profile,
        cover_letter="Dear team, I’m thrilled to apply...",
        application_stage="interview",
        applied_date=datetime.utcnow()
    )

    # Store in-memory
    store.companies[company_id] = company
    store.jobs[job_id] = job
    store.jobseekers[user_uid] = profile
    store.resumes[cv_id] = resume
    store.ats_reports[ats_id] = ats
    store.job_applications[application_id] = application

    return application

# tests/factories.py

import uuid
from datetime import datetime, timedelta

from src.database import JobsORM, JobCategoryORM
from src.database.models.jobs_model import JobStatusEnum


def create_category(session, **overrides):
    """
    Creates a JobCategoryORM record with sane defaults.
    Allows override of any field via kwargs.
    """
    category = JobCategoryORM(
        category_id=overrides.get("category_id", str(uuid.uuid4())),
        name=overrides.get("name", "Engineering"),
        slug=overrides.get("slug", "engineering"),
        description=overrides.get("description", "Engineering and technical jobs."),
        seo_description=overrides.get("seo_description", "Find engineering jobs in your area."),
        created_at=overrides.get("created_at", datetime.utcnow()),
        updated_at=overrides.get("updated_at", datetime.utcnow()),
    )

    session.add(category)
    session.commit()
    return category

def create_category_with_jobs(session, num_jobs=3, **cat_kwargs):
    from tests.factories import create_job  # Ensure it's imported
    category = create_category(session, **cat_kwargs)
    
    for _ in range(num_jobs):
        create_job(session, category_id=category.category_id)

    session.refresh(category)  # Make sure relationships are loaded
    return category



def create_job(session, category_id=None, company_id=None, **overrides):
    job = JobsORM(
        job_id=overrides.get("job_id", str(uuid.uuid4())),
        job_ref=overrides.get("job_ref", f"REF-{uuid.uuid4().hex[:8]}"),
        slug=overrides.get("slug", "default-slug"),
        external_source=overrides.get("external_source", "Internal"),

        employer_id=overrides.get("employer_id", None),
        company_id=company_id or overrides.get("company_id", None),
        category_id=category_id or overrides.get("category_id", None),

        title=overrides.get("title", "Software Engineer"),
        description=overrides.get("description", "Develop amazing products."),
        position_type=overrides.get("position_type", "FULL_TIME"),
        remote_policy=overrides.get("remote_policy", "HYBRID"),

        salary_min=overrides.get("salary_min", 50000),
        salary_max=overrides.get("salary_max", 120000),
        salary_currency=overrides.get("salary_currency", "ZAR"),
        salary_confidential=overrides.get("salary_confidential", False),

        city=overrides.get("city", "Cape Town"),
        province=overrides.get("province", "Western Cape"),
        country=overrides.get("country", "South Africa"),
        geo_location=overrides.get("geo_location", "-33.9249,18.4241"),

        posted_at=overrides.get("posted_at", datetime.utcnow()),
        expires_at=overrides.get("expires_at", datetime.utcnow() + timedelta(days=30)),
        application_deadline=overrides.get("application_deadline", datetime.utcnow() + timedelta(days=15)),

        experience_level=overrides.get("experience_level", "MID"),
        education_requirements=overrides.get("education_requirements", {"degree": "BSc", "field": "CS"}),
        required_skills=overrides.get("required_skills", ["Python", "Flask"]),
        preferred_skills=overrides.get("preferred_skills", ["Docker", "Postgres"]),

        required_documents=overrides.get("required_documents", []),
        required_questionnaire=overrides.get("required_questionnaire", None),

        application_url=overrides.get("application_url", "https://example.com/apply"),
        application_instructions=overrides.get("application_instructions", "Please attach your resume."),

        view_count=overrides.get("view_count", 0),
        application_count=overrides.get("application_count", 0),

        status=overrides.get("status", JobStatusEnum.ACTIVE.value),
        is_featured=overrides.get("is_featured", False),

        summary=overrides.get("summary", "Quick summary of the job."),
        seo_description=overrides.get("seo_description", "Search engine friendly description."),
    )

    session.add(job)
    session.commit()
    return job

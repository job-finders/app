# tests/factories.py

import uuid
from datetime import datetime, timezone
from datetime import timedelta

from src.database import *
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
        created_at=overrides.get("created_at", datetime.now(timezone.utc)),
        updated_at=overrides.get("updated_at", datetime.now(timezone.utc)),
    )

    session.add(category)
    session.commit()
    return category

def create_category_with_jobs(session, num_jobs=3, **cat_kwargs):
    category = create_category(session, **cat_kwargs)
    for _ in range(num_jobs):
        create_job(session, category_id=category.category_id)

    session.refresh(category)  # Make sure relationships are loaded
    return category



def create_job(session, category_id=None, company_id=None, **overrides):
    job = JobsORM(
        job_id=overrides.get("job_id", str(uuid.uuid4())),
        job_ref=overrides.get("job_ref", f"REF-{uuid.uuid4().hex[:8]}"),
        slug=overrides.get("slug", None),
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

        posted_at=overrides.get("posted_at", datetime.now(timezone.utc)),
        expires_at=overrides.get("expires_at", datetime.now(timezone.utc) + timedelta(days=30)),
        application_deadline=overrides.get("application_deadline", datetime.now(timezone.utc) + timedelta(days=15)),

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


def create_job_version_history(session, **overrides):
    job_version = JobVersionHistoryORM(
        id=overrides.get("id", str(uuid.uuid4())),
        job_id=overrides["job_id"],  # required
        version=overrides.get("version", 1),
        changes=overrides.get("changes", {"field": "title", "old": "Old Title", "new": "New Title"}),
        modified_by=overrides["modified_by"],  # required
        modified_at=overrides.get("modified_at", datetime.utcnow()),
    )
    session.add(job_version)
    session.commit()
    return job_version


def create_saved_job(session, **overrides):
    # Handle job object or job_id
    if "job" in overrides:
        job_id = overrides["job"].job_id
        overrides.pop("job")  # Remove job object from overrides
    else:
        job_id = overrides["job_id"]  # Use provided job_id
    
    saved_job = SavedJobORM(
        saved_job_id=overrides.get("saved_job_id", str(uuid.uuid4())),
        user_id=overrides["user_id"],  # required
        job_id=job_id,  # required
        created_at=overrides.get("created_at", datetime.now(timezone.utc)),
    )
    session.add(saved_job)
    session.commit()
    return saved_job


def create_job_application(session, **overrides):
    application = JobApplicationORM(
        application_id=overrides.get("application_id", str(uuid.uuid4())),
        user_id=overrides["user_id"],  # required
        job_id=overrides["job_id"],    # required
        ats_report_id=overrides.get("ats_report_id"),
        cv_id=overrides.get("cv_id", str(uuid.uuid4())),
        applied_date=overrides.get("applied_date", datetime.now(timezone.utc)),
        updated_at=overrides.get("updated_at", datetime.now(timezone.utc)),
        cover_letter=overrides.get("cover_letter", "I am excited to apply."),
        method=overrides.get("method", "website"),
        notes=overrides.get("notes"),
        expected_salary=overrides.get("expected_salary", 50000),
        preferred_start_date=overrides.get("preferred_start_date"),
        preferred_location=overrides.get("preferred_location", "Remote"),
        required_documents=overrides.get("required_documents", ["CV", "ID Copy"]),
        questionnaire_answers=overrides.get("questionnaire_answers", ["Because I love this role."]),
        last_application_stage=overrides.get("last_application_stage", "Applied"),
        application_stage=overrides.get("application_stage", "Applied"),
        validation_score=overrides.get("validation_score", 90),
        missing_requirements=overrides.get("missing_requirements", []),
        review_summary=overrides.get("review_summary", "Strong candidate."),
    )
    session.add(application)
    session.commit()
    return application


def create_ats_report(session, **overrides):
    report = ATSReportORM(
        ats_report_id=overrides.get("ats_report_id", str(uuid.uuid4())),
        job_id=overrides["job_id"],  # required
        cv_id=overrides["cv_id"],    # required
        score=overrides.get("score", 75),
        matched_keywords=overrides.get("matched_keywords", ["Python", "Django"]),
        missing_keywords=overrides.get("missing_keywords", ["Flask"]),
        feedback=overrides.get("feedback", "Good match with some missing tech."),
        created_at=overrides.get("created_at", datetime.now(timezone.utc)),
    )
    session.add(report)
    session.commit()
    return report




def create_job_approval_request(session, **overrides):
    request = JobApprovalRequestORM(
        request_id=overrides.get("request_id", str(uuid.uuid4())),
        job_id=overrides["job_id"],  # required
        token=overrides.get("token", str(uuid.uuid4())),
        token_expires=overrides.get("token_expires", datetime.now(timezone.utc) + timedelta(days=2)),
        requested_at=overrides.get("requested_at", datetime.now(timezone.utc)),
        requested_by=overrides["requested_by"],  # required
        approvers=overrides.get("approvers", ["user-1", "user-2"]),
        status=overrides.get("status", "pending"),
        decision_at=overrides.get("decision_at"),
        decision_by=overrides.get("decision_by"),
        feedback=overrides.get("feedback", None),
    )
    session.add(request)
    session.commit()
    return request


def create_job_with_ref(session, job_ref, title="Sample Job", status="active"):
    job = JobsORM(
        job_id=str(uuid.uuid4()),
        job_ref=job_ref,
        title=title,
        description="Test job description",
        status=status
    )
    session.add(job)
    session.commit()
    return job




import uuid
from datetime import datetime, timezone
from app.models import CompanyORM  # Update import path as needed


def create_company(session, **overrides) -> CompanyORM:
    """Factory to create and persist a test CompanyORM with optional field overrides."""

    defaults = {
        "company_id": str(uuid.uuid4()),
        "name": f"TestCorp-{uuid.uuid4().hex[:6]}",
        "description": "A leading company in tech.",
        "industry": "Technology",
        "website": "https://example.com",
        "logo_url": "https://example.com/logo.png",
        "city": "San Francisco",
        "province": "California",
        "country": "USA",
        "contact_email": "contact@example.com",
        "phone_number": "+1-555-123-4567",
        "billing_email": None,
        "send_invoice_emails": True,
        "send_trial_reminders": True,
        "employee_count": 150,
        "founded_year": 2010,
        "tech_stack": ["Python", "React", "AWS"],
        "linkedin_url": "https://linkedin.com/company/example",
        "twitter_handle": "@example",
        "is_verified": True,
        "time_verification_process_started": datetime.now(timezone.utc),
        "verification_status": "approved",
        "ip_address": "127.0.0.1",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    data = {**defaults, **overrides}

    company = CompanyORM(**data)

    session.add(company)
    session.commit()
    session.refresh(company)

    return company


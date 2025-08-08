from typing import Dict, List, Optional
from src.database.models import (
    Company,
    Job,
    JobSeekerProfile,
    JobSeekerCV,
    ATSReport,
    JobApplication
)
from src.utils.route_helpers import get_service

_FAKE_MODE = True  # Default to True for development purposes

def enable_fake_mode():
    global _FAKE_MODE
    _FAKE_MODE = True

def disable_fake_mode():
    global _FAKE_MODE
    _FAKE_MODE = False

def is_fake_mode():
    return _FAKE_MODE

# Data stores
companies: Dict[str, Company] = {}
jobs: Dict[str, Job] = {}
jobseekers: Dict[str, JobSeekerProfile] = {}
resumes: Dict[str, JobSeekerCV] = {}
ats_reports: Dict[str, ATSReport] = {}
job_applications: Dict[str, JobApplication] = {}

def clear_store():
    """Clear all fake data stores"""
    companies.clear()
    jobs.clear()
    jobseekers.clear()
    resumes.clear()
    ats_reports.clear()
    job_applications.clear()

# Relationship helper methods
def get_company_jobs(company_id: str) -> List[Job]:
    """Get all jobs for a company"""
    return [job for job in jobs.values() if job.company_id == company_id]

def get_job_applications(job_id: str) -> List[JobApplication]:
    """Get all applications for a job"""
    return [app for app in job_applications.values() if app.job_id == job_id]

def get_user_applications(user_id: str) -> List[JobApplication]:
    """Get all applications for a user"""
    return [app for app in job_applications.values() if app.user_id == user_id]

def get_user_resumes(user_id: str) -> List[JobSeekerCV]:
    """Get all resumes for a user"""
    return [resume for resume in resumes.values() if resume.user_uid == user_id]

def get_application_full_data(application_id: str) -> Optional[dict]:
    """Get complete application data with all related entities"""
    app = job_applications.get(application_id)
    if not app:
        return None
        
    return {
        'application': app,
        'job': jobs.get(app.job_id),
        'profile': jobseekers.get(app.user_id),
        'resume': resumes.get(app.cv_id),
        'ats_report': ats_reports.get(app.ats_report_id),
        'company': companies.get(jobs[app.job_id].company_id) if app.job_id in jobs else None
    }

def get_fake_job(job_id: str) -> Job:
    """
    
    :param job_id: 
    :return: 
    """
    logger = get_service("logger")()("GET FAKE JOBS :")
    logger.info("GET FAKE JOBS : {jobs}")
    return jobs.get(job_id)
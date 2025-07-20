# src/controllers/fake_data/store.py

companies = {}
jobs = {}
jobseekers = {}
resumes = {}
ats_reports = {}
job_applications = {}


def clear_store():
    companies.clear()
    jobs.clear()
    jobseekers.clear()
    resumes.clear()
    ats_reports.clear()
    job_applications.clear()

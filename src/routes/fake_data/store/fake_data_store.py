# src/controllers/fake_data/store.py

# src/controllers/fake_data/toggles.py

_FAKE_MODE = True  # Default to True for development purposes


def enable_fake_mode():
    global _FAKE_MODE
    _FAKE_MODE = True


def disable_fake_mode():
    global _FAKE_MODE
    _FAKE_MODE = False


def is_fake_mode():
    return _FAKE_MODE

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

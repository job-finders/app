# src/controllers/fake_data/controller.py

from typing import Optional, List
from src.database.models import JobApplication, JobSeekerCV
from src.routes.fake_data import store
from src.routes.fake_data.seeds import seeds


class FakeDataController:

    async def get_job_application_details(self, application_id: str) -> Optional[JobApplication]:
        return store.job_applications.get(application_id)

    async def get_cv_by_id(self, cv_id: str) -> Optional[JobSeekerCV]:
        return store.resumes.get(cv_id)

    async def get_job_applications(self, job_id: str) -> (Optional[JobApplication], List[JobApplication]):
        matching = [app for app in store.job_applications.values() if app.job_id == job_id]
        if not matching:
            # Seed fake applications
            for _ in range(5):
                seeds.generate_fake_application_pipeline(job_id)
            matching = [app for app in store.job_applications.values() if app.job_id == job_id]
        return store.jobs.get(job_id), matching

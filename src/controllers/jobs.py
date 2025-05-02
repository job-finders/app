import uuid
from datetime import datetime, timedelta

from flask import Flask
from sqlalchemy import or_

from src.controllers.controller import Controllers
from src.controllers.controller import error_handler
from src.database.models.jobs import Job
from src.database.sql.jobs import JobsORM


class JobsController(Controllers):
    # TODO make this job controller support the full functionality of a job site
    def __init__(self):
        super().__init__()

    def init_app(self, app: Flask):
        super().init_app(app=app)

    @error_handler
    async def get_all_jobs(self) -> list[Job]:
        """Complete listings of all jobs in database"""
        with self.get_session() as session:
            jobs_orm_list = session.query(JobsORM).all()
            return [
                Job(**self._orm_to_job_dict(job))
                for job in jobs_orm_list if job
            ]

    @error_handler
    async def get_job_by_id(self, job_id: str) -> Job | None:
        """Find a job matching the job_id from database"""
        with self.get_session() as session:
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
                return None
            return Job(**self._orm_to_job_dict(job_orm))

    async def get_job_by_reference(self, reference: str) -> Job | None:
        """

        :param reference:
        :return:
        """
        with self.get_session() as session:
            job_orm = session.query(JobsORM).filter_by(job_ref=reference).first()
            if not job_orm:
                return None
            return Job(**self._orm_to_job_dict(job_orm))


    @error_handler
    async def get_jobs_by_search_terms(self, search_term: str) -> list[Job]:
        """Find jobs matching the search terms"""
        with self.get_session() as session:
            search_pattern = f"%{search_term}%"
            jobs_orm_list = session.query(JobsORM).filter(
                or_(
                    JobsORM.search_term.ilike(search_pattern),
                    JobsORM.title.ilike(search_pattern),
                    JobsORM.company_name.ilike(search_pattern),
                    JobsORM.description.ilike(search_pattern),
                    JobsORM.desired_skills.ilike(search_pattern)
                )
            ).all()

            return [
                Job(**self._orm_to_job_dict(job))
                for job in jobs_orm_list if job
            ]

    @error_handler
    async def update_job(self, job_id: str, updated_job: Job) -> Job:
        """Updates the job matching the job_id"""
        with self.get_session() as session:
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
                raise ValueError(f"Job {job_id} not found")

            # Update all fields except job_id
            for key, value in updated_job.dict().items():
                if key != "job_id" and hasattr(job_orm, key):
                    setattr(job_orm, key, value)

            job_orm.updated_time = datetime.now().strftime("%d %b %Y")
            session.commit()
            return Job(**self._orm_to_job_dict(job_orm))

    @error_handler
    async def de_activate_job_listing(self, job_id: str) -> Job:
        """Mark job as inactive by setting expiration date to past"""
        with self.get_session() as session:
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
                raise ValueError(f"Job {job_id} not found")

            # Set expiration date to yesterday
            job_orm.expiration_date = datetime.now().date() - timedelta(days=1)
            session.commit()
            return Job(**self._orm_to_job_dict(job_orm))

    @error_handler
    async def activate_job_listing(self, job_id: str) -> Job:
        """Activate job listing by resetting expiration date"""
        with self.get_session() as session:
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
                raise ValueError(f"Job {job_id} not found")

            # Reset expiration date using original expires field
            days = int(job_orm.expires.split()[2])
            job_orm.expiration_date = datetime.now().date() + timedelta(days=days)
            session.commit()
            return Job(**self._orm_to_job_dict(job_orm))

    @error_handler
    async def create_job(self, job: Job) -> Job:
        """Create new job listing"""
        with self.get_session() as session:
            # Convert Pydantic model to ORM-compatible dict
            job_data = job.dict()

            # Handle optional fields and conversions
            job_data["desired_skills"] = ", ".join(job_data.get("desired_skills", []))

            # Ensure posted_date and expiration_date are set
            if "posted_date" not in job_data or not job_data["posted_date"]:
                job_data["posted_date"] = datetime.utcnow().date()
            if "expiration_date" not in job_data or not job_data["expiration_date"]:
                job_data["expiration_date"] = job_data["posted_date"] + timedelta(days=30)
            if not job_data.get("job_id"):
                job_data["job_id"] = str(uuid.uuid4())

            new_job_orm = JobsORM(**job_data)
            session.add(new_job_orm)
            session.commit()
            return Job(**self._orm_to_job_dict(new_job_orm))

    def _orm_to_job_dict(self, job_orm: JobsORM) -> dict:
        """Convert ORM object to Job model-compatible dictionary"""
        job_dict = job_orm.to_dict()

        # Convert desired_skills string to list
        if job_dict["desired_skills"]:
            job_dict["desired_skills"] = [
                skill.strip()
                for skill in job_dict["desired_skills"].split(",")
            ]
        else:
            job_dict["desired_skills"] = []


        # Convert dates to string format
        job_dict["posted_date"] = job_orm.posted_date.strftime("%d %b %Y")
        job_dict["expiration_date"] = (
            job_orm.expiration_date.strftime("%d %b %Y") if job_orm.expiration_date else None
        )

        return job_dict

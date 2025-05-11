import uuid
from datetime import datetime, timedelta, timezone

from flask import Flask
from sqlalchemy import or_, select, func
from src.controllers.controller import Controllers
from src.controllers.controller import error_handler
from src.database.models.jobs import Job, JobApplication
from src.database.sql.jobs import JobsORM, SavedJobORM,  JobApplicationORM


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
            for key, value in updated_job.model_dump(exclude_unset=True).items():
                if key != "job_id" and hasattr(job_orm, key):
                    setattr(job_orm, key, value)

            # Use UTC-aware datetime with proper timezone
            job_orm.updated_time = datetime.now(timezone.utc)
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
            job_orm.expiration_date = datetime.now(timezone.utc).date() - timedelta(days=1)
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
            job_orm.expiration_date = datetime.now(timezone.utc).date() + timedelta(days=days)
            session.commit()
            return Job(**self._orm_to_job_dict(job_orm))

    @error_handler
    async def create_job(self, job: Job) -> Job:
        """Create new job listing"""
        with self.get_session() as session:
            # Convert Pydantic model to ORM-compatible dict
            job_data = job.model_dump()

            # Handle optional fields and conversions
            job_data["desired_skills"] = ", ".join(job_data.get("desired_skills", []))

            # Ensure posted_date and expiration_date are set
            if "posted_date" not in job_data or not job_data["posted_date"]:
                job_data["posted_date"] = datetime.now(timezone.utc).date()
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

    @error_handler
    async def get_jobs_by_title(self, title: str) -> list[Job]:
        """Search for jobs by job title (case-insensitive partial match)"""
        with self.get_session() as session:
            search_pattern = f"%{title}%"
            jobs_orm_list = session.query(JobsORM).filter(
                JobsORM.title.ilike(search_pattern)
            ).all()

            return [
                Job(**self._orm_to_job_dict(job))
                for job in jobs_orm_list if job
            ]

    @error_handler
    async def get_jobs_by_qualification(self, qualification: str) -> list[Job]:
        """Filter jobs requiring a specific qualification (case-insensitive match)"""
        with self.get_session() as session:
            search_pattern = f"%{qualification}%"
            jobs_orm_list = session.query(JobsORM).filter(
                JobsORM.desired_skills.ilike(search_pattern)
            ).all()

            return [
                Job(**self._orm_to_job_dict(job))
                for job in jobs_orm_list if job
            ]

    @error_handler
    async def get_jobs_by_location(self, location: str) -> list[Job]:
        """Filter jobs by city, province, or region (case-insensitive match)"""
        with self.get_session() as session:
            search_pattern = f"%{location}%"
            jobs_orm_list = session.query(JobsORM).filter(
                JobsORM.location.ilike(search_pattern)
            ).all()

            return [
                Job(**self._orm_to_job_dict(job))
                for job in jobs_orm_list if job
            ]

    @error_handler
    async def get_jobs_by_category(self, category: str) -> list[Job]:
        """Filter jobs by category (e.g., IT, Nursing, Admin)"""
        with self.get_session() as session:
            search_pattern = f"%{category}%"
            jobs_orm_list = session.query(JobsORM).filter(
                JobsORM.search_term.ilike(search_pattern)
            ).all()

            return [
                Job(**self._orm_to_job_dict(job))
                for job in jobs_orm_list if job
            ]

    @error_handler
    async def get_recent_jobs(self, limit: int = 10) -> list[Job]:
        """Retrieve most recently posted jobs"""
        with self.get_session() as session:
            jobs_orm_list = (
                session.query(JobsORM)
                .order_by(JobsORM.posted_date.desc())
                .limit(limit)
                .all()
            )
            return [
                Job(**self._orm_to_job_dict(job))
                for job in jobs_orm_list if job
            ]

    @error_handler
    async def get_active_jobs(self) -> list[Job]:
        """Get only currently active jobs (non-expired)"""
        with self.get_session() as session:
            today = datetime.now(timezone.utc).date()
            jobs_orm_list = (
                session.query(JobsORM)
                .filter(JobsORM.expiration_date >= today)
                .order_by(JobsORM.posted_date.desc())
                .all()
            )
            return [
                Job(**self._orm_to_job_dict(job))
                for job in jobs_orm_list if job
            ]

    @error_handler
    async def save_job_for_user(self, user_id: str, job_id: str) -> None:
        """Save a job to a user's saved list"""
        with self.get_session() as session:
            # Find the job by job_id
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
                raise ValueError(f"Job {job_id} not found")

            # Check if the user already saved this job
            saved_job = session.query(SavedJobORM).filter_by(user_id=user_id, job_id=job_id).first()
            if saved_job:
                raise ValueError(f"Job {job_id} already saved by user {user_id}")

            # Save the job for the user
            new_saved_job = SavedJobORM(user_id=user_id, job_id=job_id)
            session.add(new_saved_job)

    @error_handler
    async def remove_saved_job(self, user_id: str, job_id: str) -> None:
        """Remove a saved job from the user's list"""
        with self.get_session() as session:
            # Find the saved job entry in the saved_jobs table
            saved_job_orm = session.query(SavedJobORM).filter_by(user_id=user_id, job_id=job_id).first()

            if not saved_job_orm:
                raise ValueError(f"Saved job with job_id {job_id} for user {user_id} not found")

            # Remove the saved job entry from the database
            session.delete(saved_job_orm)

    @error_handler
    async def get_saved_jobs_for_user(self, user_id: str) -> list[Job]:
        """Get jobs saved by a user"""
        with self.get_session() as session:
            result = await session.execute(
                select(JobsORM)
                .join(SavedJobORM, JobsORM.job_id == SavedJobORM.job_id)
                .where(SavedJobORM.user_id == user_id)
            )
            jobs = result.scalars().all()
            return [Job(**job.to_dict()) for job in jobs]

    @error_handler
    async def get_applied_job_applications_for_user(self, user_id: str) -> list[JobApplication]:
        """Get jobs the user has applied for"""
        with self.get_session() as session:
            applied_jobs_orm_list = session.query(JobApplicationORM).filter_by(user_id=user_id).all()
            return [JobApplication(**job.to_dict()) for job in applied_jobs_orm_list]

    @error_handler
    async def get_jobs_by_employer(self, employer_id: str) -> list[Job]:
        """List jobs posted by a specific employer"""
        with self.get_session() as session:
            stmt = select(JobsORM).where(JobsORM.search_term == employer_id)
            result = await session.execute(stmt)
            jobs = result.scalars().all()
            return [Job(**job.to_dict()) for job in jobs]

    @error_handler
    async def delete_job(self, job_id: str) -> None:
        """Permanently delete a job listing"""
        with self.get_session() as session:
            # Query the job by job_id
            job_orm = session.get(JobsORM, job_id)

            # Delete the job from the database
            if job_orm:
                session.delete(job_orm)
            return None

    @error_handler
    async def count_total_jobs(self) -> int:
        """Count total number of jobs in the database"""
        with self.get_session() as session:
            result = await session.execute(select([func.count(JobsORM.job_id)]))
            total_jobs = result.scalar()
            return total_jobs

    @error_handler
    async def count_active_jobs(self) -> int:
        """Count jobs that are still active (not expired)"""
        with self.get_session() as session:
            # Assuming expiration_date is a column in JobsORM and the active jobs are those that haven't expired
            result = await session.execute(
                select([func.count(JobsORM.job_id)]).filter(JobsORM.expiration_date > datetime.now(timezone.utc).date())
            )
            active_jobs = result.scalar()
            return active_jobs

    @error_handler
    async def count_jobs_by_category(self) -> dict[str, int]:
        """Return a dictionary with categories and job counts"""
        with self.get_session() as session:
            # Assuming 'category' is stored in a field like search_term or another field in JobsORM
            result = await session.execute(
                select([JobsORM.search_term, func.count(JobsORM.job_id)])
                .group_by(JobsORM.search_term)
            )
            category_counts = {category: count for category, count in result}
            return category_counts

    @error_handler
    async def apply_to_job(self, job_application: JobApplication):
        """
            Apply a user to a job by saving the application and applied job records.
            This method assumes there are 'JobApplicationORM' and 'AppliedJobORM' tables.

            :param job_application:
            :return: Confirmation message or exception if the user has already applied
        """
        # Open a session (use existing session management here)
        with self.get_session() as session:
            # Check if the user has already applied for this job (in AppliedJobORM)
            existing_application = session.query(JobApplicationORM).filter_by(job_id=job_application.job_id, user_id=job_application.user_id).first()
            if existing_application:
                return None

            # Create new AppliedJobORM record (tracking application action)
            applied_job_orm = JobApplicationORM(**job_application.model_dump())


            # Add both records to the session and commit
            session.add(applied_job_orm)
            return job_application


    @error_handler
    async def withdraw_job_application(self, application_id: str) -> bool:
        """
        Withdraws a job application by updating its status and withdrawal timestamp
        Args:
            application_id: The ID of the application to withdraw
        Returns:
            bool: True if withdrawal was successful, False otherwise
        """
        with self.get_session() as session:
            # Get the application with lock to prevent race conditions
            job_application = session.query(JobApplicationORM).filter_by(
                application_id=application_id
            ).with_for_update().first()

            if not job_application:
                self.logger.debug(f"Application {application_id} not found")
                return False

            # Check current state before making changes
            if job_application.status == "withdrawn":
                self.logger.debug(f"Application {application_id} already withdrawn")
                return True  # Considered successful as it's in desired state

            # Update fields
            job_application.status = "withdrawn"  # Lowercase for consistency
            job_application.updated_at = datetime.now(timezone.utc)

            # Explicitly mark as modified (helps with detached instances)
            session.add(job_application)

            # Let the session handler handle commit/rollback
            return True


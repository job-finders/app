import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from flask import Flask
from sqlalchemy import or_, select, func, and_, case
from sqlalchemy.orm import joinedload

from database.models.jobseeker_profile import JobSeekerProfile
from database.models.resume import JobSeekerCV
from src.database.sql.jobseeker_profile import JobSeekerProfileORM
from src.database.sql.resume import JobSeekerCVORM
from src.database.sql.users import UserORM
from src.controllers.controller import Controllers
from src.controllers.controller import error_handler
from src.database.models.jobs_model import Job, JobApplication, SavedJob, JobStatistics, StatusCounts, \
    ApplicationMetrics, ApplicationFunnelStats
from src.database.sql.jobs_sql import JobsORM, SavedJobORM, JobApplicationORM, CompanyORM


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
            self.logger.info(f"Loaded a total of {len(jobs_orm_list)} Jobs")
            return [Job(**job.to_dict()) for job in jobs_orm_list if job]

    @error_handler
    async def get_job_by_id(self, job_id: str) -> Job | None:
        """Find a job matching the job_id from database"""
        with self.get_session() as session:
            job_orm: JobsORM = session.get(JobsORM, job_id)
            if not job_orm:
                return None
            return Job(**job_orm.to_dict())

    async def get_job_by_reference(self, reference: str) -> Job | None:
        """

        :param reference:
        :return:
        """
        with self.get_session() as session:
            _reference = reference.casefold()
            job_orm = session.query(JobsORM).filter_by(job_ref=_reference).first()
            if not job_orm:
                return None
            return Job(**job_orm.to_dict())


    @error_handler
    async def update_job(self, job_id: str, updated_job: Job) -> Job| None:
        """Updates the job matching the job_id"""
        with self.get_session() as session:
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
               return None

            # Update all fields except job_id
            for key, value in updated_job.model_dump(exclude_unset=True).items():
                if key != "job_id" and hasattr(job_orm, key):
                    setattr(job_orm, key, value)

            # Use UTC-aware datetime with proper timezone
            job_orm.updated_time = datetime.now(timezone.utc)


            return Job(**job_orm.to_dict())

    @error_handler
    async def de_activate_job_listing(self, job_id: str) -> Job | None:
        """Mark job as inactive by setting expiration date to past"""
        with self.get_session() as session:
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
                return None

            # Set expiration date to yesterday
            job_orm.status = "closed"
            job_orm.expiration_date = datetime.now(timezone.utc).date() - timedelta(days=1)
            job_orm.updated_at = datetime.now(timezone.utc)

            return Job(**job_orm.to_dict())

    @error_handler
    async def activate_job_listing(self, job_id: str) -> Job | None:
        """Activate job listing by resetting expiration date"""
        with self.get_session() as session:
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
                return None

            # Set expiration date to yesterday
            job_orm.status = "activa"
            job_orm.expiration_date = datetime.now(timezone.utc).date() - timedelta(days=1)
            job_orm.updated_at = datetime.now(timezone.utc)

            return Job(**job_orm.to_dict())


    @error_handler
    async def archive_job_listing(self, job_id: str) -> Job | None:
        """Archive job listing """
        with self.get_session() as session:
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
                return None

            # Set expiration date to yesterday
            job_orm.status = "archive"
            job_orm.expiration_date = datetime.now(timezone.utc).date() - timedelta(days=1)
            job_orm.updated_at = datetime.now(timezone.utc)

            return Job(**job_orm.to_dict())

    @error_handler
    async def feature_job_listing(self, job_id: str) -> Job | None:
        """Archive job listing """
        with self.get_session() as session:
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
                return None

            # Set expiration date to yesterday
            job_orm.status = "active"
            job_orm.is_featured = True
            job_orm.expiration_date = datetime.now(timezone.utc).date() - timedelta(days=1)
            job_orm.updated_at = datetime.now(timezone.utc)

            return Job(**job_orm.to_dict())

    @error_handler
    async def create_job(self, job: Job) -> Job:
        """Create new job listing"""
        with self.get_session() as session:
            # Convert Pydantic model to ORM-compatible dict
            job_existing = session.query(JobsORM).filter_by(job_id=job.job_id).first()
            if job_existing:
                return None

            job_orm = JobsORM(**job.model_dump())
            session.add(job_orm)

            return Job(**job_orm.to_dict())


    @error_handler
    async def get_jobs_by_title(self, title: str) -> list[Job]:
        """Search for jobs by job title (case-insensitive partial match)"""
        with self.get_session() as session:
            search_pattern = f"%{title}%"
            jobs_orm_list = session.query(JobsORM).filter(
                JobsORM.title.ilike(search_pattern)
            ).all()

            return [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list if job_orm]


    @error_handler
    async def get_jobs_by_qualification(
            self,
            qualification: str,
            qualification_types: Optional[list[str]] = None
    ) -> list[Job]:
        """Filter jobs by educational qualification(s) with case-insensitive matching.

        Searches across specified keys in education_requirements JSON field.
        Default South African qualification types:
        - matric: National Senior Certificate (Grade 12)
        - diploma: National Diploma
        - bachelor: Bachelor's Degree (e.g., BA, BSc, BCom)
        - honours: Honours Degree
        - masters: Master's Degree
        - phd: Doctoral Degree
        - certificate: Industry Certificates
        - trade_certificate: Artisan Trade Certificates
        """
        # Set default SA qualification types if none provided
        if qualification_types is None:
            qualification_types = ["matric","diploma","bachelor","honours","masters","phd","certificate",
                "trade_certificate"]

        search_pattern = f"%{qualification}%"

        with self.get_session() as session:
            # Build OR conditions for all specified qualification types
            conditions = [
                JobsORM.education_requirements[q_type].astext.ilike(search_pattern)
                for q_type in qualification_types
            ]

            jobs_orm_list = session.query(JobsORM).filter(or_(*conditions)).all()

            return [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list if job_orm]

    from sqlalchemy import or_

    @error_handler
    async def get_jobs_by_location(self, location: str) -> list[Job]:
        """Filter jobs by city, province, or country components (case-insensitive match)"""
        with self.get_session() as session:
            search_pattern = f"%{location}%"
            jobs_orm_list = session.query(JobsORM).filter(
                or_(
                    JobsORM.city.ilike(search_pattern),
                    JobsORM.province.ilike(search_pattern),
                    JobsORM.country.ilike(search_pattern)
                )
            ).all()
            return [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list if job_orm]



    @error_handler
    async def get_jobs_by_category(
            self,
            category: str,
            subcategories: Optional[list[str]] = None
    ) -> list[Job]:
        """
        Filter jobs by category with optional subcategories.

        Common South African Categories:
        - IT & Tech
        - Finance & Accounting
        - Healthcare & Nursing
        - Engineering
        - Education & Training
        - Retail & Sales
        - Hospitality & Tourism
        - Construction & Trades
        - Government & Public Sector
        - Logistics & Supply Chain
        """
        with self.get_session() as session:
            query = session.query(JobsORM)

            # Base category filter
            filters = [JobsORM.category.ilike(f"%{category}%")]

            # Handle subcategories if provided
            if subcategories:
                sub_filters = [JobsORM.category.ilike(f"%{sub}%") for sub in subcategories]
                filters.append(or_(*sub_filters))

            jobs_orm_list = query.filter(and_(*filters)).all()

            return [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list if job_orm]

    @error_handler
    async def get_recent_jobs(self, limit: int = 100) -> list[Job]:
        """Retrieve most recently posted active jobs, ordered by posting date
        Args:
            limit: Maximum number of jobs to return (capped at 100 for performance)
        Returns:
            List of Job objects sorted by newest first, excluding expired/archived jobs
        Example:  >>> await api.get_recent_jobs(5)  # Get 5 newest active postings
        """
        # Enforce sensible upper limit for performance
        limit = min(limit, 100)

        with self.get_session() as session:
            jobs_orm_list = (
                session.query(JobsORM)
                .filter(JobsORM.status == 'active')  # Only non-archived/closed jobs
                .order_by(JobsORM.posted_at.desc())  # Use correct column name from ORM
                .limit(limit)
                .all()
            )

            return [
                Job(**job_orm.to_dict())  # Use ORM's native serialization
                for job_orm in jobs_orm_list
                if job_orm and job_orm.is_active  # Double-check active status
            ]

    @error_handler
    async def get_active_jobs(self) -> list[Job]:
        """Get currently active jobs that haven't expired and are marked as active"""
        with self.get_session() as session:
            current_time = datetime.now(timezone.utc)
            jobs_orm_list = (
                session.query(JobsORM)
                .filter(
                    JobsORM.is_active,  # Use hybrid property combining status and expiration
                    JobsORM.expires_at >= current_time
                )
                .order_by(JobsORM.posted_at.desc())
                .all()
            )

            return [
                Job(**job_orm.to_dict())
                for job_orm in jobs_orm_list
                if job_orm and job_orm.is_active
            ]

    @error_handler
    async def save_job_for_user(self, user_id: str, job_id: str) -> None|SavedJob :
        """Save a job to a user's saved list with validation"""
        with self.get_session() as session:
            # Validate both user and job exist
            user_exists = session.query(
                session.query(UserORM).filter_by(user_id=user_id).exists()
            ).scalar()

            job_exists = session.query(
                session.query(JobsORM).filter_by(job_id=job_id).exists()
            ).scalar()

            if not user_exists:
                return None
            if not job_exists:
                return None

            # Check existing save using SQL EXISTS for better performance
            already_saved = session.query(
                session.query(SavedJobORM)
                .filter_by(user_id=user_id, job_id=job_id)
                .exists()
            ).scalar()

            if already_saved:
                return None
            saved_job = SavedJob(user_id=user_id,job_id=job_id)
            # Create and add the saved job to session
            session.add(SavedJobORM(**saved_job.model_dump()))

            return saved_job

    @error_handler
    async def remove_saved_job(self, user_id: str, job_id: str) -> bool:
        """Remove a saved job from the user's list"""
        with self.get_session() as session:
            # Find the saved job entry in the saved_jobs table
            saved_job_orm = session.query(SavedJobORM).filter_by(user_id=user_id, job_id=job_id).first()

            if not saved_job_orm:
                return  False

            # Remove the saved job entry from the database
            session.delete(saved_job_orm)
            return True

    @error_handler
    async def get_saved_jobs_for_user(self, user_id: str) -> list[Job]:
        """Get jobs saved by a user with saving metadata"""
        with self.get_session() as session:
            result = await session.execute(
                select(SavedJobORM)
                .options(joinedload(SavedJobORM.job))  # Eager load job relationship
                .filter(SavedJobORM.user_id == user_id)
                .order_by(SavedJobORM.created_at.desc())
            )

            saved_jobs = result.scalars().all()

            return [
                Job(**saved_job.job.to_dict())
                for saved_job in saved_jobs
                if saved_job.job  # Handle potential orphaned entries
            ]

    @error_handler
    async def get_applied_jobs_for_user(self, user_id: str) -> list[JobApplication]:
        """Get job applications with full job details for a user"""
        with self.get_session() as session:
            result = await session.execute(
                select(JobApplicationORM)
                .options(joinedload(JobApplicationORM.job))  # Eager load job details
                .filter(JobApplicationORM.user_id == user_id)
                .order_by(JobApplicationORM.applied_date.desc())
            )

            applications = result.unique().scalars().all()

            return [
                JobApplication(**app.to_dict())
                for app in applications
                if app.job  # Ensure the associated job still exists
            ]

    @error_handler
    async def get_jobs_by_employer(self, employer_id: str, limit: int = 100) -> list[Job]:
        """Get jobs posted by a specific company/employer with validation"""
        with self.get_session() as session:
            # Validate company exists first
            company_exists = session.query(
                session.query(CompanyORM)
                .filter(CompanyORM.company_id == employer_id)
                .exists()
            ).scalar()

            if not company_exists:
                return []

            # Get jobs with company details
            result = await session.execute(
                select(JobsORM)
                .options(joinedload(JobsORM.company))  # Eager load company data
                .filter(JobsORM.company_id == employer_id)  # Use proper foreign key
                .order_by(JobsORM.posted_at.desc())
                .limit(min(limit, 1000))  # Prevent excessive results
            )

            jobs = result.unique().scalars().all()

            return [Job(**job.to_dict()) for job in jobs]

    @error_handler
    async def delete_job(self, job_id: str) -> bool:
        """Permanently delete a job listing and its dependencies"""
        with self.get_session() as session:
            # Lock the job row for update
            job_orm = session.query(JobsORM).filter_by(job_id=job_id).with_for_update().first()

            if not job_orm:
                return False


            # Delete dependent records first (applications, saved jobs)
            session.query(JobApplicationORM).filter_by(job_id=job_id).delete()
            session.query(SavedJobORM).filter_by(job_id=job_id).delete()

            # Delete main job record
            session.delete(job_orm)

            # Commit transaction
            return True


    # Updated Statistics Method
    @error_handler
    async def get_job_statistics(self) -> JobStatistics:
        """Return comprehensive job statistics with validation"""
        with self.get_session() as session:
            # Core metrics query
            stats = session.query(
                func.count(JobsORM.job_id).label('total_jobs'),
                func.sum(case((JobsORM.status == 'active', 1), else_=0)).label('active_jobs'),
                func.sum(case((JobsORM.status == 'closed', 1), else_=0)).label('closed_jobs'),
                func.sum(case((JobsORM.status == 'archived', 1), else_=0)).label('archived_jobs'),
                func.sum(JobsORM.application_count).label('total_applications'),
                func.sum(case((JobsORM.application_count > 0, 1), else_=0)).label('jobs_with_applications'),
                func.sum(case((JobsORM.status == 'active') & (JobsORM.expires_at > datetime.now(timezone.utc)), 1)).label('current_active_jobs')
            ).one()

            # Additional queries
            category_counts = dict(session.query(JobsORM.category,func.count(JobsORM.job_id)).group_by(JobsORM.category).all())

            recent_jobs = (session.query(func.count(JobsORM.job_id))
                           .filter(JobsORM.posted_at >= datetime.now(timezone.utc) - timedelta(days=30)).scalar() or 0)

            return JobStatistics(
                total_jobs=stats.total_jobs,
                status_counts=StatusCounts(
                    active=stats.active_jobs,
                    closed=stats.closed_jobs,
                    archived=stats.archived_jobs,
                    current_active=stats.current_active_jobs
                ),
                application_metrics=ApplicationMetrics(
                    total_applications=stats.total_applications or 0,
                    jobs_with_applications=stats.jobs_with_applications
                ),
                categories=category_counts,
                recent_jobs_30d=recent_jobs,
                calculated_at=datetime.now(timezone.utc)
            )

    @error_handler
    async def apply_to_job(self, job_application: JobApplication) -> JobApplication| None:
        """
        Submit a job application with validation and atomic transaction handling
        Args:
            job_application: Complete application details including user/job IDs
        Returns:
            JobApplication: The created application record
        Raises:
            ValueError: If duplicate application or invalid job/user
        """
        with self.get_session() as session:
            # Validate job exists
            if not session.query(JobsORM).filter_by(job_id=job_application.job_id).first():
                # raise ValueError(f"Job {job_application.job_id} does not exist")
                self.logger.info(f"Job {job_application.job_id} does not exist")
                return None

            # Validate user exists
            if not session.query(UserORM).filter_by(user_id=job_application.user_id).first():
                # raise ValueError(f"User {job_application.user_id} not found")
                self.logger.info(f"User {job_application.user_id} not found")
                return None

            # Check for existing application
            existing = session.query(JobApplicationORM).filter_by(
                job_id=job_application.job_id,
                user_id=job_application.user_id
            ).first()

            if existing:
                # raise ValueError("User has already applied to this job")
                self.logger(f"User has already applied to this job {existing.application_id}")
                return None

                # New completeness check
            validation = await self.validate_application_completeness(job_application)

            if validation['score'] < 70:
                job_application.status = "needs_review"

            # Create and persist application
            applied_job_orm = JobApplicationORM(**job_application.model_dump(),
                validation_score=validation['score'], missing_requirements=validation['missing'])

            # TODO - Generate AI summary async
            # TODO - create a job queu add the job to the queue then execute when application is idle
            # self.app.executor.submit(
            #     self._generate_summary_background,
            #     applied_job_orm.application_id
            # )

            session.add(applied_job_orm)
            session.commit()

            return JobApplication(**applied_job_orm.to_dict())

    def _generate_summary_background(self, application_id: str):
        """Background task for AI summary generation"""
        with self.app.app_context():
            summary = self.generate_application_review_summary(application_id)
            with self.get_session() as session:
                job_application_orm = session.query(JobApplicationORM).get(application_id)
                job_application_orm.review_summary = summary
            return None

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
            # Update job application count
            session.query(JobsORM).filter_by(job_id=job_application.job_id).update({
                JobsORM.application_count: JobsORM.application_count - 1,
                JobsORM.updated_at: datetime.now(timezone.utc)
            })
            # Explicitly mark as modified (helps with detached instances)
            session.add(job_application)

            # Let the session handler handle commit/rollback
            return True

        # -------------------------ADVANCED SEARCH AND JOB RECOMMENDATIONS ---

    @error_handler
    async def get_personalized_job_recommendations(self, user_id: str) -> list[Job]:
        """
        Generate personalized job recommendations for a job seeker.

        The recommendation engine considers various aspects of the user's profile,
        including job title preferences, industries of interest, location preferences,
        remote work preferences, relevant skills from their primary CV, and salary expectations.
        It excludes jobs the user has already applied for and prioritizes active, non-expired jobs.

        Args:
            user_id (str): Unique identifier of the job seeker.

        Returns:
            list[Job]: A list of recommended job postings, ordered by relevance.
        """

        with self.get_session() as session:
            # Get user profile and CV data
            profile_orm: JobSeekerProfileORM = session.query(JobSeekerProfileORM).get(user_id)
            cv_orm: JobSeekerCVORM = session.query(JobSeekerCVORM).filter_by(user_uid=user_id, is_primary=True).first()

            profile = JobSeekerProfile(**profile_orm.to_dict())
            cv = JobSeekerCV(**cv_orm.to_dict())

            if not profile or not cv:
                return []

            # Base query with common filters
            query = session.query(JobsORM).filter(
                JobsORM.status == 'active',
                JobsORM.expires_at > datetime.now(timezone.utc)
            )
            applied_jobs_orm_list = session.query(JobApplicationORM).filter_by(user_id=user_id).all()
            applied_jobs_list = [JobApplication(**applied_job_orm.to_dict()) for applied_job_orm in  applied_jobs_orm_list if applied_job_orm]
            # Exclude already applied jobs
            applied_job_ids = [applied_job.job_id for applied_job in applied_jobs_list]
            if applied_job_ids:
                query = query.filter(JobsORM.job_id.notin_(applied_job_ids))

            # Job Title Preferences
            if profile.job_titles_of_interest:
                title_conds = [JobsORM.title.ilike(f"%{title}%") for title in profile.job_titles_of_interest]
                query = query.filter(or_(*title_conds))

            # Industry Preferences
            if profile.industries_of_interest:
                query = query.filter(JobsORM.category.op('&&')(profile.industries_of_interest))

            # Location Preferences
            location_conds = []
            if profile.location:
                location_conds.extend([
                    JobsORM.city.ilike(f"%{profile.location}%"),
                    JobsORM.province.ilike(f"%{profile.location}%")
                ])
            if profile.locations_of_interest:
                for loc in profile.locations_of_interest:
                    location_conds.extend([
                        JobsORM.city.ilike(f"%{loc}%"),
                        JobsORM.province.ilike(f"%{loc}%")
                    ])
            if location_conds:
                query = query.filter(or_(*location_conds))

            # Remote Preference
            if profile.remote_preference:
                query = query.filter(JobsORM.remote_policy.in_(["REMOTE", "HYBRID"]))

            # Skills Matching (from CV)
            if cv.skills:
                skill_conds = [
                    cond
                    for skill in cv.skills
                    for cond in [
                        JobsORM.required_skills.contains([skill]),
                        JobsORM.preferred_skills.contains([skill])
                    ]
                ]

                query = query.filter(or_(*skill_conds))

            # Salary Expectations (from CV if available)
            if profile.expected_salary:
                query = query.filter(
                    JobsORM.salary_min >= profile.expected_salary * 0.7,
                    JobsORM.salary_max <= profile.expected_salary * 1.3
                )

            # Order by relevance factors
            results = query.order_by(
                JobsORM.posted_at.desc(),
                JobsORM.is_featured.desc(),
                JobsORM.application_count.desc()
            ).limit(100).all()

            return [Job(**job.to_dict()) for job in results]

    @error_handler
    async def calculate_job_match_score(self, job_id: str, user_id: str) -> dict:
        """
        Calculate how well a specific job matches a user's profile and CV.

        This method evaluates the alignment between the job's requirements and
        the user's profile across multiple dimensions such as skills, experience,
        education, industry, title interest, location preference, and remote work compatibility.
        It returns both a numerical score and a human-readable interpretation with suggestions.

        Args:
            job_id (str): The ID of the job to evaluate.
            user_id (str): The ID of the user whose profile is being matched.

        Returns:
            dict: A dictionary containing:
                - 'score_breakdown': Detailed match scores by category.
                - 'interpretation': Human-readable feedback based on the total score.
                - 'recommended_improvements': Suggestions to increase future match scores.
        """

        with self.get_session() as session:

            profile_orm: JobSeekerProfileORM = session.query(JobSeekerProfileORM).get(user_id)
            cv_orm: JobSeekerCVORM   = session.query(JobSeekerCVORM).filter_by(user_uid=user_id, is_primary=True).first()
            job_orm: JobsORM = session.query(JobsORM).get(job_id)

            profile:JobSeekerProfile = JobSeekerProfile(**profile_orm.to_dict())
            cv: JobSeekerCV = JobSeekerCV(**cv_orm.to_dict())
            job: Job = Job(**job_orm.to_dict())

            if not profile or not cv or not job:
                return {}

            scores = {
                'skills': 0,
                'experience': 0,
                'education': 0,
                'industry': 0,
                'title': 0,
                'location': 0,
                'remote': 0,
                'total': 0
            }

            # Skills Match (30% weight)
            if cv.skills and job.required_skills:
                matched_skills = set(cv.skills) & set(job.required_skills)
                required_match = len(matched_skills) / len(job.required_skills) if job.required_skills else 0
                preferred_match = len(set(cv.skills) & set(job.preferred_skills)) / len(
                    job.preferred_skills) if job.preferred_skills else 0
                scores['skills'] = round((required_match * 0.7 + preferred_match * 0.3) * 100)

            # Experience Level (20% weight)
            exp_levels = ['entry', 'mid', 'senior']
            user_exp = cv.experience[-1].level if cv.experience else 'entry'
            user_exp_idx = exp_levels.index(user_exp.lower())
            job_exp_idx = exp_levels.index(job.experience_level.lower())
            scores['experience'] = 100 if user_exp_idx >= job_exp_idx else round((user_exp_idx / job_exp_idx) * 100)

            # Education Match (15% weight)
            if cv.education and job.education_requirements:
                # Assume `cv.education` contains qualification levels in your normalized form (e.g., 'bachelor', 'diploma', etc.)
                user_degrees = {e.qualification.lower() for e in cv.education}

                # Extract job-required qualification keys (e.g., 'bachelor', 'masters') where values are non-empty
                job_degrees = {k for k, v in job.education_requirements.items() if v}

                if job_degrees:
                    scores['education'] = round(len(user_degrees & job_degrees) / len(job_degrees) * 100)
                else:
                    scores['education'] = 0

            # Industry Interest (10% weight)
            if job.category and profile.industries_of_interest:
                scores['industry'] = 100 if job.category in profile.industries_of_interest else 0

            # Job Title Interest (10% weight)
            if profile.job_titles_of_interest:
                scores['title'] = 100 if any(
                    title.lower() in job.title.lower()
                    for title in profile.job_titles_of_interest
                ) else 0

            # Location Compatibility (10% weight)
            location_match = False
            if profile.location and job.city:
                location_match = job.city.lower() == profile.location.lower()

            if not location_match and profile.locations_of_interest:
                location_match = job.city in profile.locations_of_interest
            scores['location'] = 100 if location_match else 0

            # Remote Preference (5% weight)
            scores['remote'] = 100 if (
                    profile.remote_preference and
                    job.remote_policy in ["REMOTE", "HYBRID"]
            ) else 0

            # Calculate weighted total
            weights = {
                'skills': 0.3,
                'experience': 0.2,
                'education': 0.15,
                'industry': 0.1,
                'title': 0.1,
                'location': 0.1,
                'remote': 0.05
            }
            scores['total'] = sum(scores[cat] * weight for cat, weight in weights.items())

            return {
                'score_breakdown': {k: round(v, 1) for k, v in scores.items()},
                'interpretation': self._get_match_interpretation(scores['total']),
                'recommended_improvements': self._get_improvement_suggestions(scores)
            }

    @staticmethod
    def _get_match_interpretation(score: float) -> str:
        """
        Convert a numerical job match score into a human-readable interpretation.

        This feedback helps the user understand how closely their profile
        aligns with the job and what that alignment means qualitatively.

        Args:
            score (float): The total match score (0 to 100).

        Returns:
            str: Interpretation string with emoji and guidance.
        """

        score = round(score, 1)

        if score >= 90:
            return "🎯 Excellent Match - Strong alignment with all key requirements and preferences"
        elif score >= 80:
            return "🌟 Very Strong Match - Meets most requirements and aligns well with preferences"
        elif score >= 70:
            return "👍 Strong Match - Good overall fit with some areas for improvement"
        elif score >= 60:
            return "💡 Good Potential - Matches key criteria but consider enhancing some areas"
        elif score >= 50:
            return "🤔 Moderate Match - Partial alignment, might require additional qualifications"
        elif score >= 40:
            return "📉 Fair Match - Some relevant aspects but significant gaps exist"
        else:
            return "⚠️ Low Match - Limited alignment with position requirements"

    @staticmethod
    def _get_improvement_suggestions(scores: dict) -> list[str]:
        """
        Provide targeted suggestions for improving job match potential.

        Based on the component scores (skills, education, location, etc.),
        this method generates a list of recommendations to help the user
        increase their compatibility with more job opportunities.

        Args:
            scores (dict): Score breakdown by category.

        Returns:
            list[str]: List of actionable suggestions.
        """

        suggestions = []
        if scores['skills'] < 70:
            suggestions.append("Develop skills mentioned in job requirements")
        if scores['education'] < 50:
            suggestions.append("Consider additional certifications or education")
        if scores['location'] < 100:
            suggestions.append("Expand your preferred locations for more opportunities")
        return suggestions

    @error_handler
    async def advanced_job_search(self, filters: dict) -> list[Job]:
        """
        Perform an advanced job search using a combination of keyword, location, profile-based defaults, and job-specific filters.

        This method supports extensive filtering options including keyword matching, geo-radius queries, remote preference,
        salary range, experience level, job types, industries, education requirements, and job posting recency.
        If the `user_id` is provided and `override_profile` is not set, filters are supplemented with defaults from the user's profile.

        Parameters:
        ----------
        filters : dict
            A dictionary containing the search filters. Supported keys include:

            - keywords: list[str]
                Keywords to match in job title, description, or company name.
            - location_radius: tuple[float, float, int]
                Tuple of (latitude, longitude, radius_km) for geo-based proximity filtering.
            - locations: list[str]
                List of cities or provinces to include in the search.
            - experience_levels: list[str]
                Experience level filters such as ['entry', 'mid', 'senior'].
            - min_salary: int
                Minimum salary expectation.
            - max_salary: int
                Optional maximum salary expectation.
            - job_types: list[str]
                Types of employment like ['FULL_TIME', 'CONTRACT'].
            - company_size: str
                One of ['small', 'medium', 'large'] based on employee count.
            - industries: list[str]
                Industry tags to filter relevant job categories.
            - education_levels: list[str]
                Minimum education level required (e.g., 'Matric', 'Bachelor’s Degree').
            - remote: bool
                If True, include only remote/hybrid jobs.
            - posting_date: str
                Posting age filter. Options: 'last_week', 'last_month', 'last_3months'.
            - limit: int
                Optional limit on the number of results returned (max: 1000).
            - user_id: str
                If provided, loads profile defaults to supplement missing filters.
            - override_profile: bool
                If True, skips profile-based filter suggestions.

        Returns:
        -------
        list[Job]
            A list of `Job` objects matching the search criteria, sorted by relevance, feature status, and recent posting.

        Notes:
        -----
        - Profile-based filters help personalize results if `user_id` is included.
        - Geo search requires PostGIS support and properly indexed `geo_location` fields.
        - The method applies defensive defaults for missing or incomplete filters.
        - Job results are ordered by featured status, date posted, and application volume.
        """

        with self.get_session() as session:
            profile = session.query(JobSeekerProfileORM).get(filters.get('user_id'))

            # Set default filters from profile
            if profile and not filters.get('override_profile'):
                if not filters.get('locations') and profile.locations_of_interest:
                    filters['locations'] = profile.locations_of_interest
                if not filters.get('industries') and profile.industries_of_interest:
                    filters['industries'] = profile.industries_of_interest
                if not filters.get('remote') and profile.remote_preference:
                    filters['remote'] = True

            query = session.query(JobsORM).join(CompanyORM)

            # Keyword Search
            if filters.get('keywords'):
                keyword_conds = []
                for keyword in filters['keywords']:
                    kw_pattern = f"%{keyword}%"
                    keyword_conds.extend([
                        JobsORM.title.ilike(kw_pattern),
                        JobsORM.description.ilike(kw_pattern),
                        CompanyORM.name.ilike(kw_pattern)
                    ])
                query = query.filter(or_(*keyword_conds))

            # Location Filters
            location_filters = []
            if filters.get('location_radius'):
                lat, lng, radius_km = filters['location_radius']
                query = query.filter(
                    func.ST_DWithin(
                        JobsORM.geo_location,
                        func.ST_MakePoint(lng, lat),
                        radius_km * 1000  # Convert km to meters
                    )
                )
            if filters.get('locations'):
                location_filters = [
                    JobsORM.city.ilike(f"%{loc}%") |
                    JobsORM.province.ilike(f"%{loc}%")
                    for loc in filters['locations']
                ]
                query = query.filter(or_(*location_filters))

            # Company Filters
            if filters.get('company_size'):
                size_map = {
                    'small': (1, 50),
                    'medium': (51, 200),
                    'large': (201, 10000)
                }
                min_e, max_e = size_map.get(filters['company_size'], (0, 10000))
                query = query.filter(CompanyORM.employee_count.between(min_e, max_e))


            # Job Attributes
            if filters.get('industries'):
                query = query.filter(JobsORM.category.op('&&')(filters['industries']))

            if filters.get('remote'):
                query = query.filter(JobsORM.remote_policy.in_(["REMOTE", "HYBRID"]))

            if filters.get('experience_levels'):
                query = query.filter(JobsORM.experience_level.in_(filters['experience_levels']))

            if filters.get('job_types'):
                query = query.filter(JobsORM.position_type.in_(filters['job_types']))

            # Salary Filter
            if filters.get('min_salary') or filters.get('max_salary'):
                min_sal = filters.get('min_salary', 0)
                max_sal = filters.get('max_salary', 10 ** 6)
                query = query.filter(
                    JobsORM.salary_min >= min_sal,
                    JobsORM.salary_max <= max_sal,
                    JobsORM.salary_confidential == False
                )

            # Education Filter
            if filters.get('education_levels'):
                edu_conds = [
                    JobsORM.education_requirements['minimum'].astext.in_(filters['education_levels'])
                ]
                query = query.filter(or_(*edu_conds))

            # Date Filters
            if filters.get('posting_date'):
                date_map = {
                    'last_week': 7,
                    'last_month': 30,
                    'last_3months': 90
                }
                days = date_map.get(filters['posting_date'], 30)
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                query = query.filter(JobsORM.posted_at >= cutoff_date)

            # Sorting and Pagination
            query = query.order_by(
                JobsORM.is_featured.desc(),
                JobsORM.posted_at.desc(),
                JobsORM.application_count.desc()
            )

            if filters.get('limit'):
                query = query.limit(min(filters['limit'], 1000))

            return [Job(**job.to_dict()) for job in query.all()]


    @error_handler
    async def validate_application_completeness(self, application: JobApplication) -> dict:
        """
        Validate a job application against the job's required criteria.

        This method checks the completeness and quality of an applicant's submission
        by verifying whether they have:
        - Submitted all required documents
        - Completed the associated questionnaire (if applicable)
        - Matched the required skills based on their CV

        Parameters:
        ----------
        application : JobApplication
            The job application object containing job ID, CV ID, attached documents,
            and any questionnaire answers submitted by the applicant.

        Returns:
        -------
        dict
            A dictionary containing:
            - `score` (int): A percentage score indicating how many required skills the applicant matches.
            - `missing` (list[str]): A list of messages detailing missing documents, unanswered questions, or unmatched skills.

        Notes:
        -----
        - The `score` is calculated only if both the job has required skills and the applicant has a CV.
        - If any required fields are incomplete or missing, they are listed in the `missing` array.
        - This function assumes the application model has `documents`, `questionnaire_answers`, `cv_id`, and `job_id` fields.
        """

        with self.get_session() as session:
            job = session.query(JobsORM).get(application.job_id)
            cv = session.query(JobSeekerCVORM).filter_by(cv_id=application.cv_id).first()

            result = {'score': 0, 'missing': []}

            # Document check
            required_docs = job.required_documents or []
            missing_docs = [doc for doc in required_docs if doc not in application.required_documents]
            if missing_docs:
                result['missing'].append(f"Missing documents: {', '.join(missing_docs)}")

            # Questionnaire check
            if job.required_questionnaire and not application.questionnaire_answers:
                result['missing'].append("Uncompleted questionnaire")

            # Skills match
            if cv and job.required_skills:
                matched_skills = set(cv.skills) & set(job.required_skills)
                result['score'] = int((len(matched_skills) / len(job.required_skills)) * 100)
                if len(matched_skills) < len(job.required_skills):
                    missing_skills = set(job.required_skills) - set(cv.skills)
                    result['missing'].append(f"Missing skills: {', '.join(missing_skills)}")

            return result

    @error_handler
    async def get_application_funnel_stats(self, job_id: str) -> ApplicationFunnelStats:
        """
        Retrieve key hiring pipeline metrics for a specific job post.

        This method calculates statistics related to the application funnel of a given job,
        including the number of candidates at each stage of the process (submitted, qualified,
        interviewed, hired, rejected), total job views, and the conversion rate from submission
        to hire.

        Parameters:
        ----------
        job_id : str
            The unique identifier of the job posting whose funnel metrics are to be retrieved.

        Returns:
        -------
        ApplicationFunnelStats
            A Pydantic model containing the following fields:
            - `views` (int): Total number of times the job posting has been viewed.
            - `started` (int): Number of candidates who started an application (submitted).
            - `completed` (int): Number of candidates who completed the application (equal to submitted in current implementation).
            - `qualified` (int): Number of candidates who passed the qualification screening.
            - `interviewed` (int): Number of candidates who were interviewed.
            - `hired` (int): Number of candidates hired for the position.
            - `rejected` (int): Number of candidates rejected.
            - `conversion_rate` (float): Percentage of submitted applicants who were hired.

        Notes:
        -----
        - This method assumes that all submitted applications are considered completed.
        - Conversion rate is calculated as `(hired / submitted) * 100`, rounded to one decimal.
        - If no applications are submitted, the conversion rate defaults to `0.0`.
        """

        with self.get_session() as session:
            # Get counts for each application stage
            stats = session.query(
                func.count(case((JobApplicationORM.application_stage == 'submitted', 1))).label('submitted'),
                func.count(case((JobApplicationORM.application_stage == 'qualified', 1))).label('qualified'),
                func.count(case((JobApplicationORM.application_stage == 'interviewed', 1))).label('interviewed'),
                func.count(case((JobApplicationORM.application_stage == 'hired', 1))).label('hired'),
                func.count(case((JobApplicationORM.application_stage == 'rejected', 1))).label('rejected')
            ).filter(JobApplicationORM.job_id == job_id).one()

            # Get view count separately
            view_count = session.query(JobsORM.view_count).filter_by(job_id=job_id).scalar() or 0

            # Unpack stats
            submitted = stats.submitted or 0
            qualified = stats.qualified or 0
            interviewed = stats.interviewed or 0
            hired = stats.hired or 0
            rejected = stats.rejected or 0

            # Compute conversion rate
            conversion_rate = round((hired / submitted * 100), 1) if submitted > 0 else 0

            return ApplicationFunnelStats(**{
                'views': view_count,
                'started': submitted,
                'completed': submitted,  # If all submitted are considered complete
                'qualified': qualified,
                'interviewed': interviewed,
                'hired': hired,
                'rejected': rejected,
                'conversion_rate': conversion_rate
            })


    @error_handler
    async def generate_application_review_summary(self, application_id: str) -> str:
        """
        Generate an AI-powered review summary of a job application using the DeepSeek API.

        This method uses applicant CV data and job requirements to formulate a structured prompt
        for an AI model, which returns a detailed review of the application. The summary includes
        matched skills, experience gaps, red flags, and suggested technical interview questions.

        Parameters:
        ----------
        application_id : str
            The unique identifier of the job application to analyze.

        Returns:
        -------
        str
            A structured summary containing:
            - Top 3 skill matches between the candidate and job requirements
            - Noted experience gaps relevant to the job
            - Potential red flags (if any)
            - 5 suggested technical interview questions

        Notes:
        -----
        - If the DeepSeek API is unreachable or returns an error, a fallback message is returned.
        - The method logs all API-related errors for monitoring purposes.
        """
        with self.get_session() as session:
            application = session.query(JobApplicationORM).get(application_id)
            cv = session.query(JobSeekerCVORM).filter_by(cv_id=application.cv_id).first()
            job = session.query(JobsORM).get(application.job_id)

            prompt = f"""
            Analyze this job application for {job.title} position:

            Candidate Skills: {cv.skills}
            Job Requirements: {job.required_skills}

            Experience Summary: {cv.experience}
            Education: {cv.education}

            Generate:
            1. Top 3 skill matches
            2. Experience gaps
            3. Potential red flags
            4. 5 technical interview questions
            """

            try:
                headers = {
                    "Authorization": f"Bearer {self.deepseek_api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": "deepseek-chat",
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }],
                    "temperature": 0.7
                }

                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']
                else:
                    self.logger.error(f"DeepSeek API Error: {response.text}")
                    return "Summary generation temporarily unavailable"

            except Exception as e:
                self.logger.error(f"DeepSeek summary failed: {str(e)}")
                return "Summary generation service unavailable"



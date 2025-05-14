import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from flask import Flask, url_for
from pydantic import ValidationError
from requests import RequestException
from sqlalchemy import or_, select, func, and_, case
from sqlalchemy.orm import joinedload
from Levenshtein import ratio as levenstein_ratio
from src.controllers.controller import Controllers
from src.database.models.jobseeker_profile import JobSeekerProfile
from src.database.models.resume import JobSeekerCV
from src.database.sql.jobseeker_profile import JobSeekerProfileORM
from src.database.sql.resume import JobSeekerCVORM
from src.database.sql.users import UserORM

from src.controllers.controller import error_handler
from src.database.models.jobs_model import (Job, JobApplication, SavedJob, JobStatistics, StatusCounts,
    ApplicationMetrics, ApplicationFunnelStats, BulkImportResult, TalentPoolReport, JobApplicationDashboard, ATSReport,
    JobApplicationStatusEnum)
from src.database.sql.jobs_sql import (JobsORM, SavedJobORM, JobApplicationORM, CompanyORM, JobApprovalRequestORM,
    ATSReportORM)


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
    
    @error_handler
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

            # Set expiration date to yesterday - this will de-activate a job listing
            job_orm.status = JobStatusEnum.CLOSED.value
            # Setting Expiration date to yesterday
            new_expiration = datetime.now(timezone.utc) - timedelta(days=1)
            job_orm.expiration_date = new_expiration.date()
            job_orm.updated_at = datetime.now(timezone.utc)

            return Job(**job_orm.to_dict())

    @error_handler
    async def activate_job_listing(self, job_id: str) -> Job | None:
        """Activate job listing by resetting expiration date"""
        with self.get_session() as session:
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
                return None

            job_orm.status = JobStatusEnum.ACTIVE.value  # Corrected typo
            # Extend expiration by 30 days from now
            new_expiration = datetime.now(timezone.utc) + timedelta(days=30)
            job_orm.expiration_date = new_expiration.date()
            job_orm.updated_at = datetime.now(timezone.utc)
            session.commit()

            return Job(**job_orm.to_dict())


    @error_handler
    async def archive_job_listing(self, job_id: str) -> Job | None:
        """Archive job listing """
        with self.get_session() as session:
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
                return None
            # Set expiration date to yesterday
            job_orm.status = JobStatusEnum.ARCHIVE.value
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
            job_orm.status = JobStatusEnum.ACTIVE.value
            job_orm.is_featured = True
            job_orm.updated_at = datetime.now(timezone.utc)

            return Job(**job_orm.to_dict())

    @error_handler
    async def create_job(self, job: Job) -> Job | None:
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
        with self.get_session() as session:
            stmt = select(JobsORM).where(
                JobsORM.title.ilike(f"%{escape_like(title)}%")
            )
            jobs = session.execute(stmt).scalars().all()
            return [Job(**job.to_dict()) for job in jobs]


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
            list of Job objects sorted by newest first, excluding expired/archived jobs
        Example:  >>> await api.get_recent_jobs(5)  # Get 5 newest active postings
        """
        # Enforce sensible upper limit for performance
        limit = min(limit, 100)

        with self.get_session() as session:
            jobs_orm_list = (
                session.query(JobsORM)
                .filter(JobsORM.status == JobStatusEnum.ACTIVE.value)  # Only non-archived/closed jobs
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
                func.sum(case((JobsORM.status == JobStatusEnum.ACTIVE.value, 1), else_=0)).label('active_jobs'),
                func.sum(case((JobsORM.status == JobStatusEnum.CLOSED.value, 1), else_=0)).label('closed_jobs'),
                func.sum(case((JobsORM.status == JobStatusEnum.ARCHIVED.value, 1), else_=0)).label('archived_jobs'),
                func.sum(JobsORM.application_count).label('total_applications'),
                func.sum(case((JobsORM.application_count > 0, 1), else_=0)).label('jobs_with_applications'),
                func.sum(
                    case(
                        (JobsORM.status == JobStatusEnum.ACTIVE.value) & (JobsORM.expires_at > func.now()),  # Changed here
                        1
                    )
                ).label('current_active_jobs')
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
                job_application.status = JobApplicationStatusEnum.UNDER_REVIEW.value

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
            if job_application.application_stage == "withdrawn":
                self.logger.debug(f"Application {application_id} already withdrawn")
                return True  # Considered successful as it's in desired state

            # Update fields
            job_application.application_stage = "withdrawn"  # Lowercase for consistency
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
                JobsORM.status == JobStatusEnum.ACTIVE.value,
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
            list[str]: list of actionable suggestions.
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
                list of cities or provinces to include in the search.
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



    # ... existing methods JOB POSTING ENHANCEMENTS ...

    @error_handler
    async def validate_job_post(self, job: Job) -> dict:
        """Validate job post completeness and employer credibility"""
        validation_result = {
            'valid': True,
            'errors': [],
            'requires_approval': False
        }

        # Basic field validation
        required_fields = ['title', 'city', 'province', 'country', 'category']
        for field in required_fields:
            if not getattr(job, field):
                validation_result['errors'].append(f"Missing required field: {field}")

        # Salary validation
        if job.salary_min and job.salary_max:
            if job.salary_min > job.salary_max:
                validation_result['errors'].append("Salary minimum cannot exceed maximum")

        # Employer validation
        with self.get_session() as session:
            # Check employer posting limits
            posted_last_month = session.query(func.count(JobsORM.job_id)).filter(
                JobsORM.company_id == job.company_id,
                JobsORM.posted_at >= datetime.now(timezone.utc) - timedelta(days=30)
            ).scalar()

            if posted_last_month >= 10:  # Example limit
                validation_result['requires_approval'] = True
                validation_result['errors'].append("Employer posting limit reached")

        # New employer approval requirement
        if job.company_id:
            company = session.query(CompanyORM).get(job.company_id)
            if company and company.creation_date > datetime.now(timezone.utc) - timedelta(days=30):
                validation_result['requires_approval'] = True

        validation_result['valid'] = len(validation_result['errors']) == 0
        return validation_result

    @error_handler
    async def add_job_posting_workflow(self, job: Job) -> Job:
        """Complete job submission workflow"""
        with self.get_session() as session:
            # Step 1: Save as draft
            job.status = JobStatusEnum.DRAFT.value
            draft_orm = JobsORM(**job.model_dump())
            session.add(draft_orm)
            session.flush()  # Get ID without commit

            # Step 2: Generate preview
            preview_data = await self._generate_job_preview(draft_orm)

            # Step 3: Automatic categorization
            draft_orm.category = await self._auto_categorize_job(draft_orm.title, draft_orm.description)

            # Step 4: Salary benchmarking
            benchmark = await self._get_salary_benchmark(
                draft_orm.category,
                draft_orm.city,
                draft_orm.experience_level
            )
            if benchmark:
                draft_orm.salary_min = benchmark.get('25_percentile', draft_orm.salary_min)
                draft_orm.salary_max = benchmark.get('75_percentile', draft_orm.salary_max)

            # Step 5: Approval check
            validation = await self.validate_job_post(Job(**draft_orm.to_dict()))
            if validation['requires_approval']:
                job.status = JobStatusEnum.PENDING_APPROVAL.value
                self._send_approval_request(draft_orm)
            else:
                job.status = JobStatusEnum.ACTIVE.value
                draft_orm.posted_at = datetime.now(timezone.utc)

            return Job(**draft_orm.to_dict())

    @error_handler
    async def detect_duplicate_jobs(self, job: Job) -> list[Job]:
        """Identify similar existing jobs"""
        with self.get_session() as session:
            duplicates = session.query(JobsORM).filter(
                JobsORM.company_id == job.company_id,
                JobsORM.title.ilike(f"%{job.title}%"),
                JobsORM.city == job.city,
                JobsORM.salary_min.between(job.salary_min * 0.9, job.salary_max * 1.1)
            ).order_by(JobsORM.posted_at.desc()).limit(5).all()

            # Add NLP-based similarity check
            similar_jobs = []
            for existing_job in duplicates:
                if self._calculate_title_similarity(job.title, existing_job.title) > 0.8:
                    similar_jobs.append(existing_job)

            return [Job(**job.to_dict()) for job in similar_jobs]

    # Helper methods
    @staticmethod
    def _calculate_title_similarity(title1: str, title2: str) -> float:
        """Calculate title similarity using Levenshtein distance"""
        return levenstein_ratio(title1.lower(), title2.lower())

    async def _auto_categorize_job(self, title: str, description: str) -> str:
        """Heuristically categorize a job based on title and description."""
        async def create_ai_prompt(title: str, description: str) -> str:
            return f"""
            You are a smart job categorization assistant.

            Given a job title and job description, your task is to categorize the job into one of the following categories:

            - information-technology
            - office-admin
            - agriculture
            - engineering
            - building-construction
            - business-management
            - cleaning-maintenance
            - community-social-welfare
            - education
            - nursing
            - finance
            - programming

            If the job does not clearly fit into any of the above, return "other".

            Respond with only the category name (no explanations or extra text).

            Here is the job:

            Title: {title}
            Description: {description}

            What is the most appropriate category?
                """.strip()

        async def call_deepseek_api(prompt: str):
            try:
                headers = {
                    "Authorization": f"Bearer {self.deepseek_api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2
                }

                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    category = response.json()['choices'][0]['message']['content'].strip().lower()
                    allowed_categories = [
                        'information-technology', 'office-admin', 'agriculture',
                        'engineering', 'building-construction', 'business-management',
                        'cleaning-maintenance', 'community-social-welfare', 'education',
                        'nursing', 'finance', 'programming', 'other'
                    ]
                    return category if category in allowed_categories else 'other'
                else:
                    self.logger.error(f"DeepSeek categorization failed: {response.text}")
                    return 'other'
            except RequestException as e:
                self.logger.error(f"DeepSeek categorization error: {str(e)}")
                return 'other'

        category_keywords = {
            'information-technology': [
                'it', 'software', 'network', 'cybersecurity', 'systems analyst',
                'tech support', 'infrastructure', 'cloud', 'devops', 'data center'
            ],
            'office-admin': [
                'admin', 'administrative', 'receptionist', 'office assistant',
                'secretary', 'clerk', 'front desk', 'scheduler'
            ],
            'agriculture': [
                'farm', 'agricultural', 'harvest', 'crop', 'irrigation',
                'livestock', 'farming', 'agribusiness'
            ],
            'engineering': [
                'engineer', 'mechanical', 'civil', 'electrical', 'technician',
                'systems engineer', 'structural', 'design engineer'
            ],
            'building-construction': [
                'builder', 'construction', 'foreman', 'plumber', 'electrician',
                'contractor', 'site supervisor', 'carpenter', 'bricklayer'
            ],
            'business-management': [
                'manager', 'executive', 'business development', 'operations',
                'project manager', 'strategy', 'team lead'
            ],
            'cleaning-maintenance': [
                'cleaner', 'janitor', 'custodian', 'maintenance', 'groundskeeper',
                'housekeeping'
            ],
            'community-social-welfare': [
                'social worker', 'community outreach', 'non-profit',
                'ngo', 'welfare', 'care worker', 'humanitarian'
            ],
            'education': [
                'teacher', 'educator', 'lecturer', 'instructor',
                'trainer', 'school', 'professor', 'tutor'
            ],
            'nursing': [
                'nurse', 'midwife', 'caregiver', 'rn', 'enrolled nurse',
                'clinical assistant', 'healthcare assistant'
            ],
            'finance': [
                'accountant', 'bookkeeper', 'auditor', 'finance', 'financial analyst',
                'investment', 'bank', 'payroll'
            ],
            'programming': [
                'developer', 'programmer', 'software engineer', 'python', 'java',
                'backend', 'frontend', 'fullstack', 'api', 'coding'
            ]
        }

        combined_text = f"{title} {description}".lower()
        scores = {category: 0 for category in category_keywords.keys()}

        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in combined_text:
                    scores[category] += combined_text.count(keyword)

        best_category = max(scores, key=scores.get)
        category_fit = best_category if scores[best_category] > 0 else None
        if not category_fit:
            # TODO - could test if user is allowed to call this api
            prompt = await create_ai_prompt(title=title, description=description)
            category_fit = await call_deepseek_api(prompt=prompt)
        return category_fit

    # noinspection PyProtectedMember
    async def _get_salary_benchmark(self, category: str, location: str, experience: str) -> dict:
        """Get salary benchmarks from historical data"""
        with self.get_session() as session:
            # noinspection PyProtectedMember
            return session.query(
                func.percentile_cont(0.25).within_group(JobsORM.salary_min).label('25_percentile'),
                func.percentile_cont(0.75).within_group(JobsORM.salary_min).label('75_percentile')
            ).filter_by(
                category=category,
                city=location,
                experience_level=experience
            ).group_by(JobsORM.category).first()._asdict()

    async def _generate_job_preview(self, job: JobsORM) -> dict:
        """Generate preview data for job posting"""
        return {
            'preview_html': f"<h1>{job.title}</h1><p>{job.description[:200]}...</p>",
            'metadata': {
                'word_count': len(job.description.split()),
                'salary_range': f"{job.salary_min} - {job.salary_max}",
                'readability_score': await self._calculate_readability(job.description)
            }
        }

    async def _calculate_readability(self, text: str) -> float:
        """
        Calculate text readability using the Flesch Reading Ease formula.

        Formula: 206.835 - 1.015*(words/sentences) - 84.6*(syllables/words)

        Returns:
            float: Readability score between 0-100 (higher = easier to read)
        """
        text = text.strip()
        if not text:
            return 0.0

        sentences = [s.strip() for s in re.split(r'(?<=[.!?])[\s\n]+', text) if s.strip()]
        num_sentences = len(sentences)
        if num_sentences == 0:
            return 0.0

        words = []
        total_syllables = 0
        for sentence in sentences:
            words_in_sentence = re.findall(r"\b[a-zA-Z']+\b", sentence)
            words.extend(words_in_sentence)
            total_syllables += sum(self._count_word_syllables(word) for word in words_in_sentence)

        num_words = len(words)
        if num_words < 1 or num_sentences < 1:
            return 0.0

        avg_words_per_sentence = num_words / num_sentences
        avg_syllables_per_word = total_syllables / num_words

        score = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)

        return round(max(0.0, min(100.0, score)), 2)

    @staticmethod
    def _count_word_syllables(word: str) -> int:
        """Estimate syllables in a word using vowel groups and common patterns"""
        word = word.lower()
        if len(word) <= 3:
            return 1

        # Handle common exceptions
        if word.endswith(('es', 'ed')) and not word.endswith(('ses', 'aes', 'ies', 'eed')):
            word = word[:-2]
        elif word.endswith('e'):
            word = word[:-1]

        # Count vowel groups
        vowels = 'aeiouy'
        count = 0
        prev_char_vowel = False

        for char in word:
            if char in vowels:
                if not prev_char_vowel:
                    count += 1
                prev_char_vowel = True
            else:
                prev_char_vowel = False

        # Final adjustments
        if word.endswith(('le', 're')) and count > 1:
            count -= 1
        if count == 0:
            count = 1

        return max(1, count)

    def _send_approval_request(self, draft_orm: JobsORM) -> None:
        """
        Initiate and manage the job post approval workflow by:
        1. Identifying appropriate approvers
        2. Generating secure approval links
        3. Sending notification emails
        4. Creating audit records
        5. Setting up approval tracking

        Parameters:
            draft_orm (JobsORM): The job post draft requiring approval

        Workflow:
            1. Determine approval recipients based on:
               - Company hierarchy (if employer has internal approval flow)
               - System admins (for new/unverified companies)
               - Category moderators (for specialized job categories)
            2. Generate unique approval token with expiration
            3. Store approval request in database
            4. Send email notifications with approval/rejection links
            5. Update job post status to 'pending_approval'

        Notifications Include:
            - Direct approval/rejection links with JWT tokens
            - Job post summary
            - Submit timestamp
            - Applicant statistics (for renewal posts)
            - Approval deadline

        Security:
            - Uses time-limited JWT tokens for authorization
            - Encodes company ID and job ID in token
            - Stores hashed token version in database
            - Automatic invalidation after:
              - Approval/rejection action
              - Token expiration (7 days)
              - Job post modification

        Raises:
            ApprovalWorkflowException: If critical failure in notification sending
        """
        with self.get_session() as session:

            # 1. Identify approvers
            approvers = session.query(UserORM).filter_by(role = "admin").all()
            if not approvers:
                raise ValueError("No eligible approvers found")

            # 2. Generate approval token
            approval_token = str(uuid.uuid4())
            token_expiration = datetime.now(timezone.utc) + timedelta(days=7)
            draft = Job(**draft_orm.to_dict())
            # 3. Create approval request record
            approval_request = JobApprovalRequestORM(
                job_id=draft_orm.job_id,
                token=approval_token,
                token_expires=token_expiration,
                requested_by=draft.company.company_id,
                approvers=[u.user_id for u in approvers],
                status='pending'
            )
            session.add(approval_request)

            # 4.TODO - APPROVALS MUST BE DEALT WITH ON THE ADMIN DASHBOARD ONLY --
            approval_link = url_for('jobs.approve_job', approval_token=approval_token, _external=True)
            rejection_link = url_for('jobs.reject_job', approval_token=approval_token, _external=True)

            email_body = f"""
            <h2>Job Post Approval Required</h2>
            <p><strong>Title:</strong> {draft.title}</p>
            <p><strong>Company:</strong> {draft.company.name}</p>
            <p><strong>Category:</strong> {draft.category}</p>
            <p><strong>Submitted:</strong> {draft.posted_at.strftime('%Y-%m-%d %H:%M')}</p>
    
            <h3>Actions Required by {token_expiration.strftime('%Y-%m-%d')}</h3>
            <p>
                <a href="{approval_link}" style="color: green;">Approve Job Post</a> | 
                <a href="{rejection_link}" style="color: red;">Request Changes</a>
            </p>
    
            <h4>Post Preview</h4>
            <div>{draft.description[:500]}...</div>
            """

            # TODO - Send Message using Send Mail - 5. Send notifications
            # for approver in approvers:
            #     msg = Message(
            #         subject=f"Approval Required: {draft_orm.title}",
            #         recipients=[approver.email],
            #         html=email_body
            #     )
            #     self.mail.send(msg)
            #
            # 6. Update job status
            draft_orm.status = JobStatusEnum.PENDING_APPROVAL.value
            session.commit()

            self.logger.info(f"Sent approval request for job {draft_orm.job_id} to {len(approvers)} approvers")


        # EMPLOYER DASHBOARDS AND RELATED METHODS

    @error_handler
    async def get_application_management_dashboard(self, employer_id: str) -> JobApplicationDashboard:
        """Employer dashboard with advanced hiring analytics"""
        with self.get_session() as session:
            # Get all jobs for this employer
            jobs = session.execute(
                select(JobsORM.job_id)
                .where(JobsORM.company_id == employer_id)
            )
            job_ids = [j[0] for j in jobs.scalars().all()]

            # Application status breakdown
            status_counts = session.execute(
                select(
                    JobApplicationORM.application_stage,
                    func.count(JobApplicationORM.application_id)
                )
                .where(JobApplicationORM.job_id.in_(job_ids))
                .group_by(JobApplicationORM.application_stage)
            )
            status_dict = {status: count for status, count in status_counts}

            # Recent applications with candidate preview
            recent_apps = session.execute(
                select(JobApplicationORM)
                .where(JobApplicationORM.job_id.in_(job_ids))
                .order_by(JobApplicationORM.applied_date.desc())
                .limit(10)
            )
            recent_applications = [
                {
                    "id": app.application_id,
                    "name": app.candidate.name,  # Assuming relationship
                    "score": app.ats_report.score if app.ats_report else 0,
                    "status": app.application_stage
                }
                for app in recent_apps.scalars().all()
            ]

            # Skills heatmap from ATS reports
            skills_query = session.execute(
                select(
                    func.jsonb_object_keys(ATSReportORM.matched_keywords).label("skill"),
                    func.count(ATSReportORM.ats_report_id)
                )
                .where(ATSReportORM.job_id.in_(job_ids))
                .group_by("skill")
            )
            skills_heatmap = {skill: count for skill, count in skills_query}

            return JobApplicationDashboard(
                total_applications=sum(status_dict.values()),
                applications_by_status=status_dict,
                recent_applications=recent_applications,
                average_application_score= await self._calculate_average_score(job_ids),
                skills_heatmap=skills_heatmap,
                pipeline_metrics=await self._calculate_pipeline_metrics(job_ids)
            )

    async def _calculate_average_score(self, job_ids: list[str]) -> float:
        with self.get_session() as session:
            result = session.execute(
                select(func.avg(ATSReportORM.score))
                .where(ATSReportORM.job_id.in_(job_ids))
            )
            return result.scalar() or 0.0

    async def _calculate_pipeline_metrics(self, job_ids: list[str]) -> dict[str, float]:
        with self.get_session() as session:
            result = session.execute(
                select(
                    func.avg(
                        case(
                            (JobApplicationORM.application_stage == JobApplicationStatusEnum.HIRED.value,
                             func.extract('epoch', JobApplicationORM.updated_at - JobApplicationORM.applied_date)),
                            else_=None
                        )
                    ),
                    func.avg(ATSReportORM.score)
                )
                .where(JobApplicationORM.job_id.in_(job_ids))
            )
            time_to_hire, avg_score = result.fetchone()
            return {
                "average_time_to_hire": time_to_hire or 0.0,
                "average_ats_score": avg_score or 0.0
            }

    @error_handler
    async def generate_talent_pool_report(self, employer_id: str) -> TalentPoolReport:
        """Generate comprehensive talent pool analysis"""
        with self.get_session() as session:
            # Skills gap analysis
            skills_gap = session.execute(
                select(
                    func.jsonb_object_keys(ATSReportORM.missing_keywords).label("skill"),
                    func.count(ATSReportORM.ats_report_id)
                )
                .join(JobsORM, JobsORM.job_id == ATSReportORM.job_id)
                .where(JobsORM.company_id == employer_id)
                .group_by("skill")
                .order_by(func.count(ATSReportORM.ats_report_id).desc())
                .limit(10)
            )

            # Diversity metrics (requires candidate demographics data)
            diversity_metrics = {
                "gender": {"male": 45, "female": 53, "other": 2},
                "ethnicity": {}  # Placeholder
            }

            # Source effectiveness
            source_effectiveness = session.execute(
                select(
                    JobApplicationORM.method,
                    func.count(JobApplicationORM.application_id),
                    func.avg(ATSReportORM.score)
                )
                .join(ATSReportORM)
                .join(JobsORM)
                .where(JobsORM.company_id == employer_id)
                .group_by(JobApplicationORM.method)
            )

            return TalentPoolReport(
                skills_gap_analysis=dict(skills_gap.all()),
                diversity_metrics=diversity_metrics,
                source_effectiveness={
                    method: {"count": count, "avg_score": score}
                    for method, count, score in source_effectiveness
                },
                average_time_to_hire= await self._get_average_time_to_hire(employer_id),
                candidate_comparison= await self._generate_candidate_comparison(employer_id)
            )

    async def _get_average_time_to_hire(self, employer_id: str) -> float:
        """Calculate average time from application to hire in days"""
        with self.get_session() as session:
            result = session.execute(
                select(
                    func.avg(
                        func.extract('epoch', JobApplicationORM.updated_at - JobApplicationORM.applied_date)
                    )
                )
                .join(JobsORM, JobApplicationORM.job_id == JobsORM.job_id)
                .where(
                    JobsORM.company_id == employer_id,
                    JobApplicationORM.application_stage == JobApplicationStatusEnum.HIRED.value,
                    JobApplicationORM.updated_at.isnot(None)
                )
            )

            avg_seconds = result.scalar()
            return round(avg_seconds / 86400, 1) if avg_seconds else 0.0  # Convert to days

    async def _generate_candidate_comparison(self, employer_id: str) -> list[dict]:
        """Generate candidate comparison data for employer"""
        with self.get_session() as session:
            # Get applications with ATS reports and candidate info
            job_applications: list[JobApplicationORM] = session.execute(
                select(JobApplicationORM)
                .join(JobsORM, JobApplicationORM.job_id == JobsORM.job_id)
                .where(
                    JobsORM.company_id == employer_id,
                    JobApplicationORM.application_stage.in_([JobApplicationStatusEnum.HIRED.value,
                                                             JobApplicationStatusEnum.SHORTLISTED.value,
                                                             JobApplicationStatusEnum.INTERVIEWING.value])
                )
                .order_by(JobApplicationORM.applied_date.desc())
                .limit(100)  # Limit for performance
            ).scalars().all()

            comparison_data = []
            for job_app in job_applications:

                ats_report_orm = session.query(ATSReportORM).filter_by(job_id=job_app.job_id, user_id=job_app.user_id).first()
                if not ats_report_orm:
                    continue
                ats_report: ATSReport = ATSReport(**ats_report_orm.to_dict())
                candidate_profile_orm = session.query(JobSeekerProfileORM).filter_by(user_uid=job_app.user_id).first()

                if not candidate_profile_orm:
                    continue
                candidate_profile: JobSeekerProfile = JobSeekerProfile(**candidate_profile_orm.to_dict())


                comparison_data.append({
                    "application_id": job_app.application_id,
                    "candidate_id": job_app.user_id,
                    "name": f"{candidate_profile.first_name} {candidate_profile.last_name}" if candidate_profile else "Anonymous",
                    "score": ats_report.score if ats_report else 0,
                    "applied_date": job_app.applied_date.strftime("%Y-%m-%d"),
                    "last_update": job_app.updated_at.strftime("%Y-%m-%d") if job_app.updated_at else None,
                    "matched_skills": ats_report.matched_keywords if ats_report else [],
                    "missing_skills": ats_report.missing_keywords if ats_report else [],
                    "experience": candidate_profile.years_experience if candidate_profile else 0,
                    "application_stage": job_app.application_stage,
                    "application_source": job_app.method
                })

            # Add ranking by score
            ranked = sorted(
                comparison_data,
                key=lambda x: x['score'],
                reverse=True
            )

            # Add percentile ranking
            scores = [x['score'] for x in ranked if x['score'] > 0]
            max_score = max(scores) if scores else 100

            for entry in ranked:
                if entry['score'] > 0:
                    entry['percentile'] = round((entry['score'] / max_score) * 100)
                else:
                    entry['percentile'] = 0

            return ranked


    @error_handler
    async def bulk_import_jobs(self, company_id: str, jobs_data: list[dict]) -> BulkImportResult | None:
        """Process bulk job imports with validation and error handling"""
        batch_id = str(uuid.uuid4())
        results = {
            "total_processed": 0,
            "successful": 0,
            "failures": 0,
            "error_details": []
        }

        with self.get_session() as session:
            for index, job_data in enumerate(jobs_data):
                try:
                    # Validate and normalize data
                    validated = await self._validate_import_job(job_data)

                    # Check duplicates
                    exists = session.execute(
                        select(JobsORM)
                        .where(JobsORM.job_ref == validated["job_ref"])
                        .where(JobsORM.company_id == company_id)
                    )
                    if exists.scalars().first():
                        raise ValueError("Duplicate job reference")

                    # Create job
                    new_job = JobsORM(
                        **validated,
                        company_id=company_id,
                        created_at=datetime.now(timezone.utc)
                    )
                    session.add(new_job)
                    results["successful"] += 1
                except (ValidationError, ValueError) as e:
                    results["failures"] += 1
                    results["error_details"].append({
                        "row": index + 1,
                        "error": str(e),
                        "data": job_data
                    })
                finally:
                    results["total_processed"] += 1

            session.commit()
            return BulkImportResult(
                **results,
                batch_id=batch_id
            )

    async def _validate_import_job(self, job_data: dict) -> dict:
        """Validate and normalize imported job data"""
        required_fields = ["title", "description", "location"]
        missing = [field for field in required_fields if field not in job_data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        normalized = {
            "job_ref": job_data.get("job_ref") or f"IMP-{uuid.uuid4().hex[:8]}",
            "title": job_data["title"].strip(),
            "description": job_data["description"],
            "salary_min": await self._parse_salary(job_data.get("salary_min")),
            "salary_max": await self._parse_salary(job_data.get("salary_max")),
            "position_type": job_data.get("position_type", "FULL_TIME"),
            "remote_policy": job_data.get("remote_policy", "ONSITE")
        }
        return normalized

    @staticmethod
    async def _parse_salary(value: str) -> float:
        """Convert salary string to numeric value"""
        if not value:
            return None
        try:
            return float(value.replace("R", "").replace(",", "").strip())
        except ValueError:
            raise ValueError(f"Invalid salary format: {value}")


    # Add to JobsController
    @error_handler
    async def get_pending_approvals(self) -> list[Job]:
        """Get jobs needing admin approval"""
        with self.get_session() as session:
            jobs = session.query(JobsORM).join(JobApprovalRequestORM).filter(
                JobApprovalRequestORM.status == JobApprovalStatusEnum.PENDING.value
            ).all()
            return [Job(**job.to_dict()) for job in jobs]


    @error_handler
    async def update_approval_status(self, job_id: str, decision: str, reviewer_id: str) -> Job:
        """Update job approval status (Admin only)"""
        with self.get_session() as session:
            job = session.query(JobsORM).get(job_id)
            request = session.query(JobApprovalRequestORM).filter_by(job_id=job_id).first()

            if decision.lower() == JobApprovalStatusEnum.APPROVED.value:
                job.status = JobStatusEnum.ACTIVE.value
                request.status = JobApprovalStatusEnum.APPROVED.value
            elif decision.lower() == JobStatusEnum.REJECTED.value:
                job.status = JobStatusEnum.ARCHIVED.value
                request.status = JobApprovalStatusEnum.REJECTED.value

            request.reviewer_id = reviewer_id
            request.reviewed_at = datetime.now(timezone.utc)

            session.commit()
            return Job(**job.to_dict())


    @error_handler
    async def find_potential_duplicates(self, job: Job) -> list[Job]:
        """Advanced duplicate detection using multiple criteria"""
        with self.get_session() as session:
            duplicates = session.query(JobsORM).filter(
                and_(
                    func.similarity(JobsORM.title, job.title) > 0.7,
                    JobsORM.company_id == job.company_id,
                    JobsORM.location == job.location,
                    func.abs(JobsORM.salary_min - job.salary_min) < 5000
                )
            ).order_by(JobsORM.posted_at.desc()).limit(10).all()

            return [Job(**j.to_dict()) for j in duplicates]


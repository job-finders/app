import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from flask import Flask
from sqlalchemy import or_, desc, String
from sqlalchemy import select, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import cast
from sqlalchemy.sql.operators import and_

from src.controllers.controller import Controllers
from src.controllers.controller import error_handler
from src.database.models.jobs_model import (Job, JobApplication, JobStatusEnum, JobCategory)
from src.database.models.jobseeker_profile import JobSeekerProfile
from src.database.models.resume import JobSeekerCV
from src.database.sql import escape_like
from src.database.sql.company import CompanyORM
from src.database.sql.employer import EmployerORM
from src.database.sql.jobs_sql import (JobsORM, SavedJobORM, JobApplicationORM, JobCategoryORM)
from src.database.sql.jobseeker_profile import JobSeekerProfileORM
from src.database.sql.resume import JobSeekerCVORM


# noinspection DuplicatedCode
class JobsSearchController(Controllers):
    """
    Summary Line
    
        Keyword arguments:
        argument -- description
        Return: return_description
    """
    
    
    def __init__(self, factory):
        super().__init__(factory)

    def init_app(self, app: Flask):
        super().init_app(app=app)


    @error_handler
    async def get_all_jobs(self,
                           page: int = 1,
                           page_size: int = 20) -> dict:
        """Paginated list of active jobs, with featured jobs preferred"""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Enforce reasonable limits

        with self.get_session() as session:
            query = session.query(JobsORM).filter(JobsORM.status == JobStatusEnum.ACTIVE.value)

            total_jobs = query.count()

            offset = (page - 1) * page_size
            jobs_orm_list = (
                query.order_by(JobsORM.is_featured.desc(), JobsORM.created_at.desc())
                    .offset(offset)
                    .limit(page_size)
                    .all()
            )

            jobs = [Job(**job.to_dict()) for job in jobs_orm_list if job]
            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0
            return {
                "page": page,
                "page_size": page_size,
                "total_jobs": total_jobs,
                "total_pages": total_pages,
                "jobs": jobs,
            }

    @error_handler
    async def search_jobs(self,
                          keyword: str = '',
                          page: int = 1,
                          page_size: int = 25) -> dict[str, str | int | list[Job]]:

        """Search jobs by keyword in title or description with pagination."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Enforce reasonable limits
        with self.get_session() as session:
            query = session.query(JobsORM).filter(
                JobsORM.status == JobStatusEnum.ACTIVE.value,
                or_(
                    JobsORM.title.ilike(f'%{keyword}%'),
                    JobsORM.description.ilike(f'%{keyword}%')
                )
            )
            
            total_jobs = query.count()

            offset = (page - 1) * page_size

            jobs_orm_list = (
                query.order_by(JobsORM.is_featured.desc(), JobsORM.created_at.desc())
                    .offset(offset)
                    .limit(page_size)
                    .all()
            )

            jobs: list[Job] =  [Job(**job.to_dict()) for job in jobs_orm_list if job]
            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0

            return {
                "page": page,
                "page_size": page_size,
                "total_jobs": total_jobs,
                "total_pages": total_pages,
                "jobs": jobs}

    @error_handler
    async def list_job_categories(self) -> list[JobCategory]:
        """
        Returns a list of job categories along with their associated jobs.
        """
        with self.get_session() as session:
            category_orm_list: list[JobCategoryORM] = (
                session.query(JobCategoryORM)
                .options(joinedload(JobCategoryORM.jobs))
                .all()
            )
            return [JobCategory(**category_orm.to_dict(include_jobs=True)) for category_orm in category_orm_list]

    @error_handler
    async def search_jobs_by_category(self, category: str, page: int = 1, page_size: int = 25) -> dict:
        """Search jobs by category with pagination, filtered to active and featured preferred."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Enforce reasonable limits
        with self.get_session() as session:
            # Get category ORM instance (single object)
            category_orm = session.query(JobCategoryORM).filter(
                JobCategoryORM.name.ilike(f'%{category}%')
            ).first()  # Get first matching category

            if not category_orm:
                # Return empty result if no category found
                return {
                    "jobs": [],
                    "total_jobs": 0,
                    "total_pages": 0,
                    "page": page,
                    "page_size": page_size
                }

            # Convert ORM to Pydantic model
            category_model = JobCategory(**category_orm.to_dict())

            base_query = session.query(JobsORM).filter(
                JobsORM.status == JobStatusEnum.ACTIVE.value,
                JobsORM.category_id == category_model.category_id
            )

            total_jobs = base_query.count()
            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0
            offset = (page - 1) * page_size

            jobs_orm_list = (
                base_query.order_by(JobsORM.is_featured.desc(), JobsORM.created_at.desc())
                .offset(offset)
                .limit(page_size)
                .all()
            )

            return {
                "jobs": [Job(**job.to_dict()) for job in jobs_orm_list],
                "total_jobs": total_jobs,
                "total_pages": total_pages,
                "page": page,
                "page_size": page_size
            }
            
    @error_handler
    async def get_job_by_id(self, job_id: str) -> Job | None:
        """Retrieve a single active job by its ID."""
        with self.get_session() as session:
            job_orm = session.query(JobsORM).filter(
                JobsORM.job_id == job_id,
                JobsORM.status == JobStatusEnum.ACTIVE.value
            ).first()
            return Job(**job_orm.to_dict()) if job_orm else None
    
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
    async def archive_job_listing(self, job_id: str) -> Job | None:
        """Archive job listing """
        with self.get_session() as session:
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
                return None
            # Set expiration date to yesterday
            job_orm.status = JobStatusEnum.ARCHIVED.value
            job_orm.expiration_date = datetime.now(timezone.utc).date() - timedelta(days=1)
            job_orm.updated_at = datetime.now(timezone.utc)

            return Job(**job_orm.to_dict())

    @error_handler
    async def get_featured_jobs(self, page: int = 1, page_size: int = 25) -> dict:
        """Retrieve paginated featured job listings."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Enforce reasonable limits

        with self.get_session() as session:
            query = session.query(JobsORM).filter(
                JobsORM.is_featured.is_(True),
                JobsORM.status == JobStatusEnum.ACTIVE.value
            ).order_by(JobsORM.updated_at.desc())

            total_jobs = query.count()
            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0


            jobs_orm_list = query.offset((page - 1) * page_size).limit(page_size).all()

            jobs = [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list]

            return {
                'jobs': jobs,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'total_jobs': total_jobs
            }

    @error_handler
    async def get_jobs_by_title(
            self,
            title: str,
            page: int = 1,
            page_size: int = 25,
    ) -> dict:
        # Input validation
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Enforce reasonable limits

        with self.get_session() as session:
            # Base query
            query = select(JobsORM).where(
                JobsORM.status == JobStatusEnum.ACTIVE.value
            )

            # Add title filtering only if title is provided
            if title.strip():
                escaped_title = escape_like(title)
                # Use full-text search if available, otherwise suffix-only search
                query = query.where(
                    JobsORM.title.ilike(f"{escaped_title}%", escape='\\')  # Trailing wildcard only
                )

            # Eager load relationships
            query = query.options(
                joinedload(JobsORM.company),
                joinedload(JobsORM.category)
            ).order_by(
                func.similarity(JobsORM.title, title).desc(),
                JobsORM.is_featured.desc(),
                JobsORM.posted_at.desc()
            )

            # Get paginated results
            total_jobs = session.scalar(select(func.count()).select_from(query.subquery()))
            jobs = session.scalars(
                query.offset((page - 1) * page_size)
                .limit(page_size)
            ).unique().all()

            # Calculate total pages
            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0

            return {
                "jobs": [Job(**job.to_dict()) for job in jobs],
                "total_jobs": total_jobs,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

    @error_handler
    async def get_jobs_by_qualification(self,qualification: str,
        qualification_types: Optional[list[str]] = None,
        page: int = 1,
        page_size: int = 25) -> dict:

        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Enforce reasonable limits

        if qualification_types is None:
            qualification_types = [
                "matric", "diploma", "bachelor", "honours", "masters", "phd",
                "certificate", "trade_certificate"
            ]

        search_pattern = f"%{qualification}%"
        with self.get_session() as session:
            conditions = [
                JobsORM.education_requirements[q_type].astext.ilike(search_pattern)
                for q_type in qualification_types
            ]
            stmt = select(JobsORM).where(
                or_(*conditions),
                JobsORM.status == JobStatusEnum.ACTIVE.value
            )

            stmt = stmt.order_by(JobsORM.is_featured.desc(), JobsORM.posted_at.desc())
            total_jobs = session.scalar(select(func.count()).select_from(stmt.subquery()))

            jobs = session.execute(
                stmt.offset((page - 1) * page_size).limit(page_size)
            ).scalars().all()

            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0

            return dict(
                jobs=[Job(**job.to_dict()) for job in jobs],
                total_jobs=total_jobs,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )

    @error_handler
    async def get_jobs_by_location(self, location: str, page: int = 1, page_size: int = 25) -> dict:
        """
        Search for jobs by location with featured and recent sorting, plus pagination.

        Args:
            location (str): Partial match for city/province/country.
            page (int): Page number.
            page_size (int): Number of items per page.

        Returns:
            dict: Paginated search results including jobs list, total count, and pagination metadata.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Enforce reasonable limits

        with self.get_session() as session:
            search_pattern = f"%{location}%"

            base_query = session.query(JobsORM).filter(
                JobsORM.status == 'active',
                or_(
                    JobsORM.city.ilike(search_pattern),
                    JobsORM.province.ilike(search_pattern),
                    JobsORM.country.ilike(search_pattern)
                )
            )

            total_jobs = base_query.count()
            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0

            jobs_orm_list = (
                base_query
                .order_by(desc(JobsORM.is_featured), desc(JobsORM.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            return {
                'jobs': [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list],
                'page': page,
                'page_size': page_size,
                'total_jobs': total_jobs,
                'total_pages': total_pages
            }

    @error_handler
    async def search_by_type(self, job_type: str, page: int = 1, page_size: int = 25) -> dict:
        """
        Search for jobs filtered by job type (e.g., full-time, part-time).

        Args:
            job_type (str): The job type to filter on.
            page (int): Page number.
            page_size (int): Number of jobs per page.

        Returns:
            dict: Paginated results with jobs list and metadata.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Enforce reasonable limits

        with self.get_session() as session:
            query = session.query(JobsORM).filter(
                JobsORM.status == 'active',
                JobsORM.position_type.ilike(job_type)  # case-insensitive match
            ).order_by(JobsORM.is_featured.desc(), JobsORM.created_at.desc())

            total_jobs = query.count()
            jobs_orm_list = query.offset((page - 1) * page_size).limit(page_size).all()
            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0
            jobs = [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list if job_orm]

            return {
                "jobs": jobs,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_jobs": total_jobs,
            }


    @error_handler
    async def get_recent_jobs(self, page: int = 1, page_size: int = 25) -> dict:
        """
        Retrieve paginated list of most recently posted active jobs.

        Args:
            page (int): The page number for pagination.
            page_size (int): Number of jobs per page (max 100).

        Returns:
            dict: Paginated search results containing jobs and metadata.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Enforce reasonable limits

        with self.get_session() as session:
            query = session.query(JobsORM).filter(
                JobsORM.status == JobStatusEnum.ACTIVE.value
            ).order_by(JobsORM.is_featured.desc(), JobsORM.posted_at.desc())

            total_jobs = query.count()
            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0

            jobs_orm_list = query.offset((page - 1) * page_size).limit(page_size).all()

            jobs = [
                Job(**job_orm.to_dict())
                for job_orm in jobs_orm_list
                if job_orm and job_orm.is_active
            ]

            return {
                'jobs': jobs,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'total_jobs': total_jobs
            }


    @error_handler
    async def search_by_salary_range(self,min_salary: int | None = None,max_salary: int | None = None,page: int = 1,
        page_size: int = 25,
        unit: str = "yearly"
    ) -> dict:
        """
        Search jobs by salary range with pagination and support for 'monthly' or 'yearly' input.

        Args:
            min_salary (int): Minimum salary in the given unit.
            max_salary (int): Maximum salary in the given unit.
            page (int): Page number for pagination.
            page_size (int): Number of jobs per page.
            unit (str): Salary unit ('monthly' or 'yearly').

        Returns:
            dict: Paginated job results matching salary filter.
        """
        # Convert monthly input to yearly if needed
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Enforce reasonable limits

        if unit == "monthly":
            if min_salary is not None:
                min_salary *= 12
            if max_salary is not None:
                max_salary *= 12

        with self.get_session() as session:
            query = session.query(JobsORM).filter(JobsORM.status == JobStatusEnum.ACTIVE.value)

            if min_salary is not None:
                query = query.filter(JobsORM.salary_min >= min_salary)
            if max_salary is not None:
                query = query.filter(JobsORM.salary_max <= max_salary)

            total_jobs = query.count()
            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0

            jobs_orm_list = query.order_by(JobsORM.is_featured.desc(), JobsORM.posted_at.desc()) \
                                .offset((page - 1) * page_size) \
                                .limit(page_size).all()

            jobs = [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list if job_orm and job_orm.is_active]

            return {
                'jobs': jobs,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'total_jobs': total_jobs,
                'min_salary': min_salary,
                'max_salary': max_salary,
                'salary_unit': unit
            }


    @error_handler
    async def get_active_jobs(self) -> list[Job]:
        """Get currently active jobs that haven't expired and are marked as active"""
        with self.get_session() as session:
            current_time = datetime.now(timezone.utc)
            jobs_orm_list = (session.query(JobsORM)
                             .filter(JobsORM.is_active, JobsORM.expires_at >= current_time)
                .order_by(JobsORM.posted_at.desc())
                             .all())

            return [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list
                    if job_orm and job_orm.is_active]

    @error_handler
    async def get_saved_jobs_for_user(self, user_id: str) -> list[Job]:
        """Get jobs saved by a user with saving metadata"""
        with self.get_session() as session:
            # All operations here are synchronous, no 'await'
            saved_jobs_orm_list = (
                session.query(SavedJobORM)
                .filter(SavedJobORM.user_id == user_id)
                .options(joinedload(SavedJobORM.job))  # Eagerly load the related Job object
                .order_by(SavedJobORM.created_at.desc())
                .all()  # This is a blocking call
            )
            return [
                Job(**saved_job.job.to_dict(include_relationships=True))
                for saved_job in saved_jobs_orm_list
                if saved_job.job  # Handle potential orphaned entries
            ]

    @error_handler
    async def get_applied_jobs_for_user(self, user_id: str) -> list[JobApplication]:
        """Get job applications with full job details for a user"""
        with self.get_session() as session:
            job_applications_orm_list = (
                session.query(JobApplicationORM).filter_by(user_id=user_id)
                .options(joinedload(JobApplicationORM.job))  # Eager load job details
                .order_by(JobApplicationORM.applied_date.desc()).all())

            return [
                JobApplication(**app.to_dict(include_relationships=True))
                for app in job_applications_orm_list if app.job]  # Ensure the associated job still exists

    @error_handler
    async def get_jobs_by_employer(self, employer_id: str, limit: int = 100) -> list[Job]:
        """Get jobs posted by a specific employer (company)"""
        with self.get_session() as session:
            # Step 1: Get the company ID associated with this employer
            employer_orm = session.query(EmployerORM).filter(EmployerORM.employer_id == employer_id).first()

            if not employer_orm:
                return []

            company_id = employer_orm.company_id

            # Step 2: Get jobs for this company
            jobs_query = (
                session.query(JobsORM)
                .filter(JobsORM.company_id == company_id)
                .options(joinedload(JobsORM.company))  # Eager load company data
                .order_by(JobsORM.posted_at.desc())
                .limit(min(limit, 1000))
            )

            jobs = jobs_query.all()
            return [Job(**job.to_dict()) for job in jobs]

    # @error_handler
    # async def get_personalized_job_recommendations(self, user_id: str) -> list[Job]:
    #     """
    #     Generate personalized job recommendations for a jobseeker.
    #
    #     The recommendation engine considers various aspects of the user's profile,
    #     including job title preferences, industries of interest, location preferences,
    #     remote work preferences, relevant skills from their primary CV, and salary expectations.
    #     It excludes jobs the user has already applied for and prioritizes active, non-expired jobs.
    #
    #     Args:
    #         user_id (str): Unique identifier of the jobseeker.
    #
    #     Returns:
    #         list[Job]: A list of recommended job postings, ordered by relevance.
    #     """
    #
    #     with self.get_session() as session:
    #         # Get user profile and CV data
    #         profile_orm: JobSeekerProfileORM = session.query(JobSeekerProfileORM).get(user_id)
    #         cv_orm: JobSeekerCVORM = session.query(JobSeekerCVORM).filter_by(user_uid=user_id, is_primary=True).first()
    #
    #         profile = JobSeekerProfile(**profile_orm.to_dict())
    #         cv = JobSeekerCV(**cv_orm.to_dict())
    #
    #         if not profile or not cv:
    #             return []
    #
    #         # Base query with common filters
    #         query = session.query(JobsORM).filter(
    #             JobsORM.status == JobStatusEnum.ACTIVE.value,
    #             JobsORM.expires_at > datetime.now(timezone.utc)
    #         )
    #         applied_jobs_orm_list = session.query(JobApplicationORM).filter_by(user_id=user_id).all()
    #         applied_jobs_list = [JobApplication(**applied_job_orm.to_dict()) for applied_job_orm in  applied_jobs_orm_list if applied_job_orm]
    #         # Exclude already applied jobs
    #         applied_job_ids = [applied_job.job_id for applied_job in applied_jobs_list]
    #         if applied_job_ids:
    #             query = query.filter(JobsORM.job_id.notin_(applied_job_ids))
    #
    #         # Job Title Preferences
    #         if profile.job_titles_of_interest:
    #             title_conds = [JobsORM.title.ilike(f"%{title}%") for title in profile.job_titles_of_interest]
    #             query = query.filter(or_(*title_conds))
    #
    #         # Industry Preferences
    #         if profile.industries_of_interest:
    #             query = query.filter(JobsORM.category.op('&&')(profile.industries_of_interest))
    #
    #         # Location Preferences
    #         location_conds = []
    #         if profile.location:
    #             location_conds.extend([
    #                 JobsORM.city.ilike(f"%{profile.location}%"),
    #                 JobsORM.province.ilike(f"%{profile.location}%")
    #             ])
    #         if profile.locations_of_interest:
    #             for loc in profile.locations_of_interest:
    #                 location_conds.extend([
    #                     JobsORM.city.ilike(f"%{loc}%"),
    #                     JobsORM.province.ilike(f"%{loc}%")
    #                 ])
    #         if location_conds:
    #             query = query.filter(or_(*location_conds))
    #
    #         # Remote Preference
    #         if profile.remote_preference:
    #             query = query.filter(JobsORM.remote_policy.in_(["REMOTE", "HYBRID"]))
    #
    #         # Skills Matching (from CV)
    #         if cv.skills:
    #             skill_conds = [
    #                 cond
    #                 for skill in cv.skills
    #                 for cond in [
    #                     JobsORM.required_skills.contains([skill]),
    #                     JobsORM.preferred_skills.contains([skill])
    #                 ]
    #             ]
    #
    #             query = query.filter(or_(*skill_conds))
    #
    #         # Salary Expectations (from CV if available)
    #         if profile.expected_salary:
    #             query = query.filter(
    #                 JobsORM.salary_min >= profile.expected_salary * 0.7,
    #                 JobsORM.salary_max <= profile.expected_salary * 1.3
    #             )
    #
    #         # Order by relevance factors
    #         results = query.order_by(
    #             JobsORM.posted_at.desc(),
    #             JobsORM.is_featured.desc(),
    #             JobsORM.application_count.desc()
    #         ).limit(100).all()
    #
    #         return [Job(**job.to_dict()) for job in results]

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

    def _get_improvement_suggestions(self, scores: dict[str, int]):
        """
            create improvement suggestions give scores
        :param scores:
        :return:
        """
        pass

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

    @error_handler
    async def get_similar_jobs(self, job_id: str, limit: int = 12) -> list[Job]:
        with self.get_session() as session:
            # Eager load category and skills
            target_job = session.query(JobsORM).options(
                joinedload(JobsORM.category),
                joinedload(JobsORM.required_skills),
                joinedload(JobsORM.preferred_skills)
            ).get(job_id)

            if not target_job:
                return []

            # --- Extract Keywords (Improved) ---
            def extract_keywords(text: str) -> list[str]:
                # Use simple space splitting for skills
                return [word.strip().lower() for word in text.split()
                        if len(word.strip()) > 3][:8]

            # Combine all text fields
            search_text = " ".join([
                target_job.title,
                target_job.description or "",
                " ".join(target_job.required_skills or []),
                " ".join(target_job.preferred_skills or [])
            ])

            keywords = list(set(extract_keywords(search_text)))

            if not keywords:
                return []

            # --- Build Conditions (JSON-safe) ---
            keyword_conditions = []
            for kw in keywords:
                # Use cast for JSON fields
                kw_cond = or_(
                    JobsORM.title.ilike(f"%{kw}%"),
                    JobsORM.description.ilike(f"%{kw}%"),
                    cast(JobsORM.required_skills, String).ilike(f"%{kw}%"),
                    cast(JobsORM.preferred_skills, String).ilike(f"%{kw}%"),
                )
                keyword_conditions.append(kw_cond)

            # --- Main Query (Optimized) ---
            base_query = session.query(JobsORM).filter(
                JobsORM.job_id != job_id,
                JobsORM.status == JobStatusEnum.ACTIVE.value
            )

            # Handle category matching
            category_match = None
            if target_job.category:
                category_match = JobsORM.category_id == target_job.category.category_id

            # Build final query
            if category_match:
                base_query = base_query.filter(or_(
                    category_match,
                    and_(*keyword_conditions)
                ))
            else:
                base_query = base_query.filter(and_(*keyword_conditions))

            # --- Ordering (Performance-friendly) ---
            order_criteria = [JobsORM.posted_at.desc()]
            if category_match:
                # Boolean sort: category matches first
                order_criteria.insert(0, category_match.desc())

            similar_jobs = (
                base_query.order_by(*order_criteria)
                .limit(limit)
                .all()
            )

            return [Job(**job.to_dict()) for job in similar_jobs]

    @error_handler
    async def get_job_by_slug(self, slug: str) -> Optional[Job]:
        """
        Retrieve a job by its slug.

        Args:
            slug: The slug string to search for (must be exact match).

        Returns:
            A Job Pydantic model instance or None if not found.
        """
        with self.get_session() as session:
            try:
                stmt = select(JobsORM).where(JobsORM.slug == slug)
                result = session.execute(stmt).scalar_one()
                return Job(**result.to_dict())
            except NoResultFound:
                return None

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
                    ))
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
    async def search_by_company(self,company_slug: str,page: int = 1,page_size: int = 25) -> dict[str, str | int | list[Job]]:
        """
        Get all active jobs posted by a specific company using slug.

        Args:
            company_slug (str): Slugified version of company name.
            page (int): Current page.
            page_size (int): Jobs per page.

        Returns:
            dict: Paginated job results.
        """
        company_name = company_slug.replace('-', ' ').strip().lower()

        with self.get_session() as session:
            query = session.query(JobsORM).filter(
                JobsORM.status == JobStatusEnum.ACTIVE.value,
                func.lower(JobsORM.company.name).ilike(f"%{company_name}%")
            )

            total_jobs = query.count()
            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0


            jobs_orm_list = query.order_by(JobsORM.posted_at.desc()) \
                                .offset((page - 1) * page_size) \
                                .limit(page_size).all()

            jobs = [
                Job(**job_orm.to_dict())
                for job_orm in jobs_orm_list
                if job_orm and job_orm.is_active
            ]

            return {
                'jobs': jobs,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'total_jobs': total_jobs,
                'company_name': company_name.title()
            }

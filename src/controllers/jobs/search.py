# Standard Library
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

# Flask Core
from flask import Flask

# SQLAlchemy Core & ORM
from sqlalchemy import or_, desc, String, case, true, select, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import cast
from sqlalchemy.sql.operators import and_

# App Core
from src.controllers.controller import Controllers, error_handler
from src.database.sql import escape_like

# Domain Models (aggregated)
from src.database.models import (
    Job,
    JobApplication,
    JobStatusEnum,
    JobCategory,
    JobSeekerProfile,
    JobSeekerCV,
)

# SQL Models (ORMs)
from src.database import (
    CompanyORM,
    EmployerORM,
    JobsORM,
    SavedJobORM,
    JobApplicationORM,
    JobCategoryORM,
    JobSeekerProfileORM,
    JobSeekerCVORM,
)

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
    async def get_all_jobs(self, page: int = 1, page_size: int = 20) -> dict:
        """Paginated list of active jobs, with featured jobs preferred"""
        if not (isinstance(page, int) and isinstance(page_size, int)):
            self.logger.error("Page Number and Page Size can only be integers")
            return {}
                    
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
                    .all())
            # get_all_jobs : Unexpected error: can't compare offset-naive and offset-aware datetimes
            jobs = [Job(**job.to_dict()) for job in jobs_orm_list if job] if jobs_orm_list else []
            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0
            return {"page": page, "page_size": page_size, "total_jobs": total_jobs,
                    "total_pages": total_pages, "jobs": jobs}

    @error_handler
    async def search_jobs(self,keyword: str = '', page: int = 1, page_size: int = 25) -> dict[str, str | int | list[Job]]:
        """sumary_line
            Search jobs by keyword in title or description with pagination.
        Keyword arguments:
        argument -- description
        Return: return_description
        """
        if not (isinstance(keyword, str) and keyword.strip()):        
            self.logger.error("Keyword can only be a string")
            return {}

        if not (isinstance(page, int) and isinstance(page_size, int)):
            self.logger.error("Page Number and Page Size can only be integers")
            return {}

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

            jobs: list[Job] =  [Job(**job.to_dict()) for job in jobs_orm_list if job] if jobs_orm_list else []
            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0

            return {"page": page,"page_size": page_size,"total_jobs": total_jobs,"total_pages": total_pages,"jobs": jobs}


    @error_handler
    async def list_job_categories(self, job_limit_per_category: int = 15) -> list[JobCategory]:
        """
        Returns a list of job categories along with a limited number of associated jobs per category.
        """
        if not isinstance(job_limit_per_category, int):
            self.logger.error("job_limit_per_category can only be a string")
            return []

        upper_limit = min(20, job_limit_per_category)
        with self.get_session() as session:
            category_orm_list: list[JobCategoryORM] = session.query(JobCategoryORM).all()

            result = []
            for category_orm in category_orm_list:
                jobs = (
                    session.query(JobsORM)
                    .filter(JobsORM.category_id == category_orm.category_id)
                    .order_by(JobsORM.created_at.desc())  # assuming you want the latest jobs
                    .limit(upper_limit)
                    .all()
                )
                category_dict = category_orm.to_dict(include_jobs=False)
                category_dict["jobs"] = [job.to_dict() for job in jobs] if jobs else []
                result.append(JobCategory(**category_dict))

            return result

    @error_handler
    async def search_jobs_by_category(self, category: str, page: int = 1, page_size: int = 25) -> dict:
        """Search jobs by category with pagination, filtered to active and featured preferred."""
        
        if not (isinstance(category, str) and category.strip()):
            self.logger.error("This is a category name where the search is to be conducted")
            return {}
        
        if not (isinstance(page, int) and isinstance(page_size, int)):
            self.logger.error("Page Number and Page Size can only be integers")
            return {}

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
                "jobs": [Job(**job.to_dict()) for job in jobs_orm_list] if jobs_orm_list else [],
                "total_jobs": total_jobs,
                "total_pages": total_pages,
                "page": page,
                "page_size": page_size}
            
    @error_handler
    async def get_job_by_id(self, job_id: str) -> Job | None:
        """Retrieve a single active job by its ID."""
        if not (isinstance(job_id, str) and job_id.strip()):
            self.logger.error("Job ID can only be a string")
            return None

        with self.get_session() as session:
            job_orm = session.query(JobsORM).filter(
                JobsORM.job_id == job_id,
                JobsORM.status == JobStatusEnum.ACTIVE.value
            ).first()
            return Job(**job_orm.to_dict()) if job_orm else None

    @error_handler
    async def get_complete_job_by_id(self, job_id: str) -> Job | None:
        """

        :param job_id:
        :return:
        """
        with self.get_session() as session:
            job_orm = (
                session.query(JobsORM).filter_by(job_id=job_id)
                .options(joinedload(JobsORM.category)).first()
            )
            return Job(**job_orm.to_dict(include_relationship=True)) if job_orm else None

    @error_handler
    async def get_application_by_id(self, application_id: str) -> JobApplication | None:
        """Get a job application by ID with all related data"""
        if not (isinstance(application_id, str) and application_id.strip()):
            self.logger.error("Invalid Application ID")
            return None
            
        with self.get_session() as session:
            job_application_orm = (
                session.query(JobApplicationORM)
                .filter_by(application_id=application_id)
                .options(joinedload(JobApplicationORM.job))  # Eager load job details
                .first()
            )
            if not job_application_orm:
                return None

            return JobApplication(**job_application_orm.to_dict(include_relationships=True))


    
    @error_handler
    async def get_job_by_reference(self, reference: str) -> Job | None:
        """
        :param reference:
        :return:
        """
        if not (isinstance(reference, str) and reference.strip()):
            self.logger.error("Job Reference can only be a string")
            return None

        with self.get_session() as session:
            _reference = reference.casefold()
            job_orm = session.query(JobsORM).filter_by(job_ref=_reference).first()
            if not job_orm:
                return None
            return Job(**job_orm.to_dict())

    @error_handler    
    async def archive_job_listing(self, job_id: str) -> Job | None:
        """Archive job listing """
        if not (isinstance(job_id, str) and job_id.strip()):
            return None

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
        
        if not (isinstance(page, int) and isinstance(page_size, int)):
            self.logger.error("Page Number and Page Size can only be Integers")
            return {}

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

            jobs = [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list] if jobs_orm_list else []

            return {'jobs': jobs,'page': page,'page_size': page_size,'total_pages': total_pages,'total_jobs': total_jobs}

    @error_handler
    async def get_jobs_by_title(self,title: str,page: int = 1,page_size: int = 25) -> dict:
        """sumary_line
        
        Keyword arguments:
        argument -- description
        Return: return_description
        """
        if not (isinstance(title, str) and title.strip()):
            self.logger.error("Only Job Titles are accepted")
            return {}

        if not (isinstance(page, int) and isinstance(page_size, int)):
            self.logger.error("Page Number and Page Size can only be Integers")
            return {}

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
                "jobs": [Job(**job.to_dict()) for job in jobs] if jobs else [],
                "total_jobs": total_jobs,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages}

    @error_handler
    async def get_jobs_by_qualification(self,qualification: str, qualification_types: Optional[list[str]] = None,
        page: int = 1, page_size: int = 25) -> dict:
        """
        
        """
        if qualification_types is None:
            qualification_types = [
                "matric", "diploma", "bachelor", "honours", "masters", "phd",
                "certificate", "trade_certificate"
            ]

        if not (isinstance(qualification, str) and qualification.strip()):
            self.logger.error(f"Qualification can only be string and a name of any of this qualifications str(qualification_types)")
            return {}

        if not (isinstance(page, int) and isinstance(page_size, int)):
            self.logger.error("Page Number and Page Size can only be Integers")
            return {}

        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Enforce reasonable limits


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
                jobs=[Job(**job.to_dict()) for job in jobs] if jobs else [],
                total_jobs=total_jobs,
                page=page,
                page_size=page_size,
                total_pages=total_pages)

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
        if not (isinstance(location, str) and location.strip()):
            self.logger.error("Location can only a string a name of Town, City, or Province")
            return {}
        if not (isinstance(page, int) and isinstance(page_size, int)):
            self.logger.error("Page Number and page size can only be integers")
            return {}

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
                'jobs': [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list if job_orm] if jobs_orm_list else [],
                'page': page,
                'page_size': page_size,
                'total_jobs': total_jobs,
                'total_pages': total_pages}

    @error_handler
    async def search_by_type(self, job_type: str, page: int = 1, page_size: int = 25) -> dict:
        """
        Search for jobs filtered by job event_type (e.g., full-time, part-time).

        Args:
            job_type (str): The job event_type to filter on.
            page (int): Page number.
            page_size (int): Number of jobs per page.

        Returns:
            dict: Paginated results with jobs list and metadata.
        """
        if not (isinstance(job_type, str) and job_type.strip()):
            self.logger.error("job_type needs to be a string")
            return {}

        if not (isinstance(page, int) and isinstance(page_size, int)):
            self.logger.error("Page Number and Page Size can only be Integers")
            return {}
            
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
            jobs = [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list if job_orm] if jobs_orm_list else []

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
        if not (isinstance(page, int) and isinstance(page_size, int)):
            self.logger.error("Page Number and Page Size can only be Integers")
            return {}

        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Enforce reasonable limits

        with self.get_session() as session:
            query = session.query(JobsORM).filter(
                JobsORM.status == JobStatusEnum.ACTIVE.value
            ).order_by(JobsORM.is_featured.desc(), JobsORM.posted_at.desc())

            total_jobs = query.count()
            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0

            jobs_orm_list = query.offset((page - 1) * page_size).limit(page_size).all()

            jobs = [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list if job_orm and job_orm.is_active] if jobs_orm_list else []

            return {
                'jobs': jobs,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'total_jobs': total_jobs}


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
        if not (isinstance(page, int) and isinstance(page_size, int)):
            self.logger.error("Page Number and Page Size can only be Integers")
            return {}
        if not (isinstance(unit, str) and unit.strip()):
            self.logger.error("Unit can only be one of two strings : (yearly, monthly)")
            return {}
        if unit.casefold() not in ['yearly', 'monthly']:
            self.logger.error("Unit needs to be either (yearly, monthly)")
            return {}
        
        # There is still a possibility that min_salary or max_salary is not int or even None. but something else.

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

            jobs = [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list if job_orm and job_orm.is_active] if jobs_orm_list else []

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
    async def get_active_jobs(self, limit: int = 100) -> list[Job]:
        """Get currently active jobs that haven't expired and are marked as active"""
        
        if not isinstance(limit, int):
            self.logger.error("Limit needs to be an integer")
            return []

        upper_limit = min(limit, 1000)  # Enforce reasonable limits        
        with self.get_session() as session:
            current_time = datetime.now(timezone.utc)
            jobs_orm_list = (session.query(JobsORM).filter(JobsORM.is_active, JobsORM.expires_at >= current_time)
                .order_by(JobsORM.posted_at.desc()).limit(upper_limit).all())

            return [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list
                    if job_orm and job_orm.is_active] if jobs_orm_list else []

    @error_handler
    async def get_saved_jobs_for_user(self, user_id: str) -> list[Job]:
        """Get jobs saved by a user with saving metadata"""
        if not (isinstance(user_id, str) and user_id.strip()):
            self.logger.error("Invalid User ID")
            return []

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
                if saved_job.job ] if saved_jobs_orm_list else []

    @error_handler
    async def get_applied_jobs_for_user(self, user_id: str, page: int = 1, page_size: int = 20) -> tuple[
        list[JobApplication], int]:
        """Get job applications with full job details for a user with pagination
        
        Returns:
            tuple: (applications_list, total_count)
        """

        if not (isinstance(user_id, str) and user_id.strip()):
            self.logger.error("Invalid User ID")
            return [], 0

        if not isinstance(page, int) or page < 1:
            page = 1
        if not isinstance(page_size, int) or page_size < 1:
            page_size = 20

        with self.get_session() as session:
            # Get total count for pagination
            total_count = (
                session.query(JobApplicationORM)
                .filter_by(user_id=user_id)
                .join(JobApplicationORM.job)  # Only count applications with existing jobs
                .count()
            )

            # Get paginated results
            offset = (page - 1) * page_size
            job_applications_orm_list = (
                session.query(JobApplicationORM)
                .filter_by(user_id=user_id)
                .options(joinedload(JobApplicationORM.job))  # Eager load job details
                .join(JobApplicationORM.job)  # Only get applications with existing jobs
                .order_by(JobApplicationORM.applied_date.desc())
                .offset(offset)
                .limit(page_size)
                .all()
            )

            # Convert to Pydantic models
            applications = [
                JobApplication(**app.to_dict(include_relationships=True))
                for app in job_applications_orm_list
            ] if job_applications_orm_list else []

            return applications, total_count  

    @error_handler
    async def get_jobs_by_employer(self, employer_id: str, limit: int = 100) -> list[Job]:
        """Get jobs posted by a specific employer (company)"""
        if not (isinstance(employer_id, str) and employer_id.strip()):
            self.logger.error("Invalid Employer ID")
            return []
        if not isinstance(limit, int):
            self.logger.error("Invalid Limit")
            return []

        upper_limit = min(limit, 1000)  # Enforce reasonable limits        
        with self.get_session() as session:
            # Step 1: Get the company ID associated with this employer
            employer_orm = session.query(EmployerORM).filter(EmployerORM.employer_id == employer_id).first()

            if not employer_orm:
                return []

            company_id = employer_orm.company_id

            # Step 2: Get jobs for this company
            jobs_orm_list = (
                session.query(JobsORM)
                .filter(JobsORM.company_id == company_id)
                .options(joinedload(JobsORM.company))  # Eager load company data
                .order_by(JobsORM.posted_at.desc())
                .limit(upper_limit).all())

            
            return [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list if job_orm] if jobs_orm_list else [] 

    @error_handler
    async def get_user_dashboard_statistics(self, user_id: str) -> dict:
        """
        Get dashboard statistics for a specific user including application counts and saved jobs.
        
        Args:
            user_id (str): The ID of the user to get statistics for.
            
        Returns:
            dict: Dictionary containing user statistics including:
                - applications_count: Total number of applications submitted
                - saved_jobs_count: Total number of saved jobs
                - recent_applications_count: Applications from last 7 days
                - cv_uploaded: Whether user has uploaded at least one CV
        """
        if not (isinstance(user_id, str) and user_id.strip()):
            self.logger.error("Invalid User ID")
            return {}

        with self.get_session() as session:
            # Count total applications
            applications_count = session.query(JobApplicationORM).filter_by(user_id=user_id).count()
            
            # Count saved jobs
            saved_jobs_count = session.query(SavedJobORM).filter_by(user_id=user_id).count()
            
            # Count recent applications (last 7 days)
            
            recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            recent_applications_count = session.query(JobApplicationORM).filter(
                JobApplicationORM.user_id == user_id,
                JobApplicationORM.applied_date >= recent_cutoff
            ).count()
            
            # Check if user has uploaded at least one CV
            cv_count = session.query(JobSeekerCVORM).filter_by(user_uid=user_id).count()
            cv_uploaded = cv_count > 0
            
            return {
                'applications_count': applications_count,
                'saved_jobs_count': saved_jobs_count,
                'recent_applications_count': recent_applications_count,
                'cv_uploaded': cv_uploaded,
                'cv_count': cv_count}
            

    @error_handler
    async def count_user_applications(self, user_id: str) -> int:
        """
        Count total number of applications submitted by a user.
        
        Args:
            user_id (str): The ID of the user to count applications for.
            
        Returns:
            int: Total number of applications submitted by the user.
        """
        if not (isinstance(user_id, str) and user_id.strip()):
            self.logger.error("Invalid User ID")
            return 0

        with self.get_session() as session:
            return session.query(JobApplicationORM).filter_by(user_id=user_id).count()

    @error_handler
    async def count_saved_jobs_for_user(self, user_id: str) -> int:
        """
        Count total number of jobs saved by a user.
        
        Args:
            user_id (str): The ID of the user to count saved jobs for.
            
        Returns:
            int: Total number of jobs saved by the user.
        """
        if not (isinstance(user_id, str) and user_id.strip()):
            self.logger.error("Invalid User ID")
            return 0

        with self.get_session() as session:
            return session.query(SavedJobORM).filter_by(user_id=user_id).count()

    @error_handler
    async def calculate_quick_match_score(self, job: Job, user_profile: JobSeekerProfile) -> float:
        """
        Lightweight match score for job listings.
        Non-AI, fast computation for listing views.
        """
        if not job or not user_profile:
            return 0.0

        scores = {}
        self.logger.info(f"Scores : {scores}")
        # -------------------------
        # Location Match (40%)
        # -------------------------
        location_score = 0
        user_loc = (user_profile.location or "").strip().lower()
        job_city = (job.city if job.city else "").strip().lower()
        job_province = (job.province if job.province else "").strip().lower()

        # Exact city match
        if user_loc and job_city and user_loc == job_city:
            location_score = 100
        # Province match
        elif user_loc and job_province and job_province in user_loc:
            location_score = 80
        # Locations of interest
        elif user_profile.locations_of_interest:
            for loc in user_profile.locations_of_interest:
                loc_low = loc.strip().lower()
                if loc_low == job_city:
                    location_score = 100
                    break
                elif job_province and job_province in loc_low:
                    location_score = 80
                    break

        # Remote preference
        if (user_profile.remote_preference == True) and (job.remote_policy in ["REMOTE", "HYBRID"]):
            location_score = max(location_score, 90)
        elif (user_profile.remote_preference == False) and (job.remote_policy in ["ONSITE", "HYBRID"]):
            location_score = max(location_score, 90)

        scores["location"] = location_score
        self.logger.info(f"Scores : {scores}")
        # -------------------------
        # Title Match (30%)
        # -------------------------
        title_score = 0
        if user_profile.job_titles_of_interest and job.title:
            job_title_lower = job.title.lower()
            for interested_title in user_profile.job_titles_of_interest:
                interested_lower = interested_title.lower()
                if interested_lower == job_title_lower:
                    title_score = 100
                    break
                elif interested_lower in job_title_lower:
                    title_score = max(title_score, 80)
                elif any(word in interested_lower for word in job_title_lower.split() if len(word) > 3):
                    title_score = max(title_score, 60)

        scores["title"] = title_score
        self.logger.info(f"Scores : {scores}")
        # -------------------------
        # Experience Match (20%)
        # -------------------------
        experience_score = 0
        if job.experience_level:
            exp_levels = {"ENTRY": 1, "MID": 2, "SENIOR": 3}
            job_level = exp_levels.get(job.experience_level.upper(), 1)

            user_level = 1
            if user_profile.expected_salary and user_profile.expected_salary > 600000:
                user_level = 3
            elif user_profile.expected_salary and user_profile.expected_salary > 300000:
                user_level = 2
            elif user_profile.profile_completion_percentage > 80:
                user_level = 2

            if user_level >= job_level:
                experience_score = 100
            elif user_level == job_level - 1:
                experience_score = 75
            else:
                experience_score = 40

        scores["experience"] = experience_score
        self.logger.info(f"Scores : {scores}")
        # -------------------------
        # Industry Match (10%)
        # -------------------------
        industry_score = 0
        if job.category and user_profile.industries_of_interest:
            for industry in user_profile.industries_of_interest:
                if industry.lower().strip() == job.category.name.lower().strip():
                    industry_score = 100
                    break
                elif industry.lower() in job.category.name.lower() or job.category.name.lower() in industry.lower():
                    industry_score = max(industry_score, 70)

        scores["industry"] = industry_score
        self.logger.info(f"Scores : {scores}")
        # -------------------------
        # Weighted Sum
        # -------------------------
        weights = {
            "location": 0.40,
            "title": 0.30,
            "experience": 0.20,
            "industry": 0.10,
        }
        total_score = sum(scores[cat] * weights[cat] for cat in weights)

        return round(total_score, 1)

    @error_handler
    async def calculate_job_match_score(self, job: Job, user_id: str) -> dict:
        """
        Deep match score for a single job against a candidate's profile & CV.
        Returns detailed breakdown, explanations, and improvement suggestions.
        """
        if not (isinstance(user_id, str) and user_id.strip()):
            self.logger.error("Invalid User ID")
            return {}

        self.logger.info(f"Calculating job match score for user_id: {user_id}")

        with self.get_session() as session:
            profile_orm = session.query(JobSeekerProfileORM).get(user_id)
            cv_orm = (
                session.query(JobSeekerCVORM)
                .options(
                    joinedload(JobSeekerCVORM.experience),
                    joinedload(JobSeekerCVORM.education),
                    joinedload(JobSeekerCVORM.certifications),
                    joinedload(JobSeekerCVORM.languages),
                    joinedload(JobSeekerCVORM.projects),
                    joinedload(JobSeekerCVORM.publications),
                    joinedload(JobSeekerCVORM.awards),
                    joinedload(JobSeekerCVORM.custom_sections),
                    joinedload(JobSeekerCVORM.jobseeker_profile)
                )
                .filter_by(user_uid=user_id, is_primary=True)
                .first()
            )
            profile = JobSeekerProfile(**profile_orm.to_dict()) if profile_orm else None
            cv = JobSeekerCV(**cv_orm.to_dict(include_relationships=True)) if cv_orm else None

            if not profile or not cv or not job:
                self.logger.error(f"Missing profile, CV, or job data for user_id: {user_id}")
                return {}

            scores = {
                "skills_match": 0,
                "experience_match": 0,
                "education_match": 0,
                "industry_match": 0,
                "title_match": 0,
                "location_match": 0,
                "remote_match": 0,
                "salary_match": 0,
                "total_score": 0
            }

            # --- SKILLS MATCH (30%) ---
            matched_skills = []
            missing_skills = []
            if cv.skills and (job.required_skills or job.preferred_skills):
                required_skills = set(job.required_skills or [])
                preferred_skills = set(job.preferred_skills or [])
                user_skills = set(cv.skills)

                matched_required = user_skills & required_skills
                matched_preferred = user_skills & preferred_skills

                # Calculate weighted skill score: 70% required, 30% preferred
                required_match_ratio = len(matched_required) / len(required_skills) if required_skills else 0
                preferred_match_ratio = len(matched_preferred) / len(preferred_skills) if preferred_skills else 0

                scores["skills_match"] = round((required_match_ratio * 0.7 + preferred_match_ratio * 0.3) * 100, 1)

                matched_skills = list(matched_required | matched_preferred)
                missing_skills = list(required_skills - user_skills)

            # --- EXPERIENCE MATCH (20%) ---
            exp_levels = ["entry", "mid", "senior"]
            user_exp_level = (cv.experience[-1].level if cv.experience else "entry").lower()
            job_exp_level = (job.experience_level or "entry").lower()

            user_exp_idx = exp_levels.index(user_exp_level) if user_exp_level in exp_levels else 0
            job_exp_idx = exp_levels.index(job_exp_level) if job_exp_level in exp_levels else 0

            def experience_score(u, j):
                if j == 0:
                    return 100 if u > 0 else 0
                return 100 if u >= j else round((u / j) * 100)

            scores["experience_match"] = experience_score(user_exp_idx, job_exp_idx)

            # --- EDUCATION MATCH (15%) ---
            if cv.education and job.education_requirements:
                user_degrees = {e.qualification.lower() for e in cv.education}
                job_degrees = {req.lower() for req in job.education_requirements}
                if job_degrees:
                    scores["education_match"] = round(len(user_degrees & job_degrees) / len(job_degrees) * 100, 1)

            # --- INDUSTRY MATCH (10%) ---
            if job.category and profile.industries_of_interest:
                scores["industry_match"] = 100 if job.category.name in profile.industries_of_interest else 0

            # --- TITLE MATCH (10%) ---
            if profile.job_titles_of_interest:
                scores["title_match"] = 100 if any(
                    title.lower() in job.title.lower()
                    for title in profile.job_titles_of_interest
                ) else 0

            # --- LOCATION MATCH (10%) ---
            location_match = False
            job_city = (job.city or "").lower()
            user_location = (profile.location or "").lower()
            if user_location and job_city:
                location_match = job_city == user_location
            if not location_match and profile.locations_of_interest:
                location_match = job_city in (loc.lower() for loc in profile.locations_of_interest)

            scores["location_match"] = 100 if location_match else 0

            # --- REMOTE MATCH (5%) ---
            # Check if user prefers remote and job allows remote/hybrid
            job_remote = (job.remote_policy or "").upper()
            profile_remote = bool(profile.remote_preference)
            scores["remote_match"] = 100 if (profile_remote and job_remote in ["HYBRID", "REMOTE"]) else 0

            # --- SALARY MATCH (NEW: 10%) ---
            salary_score = 0
            salary_match_level = "Not specified"
            salary_explanation = "Salary analysis not available"
            try:
                # Assume salary_min/max on job and expected_salary_min/max on profile are numbers (ints/floats)
                job_min = getattr(job, 'salary_min', None)
                job_max = getattr(job, 'salary_max', None)
                exp_min = getattr(profile, 'expected_salary_min', None)
                exp_max = getattr(profile, 'expected_salary_max', None)

                if None not in (job_min, job_max, exp_min, exp_max):
                    # Check range overlap
                    overlap_min = max(job_min, exp_min)
                    overlap_max = min(job_max, exp_max)
                    overlap = max(0, overlap_max - overlap_min)

                    job_range = job_max - job_min
                    exp_range = exp_max - exp_min

                    if overlap > 0:
                        # Good overlap, score relative to how much overlap covers job range
                        coverage_ratio = overlap / job_range if job_range > 0 else 0
                        salary_score = round(coverage_ratio * 100, 1)
                        salary_match_level = "Good"
                        salary_explanation = f"Your expected salary range overlaps well with the offered range."
                    else:
                        salary_score = 0
                        salary_match_level = "Poor"
                        salary_explanation = "No overlap between your expected salary and the job's offered range."
                else:
                    salary_explanation = "Salary information incomplete for comparison."
            except Exception as e:
                self.logger.error(f"Error calculating salary match: {e}")

            scores["salary_match"] = salary_score

            # --- TOTAL SCORE (weighted sum) ---
            weights = {
                "skills_match": 0.3,
                "experience_match": 0.2,
                "education_match": 0.15,
                "industry_match": 0.1,
                "title_match": 0.1,
                "location_match": 0.1,
                "remote_match": 0.05,
                "salary_match": 0.1  # Added salary with weight 10%
            }

            total_score = sum(scores[cat] * weights.get(cat, 0) for cat in scores)
            scores["total_score"] = round(total_score, 1)

            # --- EXPLANATIONS ---
            explanations = {
                "skills_explanation": self._build_skills_explanation(matched_skills, missing_skills,
                                                                     len(job.required_skills or [])),
                "experience_explanation": self._build_experience_explanation(user_exp_level, job_exp_level),
                "education_explanation": self._build_education_explanation(scores["education_match"]),
                "industry_explanation": "Industry match found." if scores[
                                                                       "industry_match"] == 100 else "Industry does not match your interests.",
                "title_explanation": "Job title matches your interests." if scores[
                                                                                "title_match"] == 100 else "Job title does not match your interests.",
                "location_explanation": "Job location matches your preferred location." if scores[
                                                                                               "location_match"] == 100 else "Job location does not match your preferred locations.",
                "remote_explanation": "Job supports your remote work preference." if scores[
                                                                                         "remote_match"] == 100 else "Job does not support your remote work preference.",
                "salary_explanation": salary_explanation
            }

            # --- RECOMMENDED IMPROVEMENTS ---
            recommended_improvements = self._get_improvement_suggestions(scores, missing_skills)

            # --- FINAL RETURN ---
            return {
                "total_score": scores["total_score"],
                "score_breakdown": {k: round(v, 1) for k, v in scores.items() if k != "total_score"},
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                **explanations,
                "salary_match_level": salary_match_level,
                "interpretation": self._get_match_interpretation(scores["total_score"]),
                "recommended_improvements": recommended_improvements
            }

    def _build_skills_explanation(self, matched_skills, missing_skills, total_required):
        return (
            f"You matched {len(matched_skills)} skill(s). "
            f"Missing {len(missing_skills)} required skill(s): {', '.join(missing_skills)}."
            if missing_skills else
            f"You matched all required skills!"
        )

    def _build_experience_explanation(self, user_exp_level, job_exp_level):
        if user_exp_level == job_exp_level:
            return f"Your experience level ({user_exp_level.title()}) matches the job requirement."
        elif exp_levels.index(user_exp_level) > exp_levels.index(job_exp_level):
            return f"Your experience level ({user_exp_level.title()}) exceeds the job requirement ({job_exp_level.title()})."
        else:
            return f"Your experience level ({user_exp_level.title()}) is below the job requirement ({job_exp_level.title()})."

    def _build_education_explanation(self, education_score):
        if education_score == 100:
            return "You meet all the education requirements."
        elif education_score > 0:
            return "You meet some of the education requirements."
        else:
            return "You do not meet the education requirements."

    def _get_improvement_suggestions(self, scores, missing_skills):
        suggestions = []
        if scores["skills_match"] < 70:
            if missing_skills:
                suggestions.append(f"Consider gaining skills in: {', '.join(missing_skills)}.")
            else:
                suggestions.append("Add more relevant skills to improve your match.")
        if scores["experience_match"] < 70:
            suggestions.append("Gain more experience related to this job's level.")
        if scores["education_match"] < 70:
            suggestions.append("Consider further education or certifications.")
        if scores["location_match"] < 50:
            suggestions.append("Expand your preferred job locations or consider remote jobs.")
        if scores["salary_match"] < 50:
            suggestions.append("Adjust your salary expectations or seek jobs with better salary ranges.")
        return suggestions

    def _get_match_interpretation(self, total_score):
        if total_score >= 90:
            return "🏆 Excellent Match - You are highly suited for this job!"
        elif total_score >= 75:
            return "👍 Strong Match - Good overall fit with some areas for improvement."
        elif total_score >= 50:
            return "👌 Moderate Match - Some gaps exist; consider improving key areas."
        elif total_score > 30:
            return "🤔 Weak Match - Significant gaps; focus on improving your profile."
        else:
            return "🚫 Poor Match - Not a good fit currently; consider other roles or upskilling."

    @error_handler
    async def get_similar_jobs(self, job_id: str, limit: int = 12) -> list[Job]:
        """
        Return up to `limit` active jobs that are similar to the given `job_id`
        based on shared keywords and/or matching category.
        """
        if not (isinstance(job_id, str) and job_id.strip()):
            self.logger.error("Invalid job_id provided")
            return []

        if not isinstance(limit, int) or limit <= 0:
            self.logger.error("Limit must be a positive integer")
            return []

        upper_limit = min(limit, 100)

        with self.get_session() as session:
            target_job = (
                session.query(JobsORM)
                .options(joinedload(JobsORM.category))
                .get(job_id)
            )
            if not target_job:
                return []

            # --- Keyword extraction -----------------------------------------------------------
            def extract_keywords(text: str) -> list[str]:
                return [w.strip().lower() for w in text.split() if len(w.strip()) > 3][:8]

            search_text = " ".join([
                target_job.title or "",
                target_job.description or "",
                *(target_job.required_skills or []),
                *(target_job.preferred_skills or []),
            ])
            keywords = list(set(extract_keywords(search_text)))
            if not keywords:
                return []

            # --- Build keyword search conditions with OR ----------------------------------
            keyword_conditions = []
            for kw in keywords:
                keyword_conditions.extend([
                    JobsORM.title.ilike(f"%{kw}%"),
                    JobsORM.description.ilike(f"%{kw}%"),
                    cast(JobsORM.required_skills, String).ilike(f"%{kw}%"),
                    cast(JobsORM.preferred_skills, String).ilike(f"%{kw}%"),
                ])

            # Combine using OR instead of AND
            if keyword_conditions:
                keyword_clause = or_(*keyword_conditions)
            else:
                keyword_clause = true()

            # --- Base query setup -------------------------------------------------------------
            base_query = session.query(JobsORM).filter(
                JobsORM.job_id != job_id,
                JobsORM.status == JobStatusEnum.ACTIVE.value
            )

            # --- Apply category filter or fallback to keyword-only ----------------------------
            if target_job.category:
                category_clause = JobsORM.category_id == target_job.category.category_id
                base_query = base_query.filter(or_(category_clause, keyword_clause))
            else:
                base_query = base_query.filter(keyword_clause)

            # --- Ordering: prioritize category match, then newest -----------------------------
            order_clauses = [JobsORM.posted_at.desc()]
            if target_job.category:
                order_clauses.insert(
                    0,
                    case(
                        (JobsORM.category_id == target_job.category.category_id, 1),
                        else_=0
                    ).desc()
                )

            # --- Execute final query ----------------------------------------------------------
            similar_jobs = (
                base_query.order_by(*order_clauses)
                .limit(upper_limit)
                .all()
            )

            return [Job(**job_orm.to_dict()) for job_orm in similar_jobs]

    @error_handler
    async def get_job_by_slug(self, slug: str) -> Optional[Job]:
        """
        Retrieve a job by its slug.

        Args:
            slug: The slug string to search for (must be exact match).

        Returns:
            A Job Pydantic model instance or None if not found.
        """
        if not (isinstance(slug, str) and slug.strip()):
            self.logger.error("Invalid slug")
            return None

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
        if not filters:
            self.logger.error("Filters not supplied")
            return []

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
            
            # This will return at most 100 jobs 
            if filters.get('limit'):
                query = query.limit(min(filters['limit'], 100))
            job_orm_list = query.all()
            return [Job(**job_orm.to_dict()) for job_orm in job_orm_list if job_orm] if job_orm_list else []

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
        if not (isinstance(company_slug, str) and company_slug.strip()):
            self.logger.error("Invalid Company Slug")
            return {}
        if not (isinstance(page, int) and isinstance(page_size, int)):
            self.logger.error("Page Number and Page_size needs be intergers")
            return {}

        # Enforce reasonable limits
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  

        company_name = company_slug.replace('-', ' ').strip().lower()
        
        with self.get_session() as session:
            query = session.query(JobsORM).filter(
                JobsORM.status == JobStatusEnum.ACTIVE.value,
                func.lower(JobsORM.company.name).ilike(f"%{company_name}%")
            )

            total_jobs = query.count()
            # preventing divide by zero.
            total_pages = math.ceil(total_jobs / page_size) if page_size > 0 else 0


            jobs_orm_list = query.order_by(JobsORM.posted_at.desc()) \
                                .offset((page - 1) * page_size) \
                                .limit(page_size).all()

            jobs = [Job(**job_orm.to_dict()) for job_orm in jobs_orm_list
                    if job_orm and job_orm.is_active] if jobs_orm_list else []

            return {
                'jobs': jobs,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'total_jobs': total_jobs,
                'company_name': company_name.title()
            }

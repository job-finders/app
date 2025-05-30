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

from src.database.models.employer_models import Employer
from src.controllers.controller import Controllers
from src.database.models.jobseeker_profile import JobSeekerProfile
from src.database.models.resume import JobSeekerCV
from src.database.sql.jobseeker_profile import JobSeekerProfileORM
from src.database.sql.resume import JobSeekerCVORM
from src.database.sql.users import UserORM

from src.controllers.controller import error_handler
from src.database.models.jobs_model import (Job, JobApplication, SavedJob, JobStatistics, StatusCounts,
                                            ApplicationMetrics, ApplicationFunnelStats, BulkImportResult,
                                            TalentPoolReport, JobApplicationDashboard, ATSReport,
                                            JobApplicationStatusEnum, JobApprovalStatusEnum, JobStatusEnum)
from src.database.sql.jobs_sql import (JobsORM, SavedJobORM, JobApplicationORM, CompanyORM, JobApprovalRequestORM,
    ATSReportORM)


class JobsSearchController(Controllers):
    """sumary_line
    
    Keyword arguments:
    argument -- description
    Return: return_description
    """
    
    
    def __init__(self):
        super().__init__()

    def init_app(self, app: Flask):
        super().init_app(app=app)


    @error_handler
    async def get_all_jobs(self, page: int = 1, page_size: int = 20) -> dict:
        """Paginated list of active jobs, with featured jobs preferred"""
        with self.get_session() as session:
            query = session.query(JobsORM).filter(JobsORM.status == 'active')

            total_jobs = query.count()

            offset = (page - 1) * page_size
            jobs_orm_list = (
                query.order_by(JobsORM.is_featured.desc(), JobsORM.created_at.desc())
                    .offset(offset)
                    .limit(page_size)
                    .all()
            )

            jobs = [Job(**job.to_dict()) for job in jobs_orm_list if job]

            return {
                "page": page,
                "page_size": page_size,
                "total_jobs": total_jobs,
                "total_pages": (total_jobs + page_size - 1) // page_size,
                "jobs": jobs,
            }



    @error_handler
    async def search_jobs(self, keyword: str = '', page: int = 1, page_size: int = 10) -> list[Job]:
        """Search jobs by keyword in title or description with pagination."""
        with self.get_session() as session:
            query = session.query(JobsORM).filter(
                JobsORM.status == 'active',
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

            jobs: list[Jobs] =  [Job(**job.to_dict()) for job in jobs_orm_list if job]


            return {
                "page": page,
                "page_size": page_size,
                "total_jobs": total_jobs,
                "total_pages": (total_jobs + page_size - 1) // page_size,
                "jobs": jobs
                }


    @error_handler
    async def search_jobs_by_category(self, category: str, page: int = 1, page_size: int = 25) -> dict:
        """Search jobs by category with pagination, filtered to active and featured preferred."""
        with self.get_session() as session:
            base_query = session.query(JobsORM).filter(
                JobsORM.status == 'active',
                JobsORM.category.ilike(f'%{category}%')  # match flexible category terms
            )

            total_jobs = base_query.count()
            total_pages = math.ceil(total_jobs / page_size)
            offset = (page - 1) * page_size

            jobs_orm_list = (
                base_query.order_by(JobsORM.is_featured.desc(), JobsORM.created_at.desc())
                        .offset(offset)
                        .limit(page_size)
                        .all()
            )

            return {
                "jobs": [Job(**job.to_dict()) for job in jobs_orm_list if job],
                "total_jobs": total_jobs,
                "total_pages": total_pages,
                "page": page,
                "page_size": page_size
            }

        
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


    @error_handler
    async def get_similar_jobs(self, job_id: str, limit: int = 12) -> List[Job]:
        """
        Retrieve a list of jobs similar to the given job by analyzing title, category,
        job description, and required skills. The method uses keyword matching via SQL
        ILIKE filters and prioritizes jobs in the same category.

        Args:
            job_id (str): The ID of the job for which similar jobs are being retrieved.
            limit (int): The maximum number of similar jobs to return.

        Returns:
            List[Job]: A list of Job objects deemed similar to the target job.
        """
        with self.get_session() as session:
            # Retrieve the target job
            target_job = session.query(JobsORM).get(job_id)
            if not target_job:
                return []

            # Extract significant keywords from title, description, and skills
            def extract_keywords(text: str) -> List[str]:
                words = re.findall(r"\b\w+\b", text.lower())
                return [word for word in words if len(word) > 3][:10]  # Limit to top 10 useful words

            title_keywords = extract_keywords(target_job.title)
            description_keywords = extract_keywords(target_job.description or "")
            skills_keywords = extract_keywords(" ".join(target_job.skills or []))

            combined_keywords = list(set(title_keywords + description_keywords + skills_keywords))

            # Build ILIKE conditions for keyword matching
            keyword_conditions = [
                or_(
                    JobsORM.title.ilike(f"%{kw}%"),
                    JobsORM.description.ilike(f"%{kw}%"),
                    JobsORM.skills.ilike(f"%{kw}%"),
                )
                for kw in combined_keywords[:8]  # Limit number of keyword ORs for performance
            ]

            # Query similar jobs based on category and keyword overlap
            similar_jobs_query = (
                session.query(JobsORM)
                .filter(
                    JobsORM.job_id != job_id,
                    JobsORM.status == JobStatusEnum.ACTIVE.value,
                    or_(
                        JobsORM.category == target_job.category,
                        *keyword_conditions
                    )
                )
                .order_by(
                    case(
                        (JobsORM.category == target_job.category, 0),
                        else_=1
                    ),
                    func.random()
                )
                .limit(limit)
            )

            similar_jobs = similar_jobs_query.all()
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

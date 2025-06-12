import asyncio
import inspect
from datetime import datetime, timezone
from typing import Optional, Any

from pydantic import Field, BaseModel
from sqlalchemy import or_

from src.controllers.admin.interfaces import AdminServiceInterface
from src.controllers.controller import error_handler
from src.database.models.jobs_model import Job, JobStatusEnum
from src.database.models.jobseeker_profile import JobSeekerProfile
from src.database.models.resume import JobSeekerCV
from src.database.models.users import RolesEnum
from src.database.sql.jobs_sql import JobsORM, ATSReportORM, JobApplicationORM, JobCategoryORM
from src.utils.route_helpers import get_controller, get_service


class JobRecommenderResult(BaseModel):
    profile: Any
    recommended_jobs: list


class AdminActionResult(BaseModel):
    __doc__ = """
    Standardized structure for returning results from admin service actions.

    This object is returned by all admin services and encapsulates the outcome of
    an operation, including whether it succeeded, a user-readable message, and
    optionally any resulting data or error details.

    Attributes:
        success (bool): Indicates whether the operation was successful.
        message (str): A human-readable message describing the result.
        data (Optional[Dict]): Additional payload data from the action (e.g., a report or entity info).
        errors (Optional[List[str]]): A list of errors encountered during the operation, if any.
    """
    success: bool
    message: str
    list_data: Optional[list[JobRecommenderResult]] = Field(default_factory=list)


class JobRecommendationService(AdminServiceInterface):
    __doc__ = """

    """
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.job_seekers_profile_controller = get_controller('job_seeker_profile')
        self.users_controller = get_controller('users')
        self.resume_controller = get_controller('resume')
        self._limit_recommended_per_jobseeker: int = 15
        self.logger = get_service('logger')()(self.__class__.__name__)
        self.__interface_map = {
            'recommend_jobs': self.all_jobseekers_recommendations_executor,
        }

    async def execute(self, action: str, *args, **kwargs):
        """
        Dynamically executes a method based on the provided action name.

        Args:
            action (str): The name of the method to execute (must be present in `_interface_schema`).
            *args: Positional arguments for the method.
            **kwargs: Keyword arguments for the method.

        Returns:
            Any: The result of the invoked method.

        Raises:
            ValueError: If the action does not exist in this service's schema
                        or if the found entry is not a callable method.
            RuntimeError: If an unexpected error occurs during the execution
                          of the target method.
        """
        try:
            method_to_execute = self.__interface_map[action]

            if method_to_execute is None:
                raise ValueError(f"Action '{action}' not found in {self.__class__.__name__}.")

            if inspect.iscoroutinefunction(method_to_execute):
                return await method_to_execute(*args, **kwargs)
            else:
                return method_to_execute(*args, **kwargs)

        # Catch specific exceptions that might be raised by the lookup or the method itself.
        except ValueError as e:
            # Re-raise the ValueError if it's one of the ones we explicitly raised.
            raise e
        except Exception as e:
            # Catch any other unexpected exceptions and wrap them in a RuntimeError.
            # Using 'from e' maintains the original exception's traceback, which is crucial for debugging.
            raise RuntimeError(f"Error executing action '{action}': {str(e)}") from e

    @error_handler
    async def all_jobseekers_recommendations_executor(self) -> AdminActionResult:
        """
            this returns a list of profiles that can be sent job recommendations
        :return:
        """
        job_seeker_profiles: list[JobSeekerProfile] = await self.job_seekers_profile_controller.list_profiles_by_role(
            role=RolesEnum.JOBSEEKER.value)

        profiles_we_can_send_recommendations = [prof for prof in job_seeker_profiles
                                                if prof.can_send_job_recommendations] if job_seeker_profiles else []
        if not profiles_we_can_send_recommendations:
            return AdminActionResult(success=False, message="Unable to find Profiles to recommend jobs for")

        errors = []
        success : list[JobRecommenderResult] = []
        for i in range(0, len(profiles_we_can_send_recommendations), 50):
            batch = profiles_we_can_send_recommendations[i:i + 50]
            tasks = [self.get_personalized_job_recommendations(profile=profile) for profile in batch]
            batch_results: list[Exception | JobRecommenderResult] = await asyncio.gather(*tasks, return_exceptions=True)
            for res in batch_results:
                if isinstance(res, Exception):
                    errors.append(res)
                else:
                    success.append(res)
        for error in errors:
            self.logger.error(error)

        # returns a list of Profiles and Recommended Jobs so the Admin Controller can send the Emails.
        return AdminActionResult(success=len(success) > 1,message="Job Recommendations Processed", list_data=success)


    @error_handler
    async def get_personalized_job_recommendations(self, profile: JobSeekerProfile) -> JobRecommenderResult:
        """
            For each Profile this Method Returns Jobs Of Interest.
        :param profile:
        :return:
        """
        resume = await self.resume_controller.get_primary_resume(user_id=profile.user_uid)
        if not resume:
            return []

        with self.session_factory() as session:

            query = self._get_base_job_query(session=session)
            applied_job_ids = self._get_applied_job_ids_by_ats_score(session=session, user_id=profile.user_uid)

            if applied_job_ids:
                # Removing all the jobs the JobSeeker already applied for.
                query = query.filter(JobsORM.job_id.notin_(applied_job_ids))

            # This applies a Profile and Resume Based Filter to the Query.
            self._apply_user_preferences(query=query, profile=profile, resume=resume)
            # This takes Jobs that the Job Seeker already applied for and try and find jobs matching those titles.
            similar_titles = self._get_similar_jobs_titles(session, applied_job_ids)
            if similar_titles:
                self._apply_similar_titles_filter(query, similar_titles)
            # This will recommended jobs that are similar to the ones the Job Seeker already applied for.
            # But also jobs that have the least number of applications already - and if they are
            # featured and posted recently
            jobs_orm_list = query.order_by(
                JobsORM.application_count.asc(),
                JobsORM.is_featured.desc(),
                JobsORM.posted_at.desc()
            ).limit(self._limit_recommended_per_jobseeker).all()
            recommended_list = [Job(**job.to_dict()) for job in jobs_orm_list if job] if jobs_orm_list else []
            _result_dict = JobRecommenderResult(profile=profile, recommended_jobs=recommended_list)
            return _result_dict

    @error_handler
    def _get_base_job_query(self, session):
        """this creates the initial job query that will be used to filter jobs based on user preferences"""
        return session.query(JobsORM).filter(
            JobsORM.status == JobStatusEnum.ACTIVE.value,
            JobsORM.expires_at > datetime.now(timezone.utc))

    @error_handler
    def _get_applied_job_ids_by_ats_score(self, session, user_id: str) -> list[str]:
        """
        Retrieves job IDs for jobs that the user has applied to, ordered by ATS score in descending order.

        This method joins job applications with their corresponding ATS reports to return a list of
        job IDs sorted by the highest ATS scores first. This allows prioritizing jobs where the
        user had better application matches.

        Args:
            session: Database session
            user_id (str): The ID of the user/jobseeker

        Returns:
            list[str]: List of job IDs ordered by ATS score (highest first)
        """
        applied_jobs =(session.query(JobApplicationORM)
            .join(ATSReportORM, JobApplicationORM.ats_report_id == ATSReportORM.ats_report_id)
            .filter(JobApplicationORM.user_id == user_id)
            .order_by(ATSReportORM.score.desc())
            .all())
        return [job.job_id for job in applied_jobs if job]


    @error_handler
    def _get_similar_jobs_titles(self, session, applied_job_ids: list[str]) -> list[str]:
        """
        Given Job ID's of the Jobs the JobSeeker Already Applied for extract the titles of those
        jobs then return them
        Finds Jobs Matching the Jobs the JobSeeker Already Applied for"""
        if not applied_job_ids:
            return []

        applied_jobs = session.query(JobsORM).filter(JobsORM.job_id.in_(applied_job_ids)).all()
        titles = [job.title for job in applied_jobs if job.title]
        return list(set(titles))  # Deduplicate

    @error_handler
    def _apply_user_preferences(self, query, profile: JobSeekerProfile, resume: JobSeekerCV):
        """
            Apply User Preferences takes Profiles and Resumes Into Account in order to match Jobs.
        :param query:
        :param profile:
        :param resume:
        :return:
        """

        if profile.job_titles_of_interest:
            title_conds = [JobsORM.title.ilike(f"%{title}%") for title in profile.job_titles_of_interest]
            query = query.filter(or_(*title_conds))

        if profile.industries_of_interest:
            # Supports Partial Matches Between Industries and Categories
            filters = []
            for value in profile.industries_of_interest:
                filters.append(JobCategoryORM.name.ilike(f"%{value}%"))
                filters.append(JobCategoryORM.slug.ilike(f"%{value}%"))
            query = query.join(JobsORM.category).filter(or_(*filters))

        location_conds = []
        if profile.location:
            location_conds.extend([
                JobsORM.city.ilike(f"%{profile.location}%"),
                JobsORM.province.ilike(f"%{profile.location}%")
            ])
        for loc in profile.locations_of_interest or []:
            location_conds.extend([
                JobsORM.city.ilike(f"%{loc}%"),
                JobsORM.province.ilike(f"%{loc}%")
            ])
        # noinspection DuplicatedCode
        if location_conds:
            query = query.filter(or_(*location_conds))

        if profile.remote_preference:
            query = query.filter(JobsORM.remote_policy.in_(["REMOTE", "HYBRID"]))

        if resume.skills:
            skill_conds = [cond for skill in resume.skills for cond in [
                JobsORM.required_skills.contains([skill]),JobsORM.preferred_skills.contains([skill])]]

            query = query.filter(or_(*skill_conds))

        if profile.expected_salary:
            query = query.filter(
                JobsORM.salary_min >= profile.expected_salary * 0.7,
                JobsORM.salary_max <= profile.expected_salary * 1.3
            )

    @error_handler
    def _apply_similar_titles_filter(self, query, similar_titles: list[str]):
        if similar_titles:
            title_conds = [JobsORM.title.ilike(f"%{title}%") for title in similar_titles]
            query = query.filter(or_(*title_conds))


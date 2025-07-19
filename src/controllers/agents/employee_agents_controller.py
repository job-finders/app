# src/controllers/agents.py
from typing import Optional

from src.agents.jobseeker.application_coach import (
    ApplicationCoachAgent,
    JobMatchInsights,
    ApplicationCoachInput
)
from src.agents.jobseeker.cover_letter import CoverLetterOutput, CoverLetterInput, CoverLetterAgent
from src.controllers.controller import Controllers, error_handler
from src.database.models import Job
from src.database.models.resume import JobSeekerCV
from src.database.models.users import User
from src.logger import init_logger
from src.utils.route_helpers import get_controller

class EmployeeAgentsController(Controllers):
    """
    Controller responsible for AI-assisted job matching, CV optimization, and cover letter generation for jobseekers.

    This controller interacts with user, resume, and job services to facilitate intelligent agent-based
    features such as:
      - Matching candidate profiles to jobs
      - Generating tailored cover letters
      - Optimizing CVs for better ATS (Applicant Tracking System) performance

    Dependencies:
        - `users_controller`: For fetching user information.
        - `resume_controller`: For fetching and managing CVs.
        - `job_search_controller`: For retrieving job details.
        - `ApplicationCoachAgent`: AI agent for job match analysis.
        - `CoverLetterAgent`: AI agent for generating tailored cover letters.
        - Logging and error handling decorators.

    Side Effects:
        - Logs important events (e.g., analysis or generation triggers).
        - Raises errors when users, jobs, or CVs are missing.
        - Delegates computation to agent services with async execution.

    Args:
        factory: Dependency injection factory used for controller/service instantiation.
    """

    def __init__(self, factory):
        """
        Initializes the EmployeeAgentsController and sets up logging.

        Args:
            factory: Dependency injection factory.
        """
        super().__init__(factory)
    

    def init_app(app: Flask):
        super().init_app(app=app)



    @error_handler
    async def analyze_job_match(
            self,
            user_id: str,
            job_id: str,
            cv_id: Optional[str] = None,
            cover_letter: Optional[str] = None
    ) -> JobMatchInsights:
        """
        Analyzes how well a candidate matches a specific job

        Args:
            user_id: ID of the jobseeker
            job_id: ID of the job to match against
            cv_id: If CV Selected run match for the Selected CV
            cover_letter: Optional cover letter text

        Returns:
            JobMatchInsights with analysis and recommendations

        """
        self.logger.info(f"Analyzing job match for user: {user_id}, job: {job_id}")
        users_controller = get_controller('users')
        job_search_controller = get_controller('jobs_search')
        resume_controller = get_controller('resume')

        user: User = await users_controller.get_user_by_uid(uid=user_id)
        job: Job = await job_search_controller.get_job_by_id(job_id=job_id)
        if cv_id is None:
            resume: JobSeekerCV = await resume_controller.get_primary_resume(user_id=user_id)
        else:
            resume: JobSeekerCV = await resume_controller.get_cv_by_id(cv_id=cv_id)

        if user is None:
            raise ValueError(f"User with ID {user_id} not found")
        if job is None:
            raise ValueError(f"Job with ID {job_id} not found")
        if resume is None:
            raise ValueError("Candidate doesn't have a CV uploaded")

        # Prepare agent input
        input_data = ApplicationCoachInput(
            job_post=job.ats_description,
            cv_text=resume.ats_description,
            cover_letter=cover_letter
        )

        # Run the agent
        agent = ApplicationCoachAgent(user_id=user_id)
        # noinspection PyTypeChecker
        return await agent.run(input_model=input_data)

    @error_handler
    async def generate_cover_letter(
            self,
            user_id: str,
            job_id: str,
            cv_id: str,
            tone: Optional[str] = "professional"
    ) -> CoverLetterOutput:
        """
        Generates a tailored cover letter for a specific job application
            :param user_id:
            :param job_id:
            :param tone:
            :param cv_id:

        Returns:
            CoverLetterOutput with generated cover letter sections
        """
        self.logger.info(f"Generating cover letter for user: {user_id}, job: {job_id}")
        users_controller = get_controller('users')
        job_search_controller = get_controller('jobs_search')
        resume_controller = get_controller('resume')

        user: User = await users_controller.get_user_by_uid(uid=user_id)
        job: Job = await job_search_controller.get_job_by_id(job_id=job_id)
        if cv_id is None:
            resume: JobSeekerCV = await resume_controller.get_primary_resume(user_id=user_id)
        else:
            resume: JobSeekerCV = await resume_controller.get_cv_by_id(cv_id=cv_id)

        if user is None:
            raise ValueError(f"User with ID {user_id} not found")

        if job is None:
            raise ValueError(f"Job with ID {job_id} not found")

        if resume is None:
            raise ValueError("Candidate doesn't have a CV uploaded")

        # Prepare agent input
        input_data = CoverLetterInput(
            job_description=job.ats_description,
            cv_text=resume.ats_description,
            tone=tone
        )
        # Run the agent
        agent = CoverLetterAgent(user_id=user_id)
        result = await agent.run(input_model=input_data)
        return result


    async def optimize_primary_cv(self, primary_resume: JobSeekerCV):
        """
            with the resume please run an Agent which will optimize the CV in order to rank higher - based on ATS Ranking
        :param user_uid:
        :return:
        """
        pass

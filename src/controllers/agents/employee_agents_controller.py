# src/controllers/agents.py
from typing import Optional

from agents.jobseeker.cover_letter import CoverLetterOutput, CoverLetterInput, CoverLetterAgent
from database.models import Job
from database.models.resume import JobSeekerCV
from database.sql.users import UserORM
from src.controllers.controller import Controllers, error_handler
from src.agents.jobseeker.application_coach import (
    ApplicationCoachAgent,
    JobMatchInsights,
    ApplicationCoachInput
)
from src.logger import init_logger
from src.database.models.users import User
from src.main import job_search_controller, users_controller, resume_controller



class EmployeeAgentsController(Controllers):
    def __init__(self):
        super().__init__()
        self.logger = init_logger("EmployeeAgentsController")


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


# src/controllers/agents.py
from typing import Optional, List
from flask import Flask

from src.database.models import JobSeekerProfile, JobApplication, Job, JobSeekerCV, CandidateBenchmarkReport

from src.controllers.controller import Controllers, error_handler
from src.controllers.company import CompanyController
from src.controllers.jobs import JobsWorkflowController, JobsSearchController
from src.controllers.jobseekers import JobSeekerProfilesController
from src.controllers.resumes import ResumeController

from src.agents.employer.candidate_benchmark import CandidateBenchmarkAgent, UserMode
from src.utils.route_helpers import get_controller


class CandidateBenchMarkController(Controllers):
    """
    Controller for benchmarking candidates against job requirements from dual perspectives:
    - Employers: Evaluate candidate suitability for hiring decisions
    - Employees: Assess job fit and career development opportunities

    Features:
    - Comprehensive candidate-job matching analysis
    - Dual-perspective insights (employer/employee)
    - Career development suggestions for employees
    - Hiring risk assessment for employers
    - CV optimization recommendations

    Dependencies:
    - `users_controller`: User profile data
    - `resume_controller`: CV/Resume handling
    - `jobs_search_controller`: Job details
    - `job_application_controller`: Application context
    - `CandidateBenchmarkAgent`: Core benchmarking agent

    Side Effects:
    - Logs benchmarking requests and results
    - Raises errors for missing data
    - Async execution of agent operations
    """

    def __init__(self, factory):
        super().__init__(factory)

    def init_app(self, app: Flask):
        super().init_app(app=app)

    @error_handler
    async def benchmark_for_employer(
        self,
        job_application_id: str,
        employer_id: str
    ) -> CandidateBenchmarkReport | None:
        """
        Benchmark a candidate from employer's perspective for hiring decisions
        
        Args:
            job_application_id: ID of the job application to evaluate
            employer_id: ID of the employer performing the evaluation
            
        Returns:
            CandidateBenchmarkReport with hiring insights and risk assessment
        """
        self.logger.info(f"Employer benchmarking for application: {job_application_id}")
        
        # Get controllers

        job_workflow_controller: JobsWorkflowController = get_controller('jobs_workflow')
        job_search_controller: JobsSearchController = get_controller('jobs_search')
        resume_controller: ResumeController = get_controller('resume')
        company_controller: CompanyController = get_controller("company")
        jobseeker_profile_controller: JobSeekerProfilesController = get_controller("job_seeker_profile")
        # Fetch application data
        application: JobApplication = await job_search_controller.get_application_by_id(
            application_id=job_application_id)

        if not application:
            return None

        job: Job = await job_search_controller.get_job_by_id(job_id=application.job_id)
        candidate_cv: JobSeekerCV = await resume_controller.get_cv_by_id(application.cv_id)
        candidate_profile: JobSeekerProfile = await jobseeker_profile_controller.get_profile_by_uid(
            user_uid=candidate_cv.user_uid)
        
        # Validate data
        if not all([application, job, candidate_cv, candidate_profile]):
            missing = [name for name, val in [
                ('application', application),
                ('job', job),
                ('candidate_cv', candidate_cv),
                ('candidate_profile', candidate_profile)
            ] if not val]
            raise ValueError(f"Missing data: {', '.join(missing)}")
        
        # Combine profile and CV data
        candidate_data = (
            f"## Candidate Profile\n"
            f"Names: {candidate_profile.full_names}\n"
            f"Summary: {candidate_profile.profile_summary or 'N/A'}\n"
            f"Skills: {', '.join(candidate_cv.skills) if candidate_cv.skills else 'N/A'}\n\n"
            f"## Candidate CV\n{candidate_cv.ats_description}"
        )
        
        # Prepare agent input
        input_data = CandidateBenchmarkAgent.Input(
            cv_text=candidate_data,
            job_post=job.ats_description,
            mode=UserMode.EMPLOYER
        )
        
        # Execute agent
        agent = CandidateBenchmarkAgent(user_id=employer_id)
        # noinspection PyTypeChecker
        return await agent.run(input_model=input_data)

    @error_handler
    async def benchmark_for_employee(
            self,
            user_id: str,
            job_id: str,
            cv_id: Optional[str] = None
    ) -> CandidateBenchmarkReport | None:
        """
        Benchmark job fit from employee's perspective for career development

        Args:
            user_id: ID of the job seeker
            job_id: ID of the target job
            cv_id: Optional specific CV ID to use (default: primary CV)

        Returns:
            CandidateBenchmarkReport with career development insights
        """
        self.logger.info(f"Employee benchmarking - User: {user_id}, Job: {job_id}")
        # Get consistent controllers
        job_search_controller: JobsSearchController = get_controller('jobs_search')
        resume_controller: ResumeController = get_controller('resume')
        jobseeker_profile_controller: JobSeekerProfilesController = get_controller("job_seeker_profile")

        # Fetch data using consistent patterns
        job: Job = await job_search_controller.get_job_by_id(job_id=job_id)
        candidate_profile: JobSeekerProfile = await jobseeker_profile_controller.get_profile_by_uid(user_uid=user_id)

        # Get CV - use primary if none specified
        cv: JobSeekerCV = await resume_controller.get_cv_by_id(cv_id) if cv_id \
            else await resume_controller.get_primary_resume(user_id)

        # Validate all required data exists
        if not job:
            self.logger.error(f"Job {job_id} not found")
            return None

            raise ValueError(f"Job {job_id} not found")
        if not candidate_profile:
            self.logger.error(f"JobSeekerProfile for user {user_id} not found")
            return None

        if not cv:
            self.logger.error(f"CV for user {user_id} not found")
            return None

        # Combine profile and CV data (consistent with employer method)
        candidate_data = (
            f"## Candidate Profile\n"
            f"Names: {candidate_profile.full_names}\n"
            f"Summary: {candidate_profile.profile_summary or 'N/A'}\n"
            f"Skills: {', '.join(cv.skills) if cv.skills else 'N/A'}\n\n"
            f"## Candidate CV\n{cv.ats_description}"
        )

        # Prepare agent input
        input_data = CandidateBenchmarkAgent.Input(
            cv_text=candidate_data,
            job_post=job.ats_description,
            mode=UserMode.EMPLOYEE
        )

        # Execute agent
        agent = CandidateBenchmarkAgent(user_id=user_id)
        return await agent.run(input_model=input_data)

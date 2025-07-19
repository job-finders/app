# src/controllers/agents.py
from typing import Optional, List
from flask import Flask
from src.agents.employer.candidate_benchmark import CandidateBenchmarkAgent, UserMode
from src.controllers.agents.ats_keywords_minig_tools import IndustryTaxonomyTool, PeerJobsTool, ParsedCVsTool
from src.controllers.controller import Controllers, error_handler, get_controller
from src.database.models import Job, User, JobSeekerCV, JobApplication
from src.database.models.agent_models import CandidateBenchmarkReport

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
    
    @staticmethod
    def init_app(app: Flask):
        super().init_app(app=app)

    @error_handler
    async def benchmark_for_employer(
        self,
        job_application_id: str,
        employer_id: str
    ) -> CandidateBenchmarkReport:
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
        app_controller = get_controller('job_application')
        job_controller = get_controller('jobs_search')
        resume_controller = get_controller('resume')
        user_controller = get_controller('users')
        
        # Fetch application data
        application: JobApplication = await app_controller.get_application_by_id(job_application_id)
        job: Job = await job_controller.get_job_by_id(application.job_id)
        candidate_cv: JobSeekerCV = await resume_controller.get_cv_by_id(application.cv_id)
        candidate_profile: User = await user_controller.get_user_by_uid(application.candidate_id)
        
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
            f"Name: {candidate_profile.full_name}\n"
            f"Summary: {candidate_profile.profile_summary or 'N/A'}\n"
            f"Skills: {', '.join(candidate_profile.skills) if candidate_profile.skills else 'N/A'}\n\n"
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
        return await agent.run(input_model=input_data)

    @error_handler
    async def benchmark_for_employee(
        self,
        user_id: str,
        job_id: str,
        cv_id: Optional[str] = None
    ) -> CandidateBenchmarkReport:
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
        
        # Get controllers
        user_controller = get_controller('users')
        job_controller = get_controller('jobs_search')
        resume_controller = get_controller('resume')
        
        # Fetch data
        user: User = await user_controller.get_user_by_uid(user_id)
        job: Job = await job_controller.get_job_by_id(job_id)
        cv: JobSeekerCV = await resume_controller.get_cv_by_id(cv_id) if cv_id \
            else await resume_controller.get_primary_resume(user_id)
        
        # Validate data
        if not user:
            raise ValueError(f"User {user_id} not found")
        if not job:
            raise ValueError(f"Job {job_id} not found")
        if not cv:
            raise ValueError(f"No CV found for user {user_id}")
        
        # Combine profile and CV data
        candidate_data = (
            f"## Candidate Profile\n"
            f"Summary: {user.profile_summary or 'N/A'}\n"
            f"Skills: {', '.join(user.skills) if user.skills else 'N/A'}\n"
            f"Experience: {user.work_experience or 'N/A'}\n\n"
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
        
# src/controllers/agents.py
from datetime import datetime, timedelta, timezone

from src.agents.employer import JobPostIntelligenceAgent

from src.database.models.agent_models import JobPostInsights

from src.controllers.controller import Controllers, error_handler
from src.agents.employer import (EnhanceJobPostOutput, EnhanceJobPostInput, EnhanceJobPostAgent, JobSummaryInput,
JobSummaryAgent, JobSummaryOutput)

from src.database.models import Job
from src.database.sql.jobs_sql import JobsORM

class EmployerAgentsController(Controllers):
    def __init__(self):
        super().__init__()

    @error_handler
    async def enhance_job_post(self, user_id: str, input_data: dict) -> EnhanceJobPostOutput:
        self.logger.info(f"Enhancing job post for user: {user_id}")
        input_model = EnhanceJobPostInput(**input_data)

        # Run the agent
        agent = EnhanceJobPostAgent(user_id=user_id)
        result = await agent.run(input_model=input_model)

        # Set default expiration dates if not provided by agent
        if not result.expires_at:
            result.expires_at = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
        if not result.application_deadline:
            result.application_deadline = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    @error_handler
    async def analyze_job_post(self, user_id: str, job_id: str) -> JobPostInsights:
        self.logger.info(f"Analyzing job post for user: {user_id}, job: {job_id}")

        # Fetch the job from database
        with self.get_session() as session:
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
                raise ValueError(f"Job with ID {job_id} not found")
            job = Job(**job_orm.to_dict())
            # Verify user has access to this job
            if job.user_id != user_id:
                raise PermissionError("User not authorized to access this job")

            # Run the analysis agent
            agent = JobPostIntelligenceAgent(user_id=user_id)

            return await agent.run(input_model=job)

    @error_handler
    async def create_job_summary(self, user_id: str, job_id: str) -> JobSummaryOutput:
        """     
            Create a summary for a job post using the JobSummaryAgent.    
        """
        self.logger.info(f"Creating job summary for user: {user_id}, job: {job_id}")

        # Fetch the job from database
        with self.get_session() as session:
            job_orm = session.get(JobsORM, job_id)
            if not job_orm:
                raise ValueError(f"Job with ID {job_id} not found")
            job = Job(**job_orm.to_dict())
            # Verify user has access to this job
            # if job.user_id != user_id:
            #     raise PermissionError("User not authorized to access this job")

            # Run the summary agent
            agent = JobSummaryAgent(user_id=user_id)
            input_model = JobPostSummaryInput(ats_description=job.ats_description)
            job_summary =  await agent.run(input_model=input_model)
            
            job_orm.summary = job_summary.summary
            job_orm.seo_description = job_summary.seo_description


import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from Levenshtein import ratio as levenstein_ratio
from flask import Flask
from pydantic import ValidationError
from requests import RequestException
from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import joinedload

from src.controllers.controller import Controllers
from src.controllers.controller import error_handler
from src.database.models.employer_models import Employer
from src.database.models.jobs_model import (Job, JobApplication, SavedJob, JobStatistics, StatusCounts,
                                            ApplicationMetrics, ApplicationFunnelStats, BulkImportResult,
                                            TalentPoolReport, JobApplicationDashboard, ATSReport,JobEditableFields,
                                            JobApplicationStatusEnum, JobApprovalStatusEnum, JobStatusEnum)
from src.database.models.jobseeker_profile import JobSeekerProfile
from src.database.sql.company import CompanyORM
from src.database.sql.jobs_sql import (JobsORM, SavedJobORM, JobApplicationORM, JobApprovalRequestORM,ATSReportORM)
from src.database.sql.jobseeker_profile import JobSeekerProfileORM
from src.database.sql.resume import JobSeekerCVORM
from src.database.sql.users import UserORM


class JobsWorkflowController(Controllers):
    """sumary_line
    
    Keyword arguments:
    argument -- description
    Return: return_description
    """
    
    
    def __init__(self, factory):
        super().__init__(factory)

    def init_app(self, app: Flask):
        super().init_app(app=app)


    # Add caching for frequent job ownership checks
    @error_handler

    @error_handler
    async def update_job(self, job_id: str, updated_job: JobEditableFields | Job) -> Job | None:
        """Updates the job matching the job_id"""
        if not (isinstance(job_id, str) and job_id.strip()):
            return None
        if not isinstance(updated_job, (Job, JobEditableFields)):
            return None

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

            return Job(**job_orm.to_dict()) if job_orm else None

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
    async def de_activate_job_listing(self, job_id: str, reviewer_id: str, validation_result: Optional[dict] = None) -> Job | None:
        """Mark job as inactive by setting expiration date to past"""
        if not (isinstance(job_id, str) and job_id.strip()):
            return None
        if not (isinstance(reviewer_id, str) and reviewer_id.strip()):
            return None
        self.logger.info(f"Updating Job_ID: {job_id} Job Approval Status to {JobApprovalStatusEnum.CLOSED.value}")
        self.logger.info(f"The Reviewer : {reviewer_id} Arrived at this Review : {validation_result}")
        return await self.update_approval_status(job_id=job_id, decision=JobStatusEnum.CLOSED.value, reviewer_id=reviewer_id)

    @error_handler
    async def activate_job_listing(self, job_id: str, reviewer_id: str, validation_result: Optional[dict] = None) -> Job | None:
        """Activate job listing by resetting expiration date"""
        if not (isinstance(job_id, str) and job_id.strip()):
            return None
        if not (isinstance(reviewer_id, str) and reviewer_id.strip()):
            return None
        self.logger.info(f"Updating Job_ID: {job_id} Job Approval Status to {JobApprovalStatusEnum.ACTIVE.value}")
        self.logger.info(f"The Reviewer : {reviewer_id} Arrived at this Review : {validation_result}")
        return await self.update_approval_status(job_id=job_id, decision=JobStatusEnum.ACTIVE.value,
        reviewer_id=reviewer_id,validation_result=validation_result)

    @error_handler
    async def reject_job_listing(self, job_id: str, reviewer_id: str, validation_result: Optional[dict] = None) -> Job | None:
        """This will mark the job in question as rejected"""
        if not (isinstance(job_id, str) and job_id.strip()):
            return None
        if not (isinstance(reviewer_id, str) and reviewer_id.strip()):
            return None
        self.logger.info(f"Updating Job_ID: {job_id} Job Approval Status to {JobApprovalStatusEnum.REJECTED.value}")
        self.logger.info(f"The Reviewer : {reviewer_id} Arrived at this Review : {validation_result}")
        return await self.update_approval_status(job_id=job_id,decision=JobApprovalStatusEnum.REJECTED.value,
        reviewer_id=reviewer_id,validation_result=validation_result)


    @error_handler
    async def _create_job(self, job: JobEditableFields | Job) -> Job | None:
        """Create new job listing"""
        if not isinstance(job, (Job, JobEditableFields)):
            self.logger.info(F"Malformed Job Variable when creating a job")
            return None

        self.logger.info(f"Will now create the following job : {job.title}")
        with self.get_session() as session:
            # Convert Pydantic model to ORM-compatible dic
            # t
            self.logger.info("Will Run Database lookup")
            job_existing = session.query(JobsORM).filter_by(job_id=job.job_id).first()
            self.logger.info("will now check if job Exist")

            if isinstance(job_existing, JobsORM):
                return None

            self.logger.info(f"Will now dump model : {job}")
            try:
                job_orm = JobsORM(**job.model_dump(
                    exclude={'applications', "saved_jobs", "category", "ats_reports", "approval_request",
                             "version_history", "company"}))
            except Exception as e:
                self.logger.error(str(e))
                return None

            session.add(job_orm)
            self.logger.info(f"now added job to session : {job_orm.to_dict()}")
            session.refresh(job_orm)  # Get ID and other defaults
            return Job(**job_orm.to_dict())

    # In JobsController
    @error_handler
    async def post_job_employer(self, employer: Employer, job_data: Job | JobEditableFields) -> Job | None:
        """
            This create a job draft post for a specific employer
            Perform Extra Employer Based Checks 
        Keyword arguments:
        argument -- description
        Return: return_description
        """
        if not (isinstance(job_data, (Job, JobEditableFields)) and isinstance(employer, Employer)):
            return None
        
        self.logger.info(f"Employee : {employer.employer_id} Started creating the Job Titled : {job_data.title}")

        # if not employer.is_verified:
        #     self.logger.info(f"Employer : {employer.employer_id} is not verified")
        #     return None

        job_data.employer_id = employer.employer_id
        return await self._create_job(job=job_data)

    @error_handler
    async def validate_job_post(self, job: Job) -> dict:
        """Validate job post completeness and employer credibility"""
        if not isinstance(job, Job):
            return {}

        self.logger.info(f"Started Job validation Heuristics on the following Job : {job.title} Job ID : {job.job_id}")
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'requires_approval': False,
            'quality_metrics': {
                'completeness_score': job.job_completeness_score,
                'readability_ok': job.readability_is_ok,
                'overall_quality': job.job_quality_score
            }
        }

        # Basic field validation
        required_fields = ['title', 'city', 'province', 'country', 'category']
        for field in required_fields:
            if not getattr(job, field):
                validation_result['errors'].append(f"Missing required field: {field}")

        # Quality-based validation
        if job.job_completeness_score < 6:
            validation_result['errors'].append(
                "Job post is incomplete. Please add more details (required skills, experience level, salary range)")
        elif job.job_completeness_score < 8:
            validation_result['warnings'].append("Consider adding more details to improve job visibility")

        if not job.readability_is_ok:
            validation_result['warnings'].append(
                "Job description may be difficult to read. Consider simplifying the language")

        if job.job_quality_score < 50:
            validation_result['requires_approval'] = True
            validation_result['errors'].append("Job quality score too low - requires manual review")

        elif job.job_quality_score < 70:
            validation_result['warnings'].append("Low quality score may reduce job visibility")

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
        if not isinstance(job, Job):            
            self.logger.info(f"Malformed Job Instance when adding job - to job post workflow")
            return None

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

            self._create_approval_request(draft_orm)

            # Step 5: Approval check
            validation = await self.validate_job_post(Job(**draft_orm.to_dict()))
            session.commit()

        if validation['requires_approval']:
            # IF we are here then the job requires admin approval
            job = await self.update_approval_status(job_id=draft_orm.job_id, status=JobApprovalStatusEnum.PENDING.value)
        else:
            job = await self.update_approval_status(job_id=draft_orm.job_id, status=JobApprovalStatusEnum.APPROVED.value)

        return job

    @error_handler
    def flag_job_post(self, job_id: str, reason: str, reporter_id: str) -> Job | None:
        """
            Could be triggered by Admin - or System.
        :param job_id:
        :param reason:
        :param reporter_id:
        :return:
        """
        if not (isinstance(job_id, str) and job_id.strip()):
            self.logger.error("Invalid or None Existent Job ID - When running flag_job_post")
            return None

        if not (isinstance(reporter_id, str) and reporter_id.strip()):
            self.logger.error("Invalid or None Existent Reporter ID- When running flag_job_post")
            return None
        
        with self.get_session() as session:
            job = session.query(JobsORM).get(job_id)
            if not job:
                return None
            if not job.approval_request:
                request = JobApprovalRequestORM(
                    requested_by=reporter_id,
                    job_id=job_id,
                    status=JobApprovalStatusEnum.FLAGGED.value,
                    feedback=reason
                )
                session.add(request)
            else:
                job.approval_request.status = JobApprovalStatusEnum.FLAGGED.value
                job.approval_request.review_notes = reason

            session.commit()
            return job

    @error_handler
    async def save_job_for_user(self, user_id: str, job_id: str) -> None|SavedJob :
        """Save a job to a user's saved list with validation"""
        if not(isinstance(user_id, str) and user_id.strip()):
            self.logger.error("Malformed User ID when saving job for user")
            return None

        if not(isinstance(job_id, str) and job_id.strip()):
            self.logger.error("Malformed Job ID when saving job for user")
            return None

        with self.get_session() as session:
            # Validate both user and job exist
            user_exists = session.query(session.query(UserORM).filter_by(user_id=user_id).exists()).scalar()
            job_exists = session.query(session.query(JobsORM).filter_by(job_id=job_id).exists()).scalar()

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
        if not(isinstance(user_id, str) and user_id.strip()):
            return False
        if not (isinstance(job_id, str) and job_id.strip()):
            return False

        with self.get_session() as session:
            # Find the saved job entry in the saved_jobs table
            saved_job_orm = session.query(SavedJobORM).filter_by(user_id=user_id, job_id=job_id).first()

            if not saved_job_orm:
                return  False

            # Remove the saved job entry from the database
            session.delete(saved_job_orm)
            return True

    @error_handler
    async def delete_job(self, job_id: str) -> bool:
        """Permanently delete a job listing and its dependencies"""
        if not (isinstance(job_id, str) and job_id.strip()):
            return False
        
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
                        (JobsORM.status == JobStatusEnum.ACTIVE.value) & (JobsORM.expires_at > func.now())
                        # Changed here

                    )
                ).label('current_active_jobs')
            ).one()
            # Additional queries
            category_counts = dict(session.query(JobsORM.category,func.count(JobsORM.job_id)).group_by(JobsORM.category).all())
            recent_jobs = (session.query(func.count(JobsORM.job_id)).filter(JobsORM.posted_at >= datetime.now(timezone.utc) - timedelta(days=30)).scalar() or 0)

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

    @error_handler
    def _generate_summary_background(self, application_id: str):
            """Background task for AI summary generation"""
            if not(isinstance(application_id, str) and application_id.strip()):
                return None

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
        if not(isinstance(application_id, str) and application_id.strip()):
            return None

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

        if not(isinstance(job_id, str) and job_id.strip()):
            return None

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
    async def generate_application_review_summary(self, application_id: str) -> str | None:
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
        if not(isinstance(application_id, str) and application_id.strip()):
            return None
        
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

    @error_handler
    async def detect_duplicate_jobs(self, job: Job) -> list[Job]:
        """Identify similar existing jobs"""

        if not isinstance(job, Job):
            return []

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
    def _calculate_title_similarity(title1: str, title2: str) -> float | None:
        """Calculate title similarity using Levenshtein distance"""
        
        if not (isinstance(title1, str) and isinstance(title2, str)):
            return None
        title1 = title1.strip()
        title2 = title2.strip()

        return levenstein_ratio(title1.lower(), title2.lower())

    async def _auto_categorize_job(self, title: str, description: str) -> str | None:
        """Heuristically categorize a job based on title and description."""
        if not (isinstance(title, str) and title.strip()):
            return None
        title = title.strip()
        if not (isinstance(description, str) and description.strip()):
            return None
        description = description.strip()

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


    def _create_approval_request(self, draft_orm: JobsORM) -> None:
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
            # Once the Employer edits the job which was flagged the status will switch to pending
            # and will be legible for rechecking job to see if it meets requirements
            approval_request = JobApprovalRequestORM(
                job_id=draft_orm.job_id,
                token=approval_token,
                token_expires=token_expiration,
                requested_by=draft.company.company_id,
                approvers=[u.user_id for u in approvers],
                status=JobApprovalStatusEnum.FLAGGED.value
            )
            session.add(approval_request)
            # This means the employer needs to be aware of the reasons why their job was flagged
            draft_orm.status = JobStatusEnum.NEEDS_ATTENTION.value
            session.commit()

            self.logger.info(f"Sent approval request for job {draft_orm.job_id} to {len(approvers)} approvers")


        # EMPLOYER DASHBOARDS AND RELATED METHODS


    @error_handler
    async def get_company_analytics_dashboard(self, company_id: str) -> JobApplicationDashboard:
        """Employer dashboard with advanced hiring analytics
        This dashboard can be shown to the Employer.
        """
        self.logger.info("Started running : get_company_analytics_dashboard")
        if not (isinstance(company_id, str) and company_id.strip()):
            self.logger.error(f"Error Invalid Company ID")
            return None

        with self.get_session() as session:
            # Get all jobs for this employer
            jobs = session.execute(
                select(JobsORM.job_id)
                .where(JobsORM.company_id == company_id)
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
        """calculate average ATS Score for ATS Reports for a Specific Job"""
        with self.get_session() as session:
            result = session.execute(
                select(func.avg(ATSReportORM.score))
                .where(ATSReportORM.job_id.in_(job_ids))
            )
            return result.scalar() or 0.0

    async def _calculate_pipeline_metrics(self, job_ids: list[str]) -> dict[str, float]:
        """Calculate Job Applications Pipeline Metrics"""
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
    async def generate_talent_pool_report(self, employer_id: str) -> TalentPoolReport | None:
        """Generate comprehensive talent pool analysis"""
        self.logger.info("Started Running : generate_talent_pool_report")
        if not (isinstance(employer_id, str) and employer_id.strip()):
            self.logger.error("Invalid Employer ID")
            return None


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

    async def _get_average_time_to_hire(self, employer_id: str) -> float | None:
        """Calculate average time from application to hire in days"""
        self.logger.info("Started Running : _get_average_time_to_hire")
        if not (isinstance(employer_id, str) and employer_id.strip()):
            self.logger.error("Invalid Employer ID")
            return None

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
        self.logger.info("Started Running : _generate_candidate_comparison")
        if not (isinstance(employer_id, str) and employer_id.strip()):
            self.logger.error("Invalid Employer ID")
            return []

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
    async def _parse_salary(value: str) -> float | None:
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
        """Get jobs needing admin approval - fetch featured jobs first"""
        self.logger.info("Started Running: get_pending_approvals")

        with self.get_session() as session:
            # Query for pending approval jobs with featured priority
            jobs = (
                session.query(JobsORM).join(JobApprovalRequestORM).filter(
                    JobApprovalRequestORM.status == JobApprovalStatusEnum.PENDING.value
                ).order_by(
                    JobsORM.is_featured.desc(),  # Featured jobs first
                    JobsORM.created_at.desc()    # Then newest first
                ).options(joinedload(JobsORM.approval_request)).limit(100).all()  # Eager load relationship
            )

            #TODO- Consider including approval requssts with the job in this response
            return [Job(**job.to_dict()) for job in jobs if job] if jobs else []

    def format_validation_feedback(self, validation_result: dict) -> str:
        """Convert validation results into human-readable feedback string."""
        self.logger.info("Started Running : format_validation_feedback")
        lines = []

        if not validation_result:
            return "No validation feedback available."

        if validation_result.get("errors"):
            lines.append("❌ Errors:")
            lines.extend(f" - {err}" for err in validation_result["errors"])
            lines.append("")  # spacer

        if validation_result.get("warnings"):
            lines.append("⚠️ Warnings:")
            lines.extend(f" - {warn}" for warn in validation_result["warnings"])
            lines.append("")

        if validation_result.get("quality_metrics"):
            qm = validation_result["quality_metrics"]
            lines.append("📊 Quality Metrics:")
            lines.append(f" - Completeness Score: {qm.get('completeness_score', 'N/A')}/10")
            lines.append(f" - Readability OK: {'Yes' if qm.get('readability_ok') else 'No'}")
            lines.append(f" - Overall Quality Score: {qm.get('overall_quality', 'N/A')}/100")
            lines.append("")

        return "\n".join(lines).strip()

    @error_handler
    async def update_approval_status(self, job_id: str, decision: str, reviewer_id: str,
                                     validation_result: Optional[dict] = None) -> Job | None:
        """Update job approval status (Admin only)

        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'requires_approval': False,
            'quality_metrics': {
                'completeness_score': job.job_completeness_score,
                'readability_ok': job.readability_is_ok,
                'overall_quality': job.job_quality_score
            }
        }
        """
        self.logger.info("Started Running : update_approval_status")
        if not(isinstance(job_id, str) and job_id.strip()):
            return None

        if not (isinstance(decision, str) and decision.strip()):
            return None
        if not (isinstance(reviewer_id, str) and reviewer_id.strip()):
            return None

        with self.get_session() as session:
            job = session.query(JobsORM).get(job_id)
            request = session.query(JobApprovalRequestORM).filter_by(job_id=job_id).first()

            if validation_result:
                # Taking validation results so we format it in a way that can be added to feedback
                request.feedback = self.format_validation_feedback(validation_result)

            if decision.casefold() == JobApprovalStatusEnum.APPROVED.value:
                job.status = JobStatusEnum.ACTIVE.value
                request.status = JobApprovalStatusEnum.APPROVED.value


            elif decision.casefold() == JobApprovalStatusEnum.REJECTED.value:
                job.status = JobStatusEnum.ARCHIVED.value
                request.status = JobApprovalStatusEnum.REJECTED.value

            elif decision.casefold() == JobApprovalStatusEnum.PENDING.value:
                request.status = JobApprovalStatusEnum.PENDING.value
                job.status = JobStatusEnum.PENDING_APPROVAL.value
            elif decision.casefold() == JobApprovalStatusEnum.FLAGGED.value:

                request.status = JobApprovalStatusEnum.FLAGGED.value
                job.status = JobStatusEnum.NEEDS_ATTENTION.value

            request.reviewer_id = reviewer_id
            request.reviewed_at = datetime.now(timezone.utc)

            session.commit()
            return Job(**job.to_dict())


    @error_handler
    async def find_potential_duplicates(self, job: Job) -> list[Job]:
        """Advanced duplicate detection using multiple criteria"""
        self.logger.info("Started Find potential Job Duplicates detection")
        if not isinstance(job, Job):
            return None

        with self.get_session() as session:
            duplicates_orm_list = session.query(JobsORM).filter(
                and_(
                    func.similarity(JobsORM.title, job.title) > 0.7,
                    func.similarity(JobsORM.description, job.description) > 0.7,
                    JobsORM.company_id == job.company_id,
                    JobsORM.location == job.location,
                    func.abs(JobsORM.salary_min - job.salary_min) < 2000)
                    ).order_by(JobsORM.posted_at.desc()).limit(10).all()

            return [Job(**job.to_dict()) for job in duplicates_orm_list if job] if duplicates_orm_list else []

    @error_handler
    async def update_draft_application(self, application_id: str, updated_data: dict) -> None:
        """will take a draft job application and update it."""
        self.logger.info("Started update of draft application")
        if not (isinstance(application_id, str) and application_id.strip()):
            self.logger.error("Application_id contains invalid data")
            return None

        with self.get_session() as session:
            application_orm: JobApplicationORM = (
                session.query(JobApplicationORM)
                .filter_by(application_id=application_id)
                .first()
            )

            if application_orm and application_orm.application_stage == "draft":
                for key, value in updated_data.items():
                    setattr(application_orm, key, value)
            session.commit()
            self.logger.info("Updated draft application")
            return None
    



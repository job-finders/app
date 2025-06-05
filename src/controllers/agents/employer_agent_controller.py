# src/controllers/agents.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from src.agents.employer.candidate_benchmark import JobPostSummaryInput
from src.agents.employer.document_verifications import DocumentVerificationInput, DocumentVerificationAgent, \
    DocumentVerificationOutPut
from src.agents.employer import JobPostIntelligenceAgent



from src.database.models.agent_models import JobPostInsights

from src.controllers.controller import Controllers, error_handler
from src.agents.employer import (EnhanceJobPostOutput, EnhanceJobPostInput, EnhanceJobPostAgent, JobSummaryInput,
JobSummaryAgent, JobSummaryOutput)

from src.database.models import Job
from src.database.sql.jobs_sql import JobsORM
from src.database.sql.company import CompanyORM, CompanyVerificationDocumentORM, CompanyCIPCORM, \
    AIBasedDocumentReviewResultORM
from src.database.models.company_models import Company, CompanyVerificationDocument, CompanyCIPC, CompanyVerificationStatus, AllowableCompanyVerificationDocumentsEnum
from src.utils.route_helpers import get_service


class EmployerAgentsController(Controllers):
    """
    Controller for AI-powered employer tools, including job post enhancement, summarization,
    and company document verification.

    This controller enables employers to automate and improve job posts, evaluate the strength
    of their listings, and verify their company's authenticity using intelligent agent services.

    Dependencies:
        - EnhanceJobPostAgent
        - JobPostIntelligenceAgent
        - JobSummaryAgent
        - DocumentVerificationAgent
        - SQLAlchemy session (via self.get_session)
        - Logging, configuration, and database ORM classes

    Side Effects:
        - Writes to job and company tables in the database
        - Triggers AI agents that can modify or enhance data
        - Logs user and system actions
    """

    def __init__(self, factory):
        super().__init__(factory)

    def init_app(self, app):
        super().init_app(app)
        # App-specific initialization
        # self.cache.init_app(app)

    @error_handler
    async def enhance_job_post(self, user_id: str, input_data: dict) -> EnhanceJobPostOutput:
        """
        Enhance a job post using AI by improving content, formatting, and SEO elements.

        Args:
            user_id (str): ID of the employer requesting enhancement.
            input_data (dict): Raw job post input fields. Must match EnhanceJobPostInput schema.

        Returns:
            EnhanceJobPostOutput: Enhanced job post content including title, description, requirements,
            and auto-generated fields like expiration dates.

        Raises:
            ValueError: If required fields are missing or agent fails.
        """

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
        return result

    @error_handler
    async def analyze_job_post(self, user_id: str, job_id: str) -> JobPostInsights:
        """
        Analyze an existing job post and generate insights on clarity, inclusiveness, and SEO.

        Args:
            user_id (str): ID of the employer requesting the analysis.
            job_id (str): ID of the job post to analyze.

        Returns:
            JobPostInsights: AI-generated feedback on how to improve the job post.

        Raises:
            ValueError: If job is not found.
            PermissionError: If the user does not own the job post.
        """

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

            # noinspection PyTypeChecker
            return await agent.run(input_model=job)

    @error_handler
    async def create_job_summary(self, user_id: str, job_id: str) -> JobSummaryOutput:
        """
        Generate a concise and effective job summary for SEO and job board visibility.

        This method invokes the JobSummaryAgent and updates the database with the resulting
        summary and SEO-friendly description.

        Args:
            user_id (str): ID of the employer requesting the summary.
            job_id (str): ID of the job to summarize.

        Returns:
            JobSummaryOutput: Generated summary and SEO description fields.

        Raises:
            ValueError: If the job is not found.
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
            session.commit()
            # noinspection PyTypeChecker
            return job_summary

    @error_handler
    async def analyze_company_documents_for_authenticity(self, company_id: str):
        """
        Run an AI-based verification process on a company's official documents.

        This method verifies a company's identity and legal compliance by running
        document checks using AI agents, and updates the company's verification status.

        Args:
            company_id (str): ID of the company to verify.

        Returns:
            None

        Side Effects:
            - Updates verification timestamps and statuses in DB.
            - Runs AI document evaluation agents.
            - Logs all steps and errors.
        """

        self.logger.info(f"Starting company verification for {company_id}")
        with self.get_session() as session:
            company_orm = session.query(CompanyORM).filter_by(company_id=company_id).first()
            if not company_orm:
                self.logger.warning(f"Company {company_id} not found.")
                return

            # Mark that the process has started
            company_orm.time_verification_process_started = datetime.now(timezone.utc)
            company_orm.verification_status = CompanyVerificationStatus.PENDING.value
            session.add(company_orm)
            session.commit()

            await self.run_document_verification_agents(company_orm, session)

            # Re-fetch documents with updated AI status
            documents = session.query(CompanyVerificationDocumentORM).filter_by(company_id=company_id).all()
            doc_types = [doc.document_type for doc in documents]

            if AllowableCompanyVerificationDocumentsEnum.DIRECTOR_ID_CARD_FRONT.value not in doc_types:
                company_orm.verification_status = CompanyVerificationStatus.DOCUMENTS_REJECTED.value
            elif all(d.ai_review_status == "approved" for d in documents):
                company_orm.is_verified = True
                company_orm.verification_status = CompanyVerificationStatus.VERIFIED.value
            elif any(d.ai_review_status == "rejected" for d in documents):
                company_orm.is_verified = False
                if any(d.ai_review_status == "approved" for d in documents):
                    company_orm.verification_status = CompanyVerificationStatus.HUMAN_REVIEW.value
                else:
                    company_orm.verification_status = CompanyVerificationStatus.DOCUMENTS_REJECTED.value
            else:
                company_orm.is_verified = False
                company_orm.verification_status = CompanyVerificationStatus.HUMAN_REVIEW.value

            session.add(company_orm)
            session.commit()

    @error_handler
    async def run_document_verification_agents(self, company_orm: CompanyORM, session):
        """
        Run AI document agents on each company document to assess legitimacy and consistency.

        This method processes various uploaded documents, checks against company registration
        data (e.g., CIPC records), and persists AI findings.

        Args:
            company_orm (CompanyORM): SQLAlchemy ORM object for the company.
            session: SQLAlchemy session object for database transactions.

        Side Effects:
            - Stores agent output in the database.
            - Updates document statuses and adds notes.
            - Commits all changes per document.
        """

        self.logger.info(f"Running AI document verification for company {company_orm.company_id}")

        documents_list: list[CompanyVerificationDocumentORM] = session.query(CompanyVerificationDocumentORM).filter_by(company_id=company_orm.company_id).all()
        cipc_record = session.query(CompanyCIPCORM).filter_by(company_id=company_orm.company_id).first()

        document_verification_agent = DocumentVerificationAgent(user_id=company_orm.company_id)

        for doc in documents_list:
            agent_input = DocumentVerificationInput(
                document_type=doc.document_type,
                supplied_document_pdf= get_service('company_document_loader')(document_uri=doc.file_url),
                director_name=cipc_record.director_name,
                id_number=cipc_record.director_id,
                director_id_card_pdf=company_orm.company_id,
                cipc_company_data=CompanyCIPC(**cipc_record.to_dict()),
                company_data=Company(**company_orm.to_dict())
            )

            document_verification_output: DocumentVerificationOutPut = await document_verification_agent.run(input_model=agent_input)
            # AI Output Example (suspicious tax clearance certificate)
            session.add(AIBasedDocumentReviewResultORM(**document_verification_output.model_dump()))
            session.commit()

            status, notes = self.reduce_verification_output(document_verification_output)
            doc.status = status
            doc.notes = notes
            session.add(doc)
        session.commit()

    @error_handler
    def reduce_verification_output(self, ai_output: DocumentVerificationOutPut) -> Tuple[str, Optional[str]]:
        """
        Derive a verification status and summary notes from raw AI output.

        Args:
            ai_output (DocumentVerificationOutPut): AI results from analyzing a company document.

        Returns:
            Tuple[str, Optional[str]]:
                - status: One of ["approved", "rejected", "human_review"]
                - notes: Detailed human-readable analysis from the AI output

        Logic includes:
            - Validity checks
            - Director and ID matches
            - CIPC verification
            - Suspicion flags and reviewer comments
        """

        if ai_output.requires_human_review or ai_output.is_suspicious:
            status = "human_review"
        elif not ai_output.is_document_valid:
            status = "rejected"
        else:
            status = "approved"

        # Compile notes from relevant fields
        notes_parts = []

        # Core validity and reasoning
        notes_parts.append(f"Document Validity: {ai_output.is_document_valid}")
        if ai_output.reason:
            notes_parts.append(f"Invalidity Reason: {ai_output.reason}")

        # Match results
        if ai_output.match_director_name is not None:
            notes_parts.append(f"Director Name Match: {ai_output.match_director_name}")
        if ai_output.match_id_number is not None:
            notes_parts.append(f"ID Number Match: {ai_output.match_id_number}")
        if ai_output.match_cipc_data is not None:
            notes_parts.append(f"CIPC Data Match: {ai_output.match_cipc_data}")
        if ai_output.match_company_profile_data is not None:
            notes_parts.append(f"Company Profile Match: {ai_output.match_company_profile_data}")

        # CIPC verification details
        if ai_output.cipc_number_verified_online is not None:
            notes_parts.append(f"CIPC Online Verification: {ai_output.cipc_number_verified_online}")
        if ai_output.cipc_number_verification_notes:
            notes_parts.append(f"CIPC Verification Notes: {ai_output.cipc_number_verification_notes}")

        # Fraud indicators
        if ai_output.is_suspicious:
            notes_parts.append(f"Suspicious Document: True")
        if ai_output.suspicious_notes:
            notes_parts.append(f"Suspicious Indicators: {ai_output.suspicious_notes}")

        # Review metadata
        if ai_output.score is not None:
            notes_parts.append(f"Confidence Score: {ai_output.score:.2f}")
        if ai_output.reviewer_notes:
            notes_parts.append(f"Reviewer Summary: {ai_output.reviewer_notes}")

        # Human review flag (if not already covered by status)
        if ai_output.requires_human_review and status != "human_review":
            notes_parts.append("Flagged for Manual Review")

        # Combine all notes
        notes = "\n".join(notes_parts) if notes_parts else None

        return status, notes

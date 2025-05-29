import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from flask import Flask, render_template, url_for
from sqlalchemy.orm import joinedload

from src.controllers.controller import Controllers, error_handler
from src.controllers.jobs import JobsWorkflowController
from src.controllers.resumes import ResumeController
from src.database.models.company_models import Company
from src.database.models.employer_models import Employer
from src.database.models.jobs_model import Job, JobStatusEnum, TalentPoolReport, JobApplicationDashboard
from src.database.models.resume import JobSeekerCV, SavedCV
from src.database.models.users import User
from src.database.sql.company import CompanyORM
from src.database.sql.employer import EmployerORM
from src.database.sql.users import UserORM
from src.emailer import EmailModel
from src.logger import init_logger
from src.main import send_mail


class CompanyController(Controllers):
    """Handles employer profiles and company-related operations"""
    
    def __init__(self, jobs_controller=None, resume_controller=None):
        super().__init__()
        self.logger = init_logger("CompanyController")
        self.jobs_workflow_controller: JobsWorkflowController = jobs_controller  # Injected dependency
        self.resume_controller: ResumeController = resume_controller


    def init_app(self, app: Flask):
        super().init_app(app=app)


    async def get_all_companies(self) -> list[Company]:
        """
        :return:
        """
        with self.get_session() as session:
            company_orm_list = session.query(CompanyORM).all()
            return [Company(**company_orm.to_dict()) for company_orm in company_orm_list]


    @error_handler
    async def create_company(self, company_data: Company) -> Company:
        """

        :param company_data:
        :return:
        """
        with self.get_session() as session:
            _name = company_data.name.casefold()
            company_orm = session.query(CompanyORM).filter_by(name=_name).first()
            if company_orm:
                raise ValueError(f"Company with this name already exists {_name.title()}")

            session.add(CompanyORM(**company_data.model_dump()))

            return company_data

    @error_handler
    async def register_employer(self, employer_data: Employer) -> Employer:
        """Create new employer profile with company association
        Links employer to Auth0/Firebase UID and initial company metadata
        """
        with self.get_session() as session:
            if session.query(EmployerORM).filter_by(user_uid=employer_data.user_uid).first():
                raise ValueError("Employer profile exists for this user")
                
            employer_orm = EmployerORM(**employer_data.model_dump())
            session.add(employer_orm)

            return Employer(**employer_orm.to_dict())

    @error_handler
    async def get_company_by_id(self, company_id: str) -> Company:
        """
        Return a company complete with its job listings
        :param company_id: UUID of the company to retrieve
        :return: Company object with nested jobs
        """
        with self.get_session() as session:
            # Get company with eager-loaded jobs in single query
            company_orm = (
                session.query(CompanyORM)
                .options(joinedload(CompanyORM.jobs))
                .filter_by(id=company_id)
                .first()
            )

            if not company_orm:
                raise ValueError(f"Company with ID {company_id} not found")

            # Convert ORM to Pydantic model
            return Company(**company_orm.to_dict())


    @error_handler
    async def _get_employer(self, employer_id: str, session) -> EmployerORM| None:

        employer_orm = session.query(EmployerORM).filter_by(employer_id=employer_id).first()
        if isinstance(employer_orm, EmployerORM):
            return employer_orm
        raise ValueError("Employer does not exist")

    @error_handler
    async def get_employer_by_uid(self, user_id: str) -> Employer:
        """
        :param user_id:
        :return:
        """
        with self.get_session() as session:
            employer_orm = session.query(EmployerORM).filter_by(user_id==user_id).first()
            if not employer_orm:
                raise ValueError("The User is not already an Employer")
            return Employer(**employer_orm.to_dict())

    @error_handler
    async def get_employer_by_employer_id(self, employer_id: str) -> Employer:
        """
        :param employer_id:
        :return:
        """
        with self.get_session() as session:
            employer_orm = session.query(EmployerORM).filter_by(employer_id==employer_id).first()
            if not employer_orm:
                raise ValueError("The User is not already an Employer")
            return Employer(**employer_orm.to_dict())


    @error_handler
    async def get_company_jobs(self, company_id: str, status: Optional[JobStatusEnum] = None) -> List[Job]:
        """Retrieve company jobs with optional status filtering"""
        with self.get_session() as session:
            # Get company with jobs relationship
            company = (
                session.query(CompanyORM)
                .options(joinedload(CompanyORM.jobs))  # Eager load jobs
                .filter(CompanyORM.company_id == company_id)
                .first()
            )
            if not company:
                return []
            # Apply status filter if provided
            jobs = company.jobs
            if status:
                jobs = [job for job in jobs if job.status == status.value]
            return [Job(**job.to_dict()) for job in jobs]

    @error_handler
    async def get_application_analytics(self, company_id: str) -> JobApplicationDashboard:
        """Get hiring metrics using JobsController's analytics engine
        Combines company-specific filtering with core analytics logic
        """
        return await self.jobs_workflow_controller.get_company_analytics_dashboard(company_id=company_id)

    @error_handler
    async def generate_talent_pool_report(self, company_id: str) -> TalentPoolReport:
        """

        :param company_id:
        :return:
        """
        return await self.jobs_workflow_controller.generate_talent_pool_report(company_id=company_id)

    @error_handler
    async def update_employer_profile(self, employer_id: str, company_data: Company) -> Employer:
        """

        :param employer_id:
        :param company_data:
        :return:
        """
        with self.get_session() as session:
            employer_orm = session.query(EmployerORM).filter_by(employer_id=employer_id).first()
            if not employer_orm:
                return  None
            employer_orm.company_id = company_data.company_id
            session.commit()
            return Employer(**employer_orm.to_dict())

    @error_handler
    async def post_job(self, user_uid: str, job_data: Job) -> Job:
        """
            ensure jobs could be posted under this company -
            check verification status of employer profile
            check verification status of company_profile
        :param user_uid:
        :param job_data:
        :return:
        """
        with self.get_session() as session:

            employer_orm = session.query(EmployerORM).filter_by(user_uid=user_uid).first()
            if not employer_orm:
                raise ValueError("No Valid Employer with this User ID")

            _employer_profile = Employer(**employer_orm.to_dict())
            company_orm = session.query(CompanyORM).filter_by(company_id=_employer_profile.company_id).first()

            if not company_orm:
                raise ValueError("Unable to load your company details")

            company_profile = Company(**company_orm.to_dict())

            if not (_employer_profile.is_valid and _employer_profile.is_verified):
                raise ValueError('Your Employer Profile is not yet verified (or its incomplete)')

            if not (company_profile.is_valid and company_profile.is_verified):
                raise ValueError('Your Company Profile is not yet verified (or its incomplete)')
            # TODO - once subscriptions are added please check the status of the subscription here
            # creating job with jobs controller then return the results
            return await self.jobs_workflow_controller.create_job(job=job_data)

    @error_handler
    async def get_saved_candidates(self, user_uid: str) -> list[JobSeekerCV]:
        """
            using user_uid will retrieve a list of candidates
        :param user_uid:
        :return:
        """
        with self.get_session() as session:
            employer_profile_orm = session.query(EmployerORM).filter_by(user_uid=user_uid).first()

            if not employer_profile_orm:
                return []

            employer_details: Employer = Employer(**employer_profile_orm.to_dict())
            if not (employer_details.is_valid and employer_details.is_verified):
                return []

            return await self.resume_controller.employer_saved_cvs(employer_id=employer_details.employer_id)

    @error_handler
    async def save_candidate(self, user_uid: str, save_cv_model:SavedCV) -> SavedCV| None:
        """

        :param save_cv_model:
        :param user_uid:
        :return:
        """
        with self.get_session() as session:
            employer_orm = session.query(EmployerORM).filter_by(user_uid=user_uid).first()
            if not employer_orm:
                return None

            _employer_profile: Employer = Employer(**employer_orm.to_dict())
            if not (_employer_profile.is_valid and _employer_profile.is_verified):
                return None

            is_saved = await self.resume_controller.employer_save_cv(employer_id=_employer_profile.employer_id, save_cv_model=save_cv_model)
            return save_cv_model if is_saved else None

    @staticmethod
    async def _get_user_by_uid(session, uid: str) -> User:
        """
            :param uid:
            :return:
        """
        user_orm = session.query(UserORM).filter_by(uid=uid).first()
        return User(**user_orm.to_dict())

    @error_handler
    async def initiate_employer_profile_verification(self, employer_id: str ) -> None:
        """

        :param employer_id:
        :return:
        """
        with self.get_session() as session:
            employer_orm = session.query(EmployerORM).filter_by(employer_id=employer_id).first()
            employer = Employer(**employer_orm.to_dict())

            if not employer:
                raise ValueError("Employer not found")

            if not employer.contact_email:
                raise ValueError("Employer does not have a contact email")
            token = secrets.token_urlsafe(32)
            employer_orm.verification_token = token
            employer_orm.verification_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)


            verification_link = url_for('company.verify_employer_profile', token=token, employer_id=employer_id)


            subject = "Employer Profile Verification"
            user = await self._get_user_by_uid(session=session, uid=employer.user_uid)
            context = dict(current_user=user, verification_link=verification_link)
            email_body = render_template('email/employer_profile_verification.html', **context)
            _subject = f"{user.name.title()} Please Verify your Employer Profile | jobfinders.site"
            email = EmailModel(to_=str(employer.contact_email), subject_=_subject, html_=email_body)
            response = await send_mail.send_mail_resend(email=email)

    @error_handler
    async def mark_employer_as_verified(self, employer_id: str) -> bool:

        with self.get_session() as session:
            employer_orm = session.query(EmployerORM).filter_by(employer_id=employer_id).first()

            employer_orm.is_verified = True
            employer_orm.verification_token = None
            employer_orm.verification_token_expires_at = None
            return True


    async def initiate_verification_process(self, company_id: str, document_paths: list, user_id: str):
        """Handle verification workflow"""
        # Store documents in database
        verification_id = await self._store_verification_documents(
            company_id,
            document_paths,
            user_id
        )

        # Run initial AI screening
        ai_result = await self._analyze_documents_with_ai(document_paths)

        if ai_result['is_valid']:
            await self._mark_company_verified(company_id)
            return {'status': 'verified', 'verification_id': verification_id}

        if ai_result['needs_human_review']:
            await self._flag_for_human_review(company_id, verification_id)
            await self._notify_admins(company_id, verification_id)
            return {'status': 'pending_review', 'verification_id': verification_id}

        await self._reject_verification(company_id, ai_result['reason'])
        return {'status': 'rejected', 'reason': ai_result['reason']}


    async def get_verification_status(self, company_id: str):
        return await self._get_verification_status_from_db(company_id)

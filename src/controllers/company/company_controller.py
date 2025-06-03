import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from flask import Flask, render_template, url_for
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from src.database.sql.jobs_sql import JobsORM
from src.controllers.controller import Controllers, error_handler
from src.controllers.jobs import JobsWorkflowController
from src.controllers.resumes import ResumeController
from src.database.models.company_models import Company, CompanyUpdate
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
            return [Company(**company_orm.to_dict()) for company_orm in company_orm_list if company_orm]


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
    async def get_employer_created_company(self, uid: str) -> Optional[Company]:
        """
            get the company which the employer just created
        :param uid:
        :return:
        """
        with self.get_session() as session:
            employer_orm = session.query(EmployerORM).filter_by(user_uid=uid).first()
            if not employer_orm:
                self.logger.info(f"Unable to locate Employer ORM Model for UID : {uid}")

                return None

            company_id = employer_orm.company_id
            company_orm = session.query(CompanyORM).filter_by(company_id=company_id).first()
            if not company_orm:
                return None
            return Company(**company_orm.to_dict())


    @error_handler
    async def register_employer(self, employer_data: Employer) -> Optional[Employer]:
        """Create new employer profile with company association
        Links employer to Auth0/Firebase UID and initial company metadata
        """
        with self.get_session() as session:
            if session.query(EmployerORM).filter_by(user_uid=employer_data.user_uid).first():
                raise ValueError("Employer profile exists for this user")
                
            # Dump the Employer Model without the relationships
            employer_orm = EmployerORM(**employer_data.model_dump(exclude={'company', 'saved_candidates'}))
            if not employer_orm:
                return None

            self.logger.info(f"Creating Employer ORM : {employer_orm.to_dict()}")
            session.add(employer_orm)
            self.logger.info(f"Employer Added to Session but if error occurs the data will be rolled back")
            # Do Not Include Relationships here because the data is not yet saved to the database
            return employer_data

    @error_handler
    async def get_company_by_id(self, company_id: str) -> Optional[Company]:
        """
        Return a company complete with its job listings and applications
        :param company_id: UUID of the company to retrieve
        :return: Company object with nested jobs and applications
        """
        with self.get_session() as session:
            # Eager load all relationships to avoid N+1 queries
            company_orm: CompanyORM = (
                session.query(CompanyORM)
                .options(
                    joinedload(CompanyORM.jobs).options(
                        joinedload(JobsORM.applications)
                    ),
                    joinedload(CompanyORM.employers),
                    joinedload(CompanyORM.saved_candidates)
                )
                .filter(CompanyORM.company_id == company_id)  # Fixed filter condition
                .first()
            )

            if not company_orm:
                self.logger.info(f"Unable to obtain company data with ID: {company_id}")
                return None

            self.logger.info(f"Obtained company data for ID: {company_id}")

            # Convert ORM to Pydantic model
            return Company.model_validate(company_orm)

    @error_handler
    async def get_employees_by_company_id(self, company_id: str) -> list[Employer]:
        """

        :param company_id:
        :return:
        """
        with self.get_session() as session:
            employer_orm_list = session.query(EmployerORM).filter_by(company_id==company_id).all()
            return [Employer(**employer_orm.to_dict()) for employer_orm in employer_orm_list if employer_orm]

    @error_handler
    async def get_company_by_name(self, name: str) -> Company:
        """
        Return a company with the exact name (case-insensitive)
        :param name: Exact name of the company to retrieve
        :return: Company object with nested jobs
        :raises ValueError: If no company matches the exact name
        """
        with self.get_session() as session:
            # Case-insensitive exact match
            company_orm: CompanyORM = (
                session.query(CompanyORM)
                .options(joinedload(CompanyORM.jobs))
                .filter(func.lower(CompanyORM.name) == func.lower(name))
                .first()
            )

            if not company_orm:
                raise ValueError(f"No company found with name '{name}'")

            return Company(**company_orm.to_dict(include_relationships=True))

    @error_handler
    async def search_companies_by_name(self, name: str) -> list[Company]:
        """
        Search for companies containing the name substring
        :param name: Substring to search in company names
        :return: List of matching Company objects
        """
        with self.get_session() as session:
            companies_orm: list[CompanyORM] = (
                session.query(CompanyORM)
                .options(joinedload(CompanyORM.jobs))
                .filter(func.lower(CompanyORM.name).contains(func.lower(name)))
                .all()
            )

            if not companies_orm:
                raise ValueError(f"No companies found matching '{name}'")

            return [Company(**c.to_dict()) for c in companies_orm]

    @error_handler
    async def _get_employer(self, employer_id: str, session) -> EmployerORM| None:

        employer_orm = session.query(EmployerORM).filter_by(employer_id=employer_id).first()
        if isinstance(employer_orm, EmployerORM):
            return employer_orm
        raise ValueError("Employer does not exist")

    @error_handler
    async def get_employer_by_uid(self, user_id: str) -> Employer | None:
        """
        :param user_id:
        :return:
        """
        with self.get_session() as session:
            self.logger.info(f"Inside get_employer by uid : {user_id}")
            employer_orm = session.query(EmployerORM).filter_by(user_uid=user_id).first()
            if not employer_orm:
                self.logger.info(f"Employer Record Not found : ")
                return None

            self.logger.info(f"Found Employer Record : {employer_orm.to_dict(include_relationships=True)}")

            return Employer(**employer_orm.to_dict(include_relationships=True))


    @error_handler
    async def get_employer_by_employer_id(self, employer_id: str) -> Employer| None:
        """
        :param employer_id:
        :return:
        """
        with self.get_session() as session:
            employer_orm = session.query(EmployerORM).filter_by(employer_id=employer_id).first()
            if not employer_orm:
                return None
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
    async def get_all_company_employers(self, company_id: str) -> List[Employer]:
        """
        Retrieve all employers associated with a specific company
        :param company_id: UUID of the company
        :return: List of Employer objects
        """
        with self.get_session() as session:
            employers_orm = (
                session.query(EmployerORM)
                .filter_by(company_id=company_id)
                .all()
            )

            if not employers_orm:
                return []

            return [Employer(**employer.to_dict()) for employer in employers_orm]


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
    async def update_employer_profile(self, employer_profile: Employer) -> Employer:
        with self.get_session() as session:
            self.logger.info("Inside Update Employer Profile")

            # Get existing employer ORM
            employer_orm = session.query(EmployerORM).filter_by(
                employer_id=employer_profile.employer_id
            ).first()

            if not employer_orm:
                return None

            # Convert Pydantic model to dict, excluding relationships
            exclude_fields = {"company", "saved_candidates", "created_at", "updated_at"}
            update_data = employer_profile.model_dump(exclude=exclude_fields)

            # Update scalar fields
            for key, value in update_data.items():
                if hasattr(employer_orm, key):
                    if value:
                        setattr(employer_orm, key, value)

            # Handle timestamp update
            employer_orm.updated_at = func.now()

            # Handle company relationship separately if needed
            if employer_profile.company_id and employer_profile.company_id != employer_orm.company_id:
                # Verify new company exists
                new_company = session.query(CompanyORM).filter_by(
                    company_id=employer_profile.company_id
                ).first()

                if new_company:
                    employer_orm.company = new_company

            session.commit()
            session.refresh(employer_orm)

            # Return updated employer with relationships
            return Employer.model_validate(employer_orm)

    @error_handler
    async def update_company(self, company_id: str, update_data: CompanyUpdate) -> Company:
        with self.get_session() as session:
            # Get existing company
            company_orm = session.query(CompanyORM).filter_by(company_id=company_id).first()
            if not company_orm:
                raise ValueError("Company not found")

            # Convert Pydantic model to dict, excluding unset fields
            update_dict = update_data.model_dump(exclude_unset=True)

            # Update fields
            for key, value in update_dict.items():
                if hasattr(company_orm, key):
                    if value:
                        setattr(company_orm, key, value)

            # Update timestamp
            company_orm.updated_at = func.now()

            session.commit()
            session.refresh(company_orm)
            return Company.model_validate(company_orm)

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
            # async def post_job_employer(self, employer: Employer, job_data: Job) -> Job:
            return await self.jobs_workflow_controller.post_job_employer(employer=_employer_profile,  job=job_data)

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
            
            # Rendering verification email on its template
            email_body = render_template('email/employer_profile_verification.html', **context)
            _subject = f"{user.name.title()} Please Verify your Employer Profile | jobfinders.site"

            email = EmailModel(to_=str(employer.contact_email), subject_=_subject, html_=email_body)
            # Sending Email then obtaining a response
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


    async def get_industries(self):
        industries = [
            "Information Technology", "Finance and Banking", "Mining and Resources",
            "Agriculture", "Manufacturing", "Healthcare", "Education", "Tourism and Hospitality",
            "Retail", "Construction and Engineering", "Telecommunications", "Energy",
            "Transportation and Logistics", "Media and Advertising", "Government",
            "Non-profit", "Consulting", "Automotive", "Real Estate", "Food and Beverage",
            "E-commerce", "Biotechnology", "Pharmaceuticals", "Insurance", "Legal"
        ]
        return industries


    async def get_countries(self):
        countries = [
            "South Africa", "Botswana", "Lesotho", "Eswatini", "Namibia", "Zimbabwe",
            "Zambia", "Mozambique", "Malawi", "Angola", "Kenya", "Nigeria", "Ghana",
            "China", "Russia", "United States", "United Kingdom", "Germany", "Australia",
            "Canada", "United Arab Emirates", "Singapore", "India", "Brazil"
        ]
        return countries

    async def get_tech_options(self):
        tech_options = [
            "Python", "JavaScript", "Java", "C#", "PHP", "C++", "Ruby", "Swift", "Go",
            "TypeScript", "Kotlin", "Rust", "SQL", "HTML/CSS", "React", "Angular", "Vue.js",
            "Node.js", "Django", "Flask", "Spring", "Laravel", "Ruby on Rails", ".NET",
            "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "Terraform", "Ansible"
        ]
        return tech_options
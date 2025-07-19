# Standard Library
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List

# Flask Core
from flask import Flask, render_template, url_for

# SQLAlchemy ORM
from sqlalchemy import func
from sqlalchemy.orm import joinedload

# App Core
from src.logger import init_logger
from src.emailer import EmailModel
from src.utils.route_helpers import get_service, get_controller
from src.controllers.controller import Controllers, error_handler

# Domain Models (all aggregated exports)
from src.database.models import (
    Company,
    CompanyUpdate,
    CompanyVerificationStatus,
    CompanyCIPC,
    CompanyVerificationDocument,
    Employer,
    Job,
    JobStatusEnum,
    TalentPoolReport,
    JobApplicationDashboard,
    JobSeekerCV,
    SavedCV,
    User,
)

# SQL Models (ORMs)
from src.database import (
    CompanyORM,
    CompanyCIPCORM,
    CompanyVerificationDocumentORM,
    DirectorDetailsORM,
    EmployerORM,
    UserORM,
)

# from src.cache.cache_redis import cached

LONG_CACHE = 60  # i HOUR cACHE
SHORT_CACHE = 15 # 15 MINUTES CACHE
MEDIUM_CACHE = 30 # 30 MINUTES CACHE

class CompanyController(Controllers):
    __doc__ = """    
    CompanyController handles all business logic related to company and employer management within the platform.
    
        Responsibilities:
        - Company CRUD: Create, retrieve, update, and search for companies, including fetching by ID or name, and searching by substring.
        - Employer CRUD: Register, retrieve, and update employer profiles, including linking employers to companies and managing their verification status.
        - Job Management: Retrieve jobs for a company, filter by status, and post new jobs (with verification checks).
        - Candidate Management: Retrieve and save candidates (CVs) for employers.
        - Verification Workflow: Initiate and manage company and employer verification processes, including document storage, AI/ML analysis, human review, and notification flows.
        - Analytics: Fetch application analytics and generate talent pool reports for companies.
        - Industry, Country, and Tech Options: Provide static lists for industries, countries, and technology stacks.
        - CIPC Records: Manage CIPC (Companies and Intellectual Property Commission) records for companies.
        - Email Notifications: Send verification and notification emails to employers and admins.
    
        Requirements/Dependencies:
        - Database session management (SQLAlchemy ORM models for Company, Employer, Job, User, etc.).
        - Pydantic models for data validation and serialization.
        - Flask for request context, URL generation, and template rendering.
        - Email service for sending notifications.
        - Logger for activity and error tracking.
        - AI/ML service for document analysis (integration point for future enhancements).
        - Utility helpers for controller and service access.
    
        Error Handling:
        - Uses a decorator to handle and log errors for all async controller methods.
    
        Note:
        - Some methods contain placeholders for future implementation (e.g., AI/ML document analysis, admin notifications).
        - Relationships between models (e.g., company-employer, company-jobs) are handled via ORM and Pydantic serialization.
    
    """
    
    def __init__(self,factory):
        super().__init__(factory)
        self.logger = init_logger("CompanyController")
        self.jobs_workflow_controller = get_controller('jobs_workflow')
        self.resume_controller = get_controller('resume')
        self.employer_ai_agents = get_controller('employer_agents')



    def init_app(self, app: Flask):
        super().init_app(app=app)

    @error_handler
    async def get_all_companies(self) -> list[Company]:
        """
        :return:
        """
        with self.get_session() as session:
            company_orm_list = session.query(CompanyORM).all()
            return [Company(**company_orm.to_dict()) for company_orm in company_orm_list if company_orm] if company_orm_list else []


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

            # Updating IP Address
            company_data.ip_address = get_service('ip_address')()
            session.add(CompanyORM(**company_data.model_dump()))

            return company_data

    @error_handler
    async def get_employer_created_company(self, uid: str) -> Optional[Company]:
        """
            get the company which the employer just created
        :param uid:
        :return:
        """
        if not(isinstance(uid, str) and uid.strip()):
            return None

        with self.get_session() as session:
            employer_orm = session.query(EmployerORM).filter_by(user_uid=uid).first()
            if not employer_orm:
                self.logger.info(f"Unable to locate Employer ORM Model for UID : {uid}")
                return None

            company_id = employer_orm.company_id
            company_orm = session.query(CompanyORM).filter_by(company_id=company_id).first()

            return Company(**company_orm.to_dict()) if company_orm else None


    @error_handler
    async def register_employer(self, employer_data: Employer) -> Optional[Employer]:
        """Create new employer profile with company association
        Links employer to Auth0/Firebase UID and initial company metadata
        """
        if not isinstance(employer_data, Employer):
            return None

        with self.get_session() as session:
            if session.query(EmployerORM).filter_by(user_uid=employer_data.user_uid).first():
                raise ValueError("Employer profile exists for this user")
                
            # Updating IP Address
            _ip_address = get_service('ip_address')()
            employer_data.ip_address = _ip_address
            self.logger.info(f"Retrieved IP Address : {_ip_address}")
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
            if not (isinstance(company_id, str) and company_id.strip()):
                return None

            company_orm = session.query(CompanyORM).get(company_id)
            if not company_orm:
                self.logger.info(f"Unable to obtain company data with ID: {company_id}")
                return None

            self.logger.info(f"Obtained company data for ID: {company_id}")

            # Convert ORM to Pydantic model
            return Company(**company_orm.to_dict(include_relationships=True))

    @error_handler
    async def get_employees_by_company_id(self, company_id: str) -> list[Employer]:
        """

        :param company_id:
        :return:
        """
        if not (isinstance(company_id, str) and company_id.strip()):
            return []

        with self.get_session() as session:
            employer_orm_list = session.query(EmployerORM).filter_by(company_id==company_id).all()
            return [Employer(**employer_orm.to_dict()) for employer_orm in employer_orm_list
                    if employer_orm] if employer_orm_list else []

    @error_handler
    async def get_company_by_name(self, name: str) -> Company | None:
        """
        Return a company with the exact name (case-insensitive)
        :param name: Exact name of the company to retrieve
        :return: Company object with nested jobs
        :raises ValueError: If no company matches the exact name
        """
        if not (isinstance(name, str) and name.strip()):
            return None
        #TODO- Ensure Company is returning all the needed data
        with self.get_session() as session:
            # Case-insensitive exact match 
            company_orm: CompanyORM = (
                session.query(CompanyORM)
                .options(joinedload(CompanyORM.jobs))
                .filter(func.lower(CompanyORM.name) == func.lower(name))
                .first()
            )
            return Company(**company_orm.to_dict(include_relationships=True)) if company_orm else None

    @error_handler
    async def search_companies_by_name(self, name: str) -> list[Company]:
        """
        Search for companies containing the name substring
        :param name: Substring to search in company names
        :return: List of matching Company objects
        """
        if not (isinstance(name, str) and name.strip()):
            return []

        with self.get_session() as session:
            companies_orm: list[CompanyORM] = (
                session.query(CompanyORM)
                .options(joinedload(CompanyORM.jobs))
                .filter(func.lower(CompanyORM.name).contains(func.lower(name)))
                .all()
            )
            return [Company(**company_orm.to_dict()) for company_orm in companies_orm
                    if company_orm] if companies_orm else []

    @error_handler
    async def _get_employer(self, employer_id: str, session) -> EmployerORM| None:
        """will return the EmployerORM Model"""
        if not (isinstance(employer_id, str) and employer_id.strip()):
            return None
        employer_orm = session.query(EmployerORM).filter_by(employer_id=employer_id).first()
        return employer_orm if isinstance(employer_orm, EmployerORM) else None

    @error_handler
    async def get_employer_by_uid(self, user_id: str) -> Employer | None:
        """
        :param user_id:
        :return:
        """
        if not (isinstance(user_id, str) and user_id.strip()):
            return None

        with self.get_session() as session:
            self.logger.info(f"Inside get_employer by uid : {user_id}")
            employer_orm = session.query(EmployerORM).filter_by(user_uid=user_id).first()
            if not employer_orm:
                self.logger.info(f"Employer Record Not found : ")
                return None
            self.logger.info(f"Found Employer Record : ")
            return Employer(**employer_orm.to_dict(include_relationships=True))


    @error_handler
    async def get_employer_by_employer_id(self, employer_id: str) -> Employer| None:
        """
        :param employer_id:
        :return:
        """
        if not (isinstance(employer_id, str) and employer_id.strip()):
            return None
        with self.get_session() as session:
            employer_orm = session.query(EmployerORM).filter_by(employer_id=employer_id).first()
            return Employer(**employer_orm.to_dict()) if employer_orm else None


    @error_handler
    async def get_company_jobs(self, company_id: str, status: Optional[JobStatusEnum] = None) -> List[Job]:
        """Retrieve company jobs with optional status filtering"""
        if not (isinstance(company_id, str) and company_id.strip()):
            return []

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
            self.logger.info(f"Company DATA : {company.name}")
            self.logger.info(f"COMPANY JOBS : {jobs}")
            if status:
                jobs = [job for job in jobs if job.status.casefold() == status.value.casefold()]
            return [Job(**job.to_dict()) for job in jobs] if jobs else []


    @error_handler
    async def get_all_company_employers(self, company_id: str) -> List[Employer]:
        """
        Retrieve all employers associated with a specific company
        :param company_id: UUID of the company
        :return: List of Employer objects
        """
        if not (isinstance(company_id, str) and company_id.strip()):
            return []
        with self.get_session() as session:
            employers_orm = (
                session.query(EmployerORM)
                .filter_by(company_id=company_id)
                .all()
            )
            return [Employer(**employer.to_dict()) for employer in employers_orm] if employers_orm else []


    @error_handler
    async def get_application_analytics(self, company_id: str) -> JobApplicationDashboard | None:
        """Get hiring metrics using JobsController's analytics engine
        Combines company-specific filtering with core analytics logic
        """
        if not (isinstance(company_id, str) and company_id.strip()):
            return None
        return await self.jobs_workflow_controller.get_company_analytics_dashboard(company_id=company_id)

    @error_handler
    async def generate_talent_pool_report(self, company_id: str) -> TalentPoolReport | None:
        """
        :param company_id:
        :return:
        """
        if not (isinstance(company_id, str) and company_id.strip()):
            return None
        return await self.jobs_workflow_controller.generate_talent_pool_report(company_id=company_id)

    @error_handler
    async def update_employer_profile(self, employer_profile: Employer) -> Employer | None:
        with self.get_session() as session:
            self.logger.info("Inside Update Employer Profile")
            # Get existing employer ORM
            employer_orm = session.query(EmployerORM).filter_by(employer_id=employer_profile.employer_id).first()
            if not employer_orm:
                return None

            # Updating IP Address
            _ip_address = get_service('ip_address')()
            employer_profile.ip_address = _ip_address
            self.logger.info(f"Retrieved IP Address : {_ip_address}")
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
                new_company = session.query(CompanyORM).filter_by(company_id=employer_profile.company_id).first()
                if new_company:
                    employer_orm.company = new_company

            session.commit()
            session.refresh(employer_orm)
            # Return updated employer with relationships
            return Employer(**employer_orm.to_dict())

    @error_handler
    async def update_company(self, company_id: str, update_data: CompanyUpdate) -> Company | None:
        """Update Company"""
        if not (isinstance(company_id, str) and company_id.strip()):
            return None
        if not isinstance(update_data, CompanyUpdate):
            return None
        with self.get_session() as session:
            # Get existing company
            company_orm = session.query(CompanyORM).filter_by(company_id=company_id).first()
            if not company_orm:
                return None

            if not update_data.ip_address:
                # Updating IP Address
                _ip_address = get_service('ip_address')()
                self.logger.info(f"Retrieved IP Address : {_ip_address}")
                update_data.ip_address = _ip_address

            # Convert Pydantic model to dict, excluding unset fields
            update_dict = update_data.model_dump(exclude_unset=True)

            # Update fields
            for key, value in update_dict.items():
                if hasattr(company_orm, key):
                    if value:
                        setattr(company_orm, key, value)

            # Update timestamp
            company_orm.updated_at = datetime.now(timezone.utc)

            session.commit()
            session.refresh(company_orm)
            return Company(**company_orm.to_dict())

    @error_handler
    async def post_job(self, user_uid: str, job_data: Job) -> Optional[Job]:
        """
            ensure jobs could be posted under this company -
            check verification status of employer profile
            check verification status of company_profile
        :param user_uid:
        :param job_data:
        :return:
        """
        if not (isinstance(user_uid, str) and user_uid.strip()):
            return None
        if not isinstance(job_data, Job):
            return None

        with self.get_session() as session:
            employer_orm = session.query(EmployerORM).filter_by(user_uid=user_uid).first()
            if not employer_orm:
                return None

            _employer_profile = Employer(**employer_orm.to_dict())
            company_orm = session.query(CompanyORM).filter_by(company_id=_employer_profile.company_id).first()

            if not company_orm:
                return None

            company_profile = Company(**company_orm.to_dict())
            if not (_employer_profile.is_valid and _employer_profile.is_verified):
                return None

            if not (company_profile.is_valid and company_profile.is_verified):
                return None

            # TODO - once subscriptions are added please check the status of the subscription here
            # creating job with jobs controller then return the results
            # async def post_job_employer(self, employer: Employer, job_data: Job) -> Job:
            return await self.jobs_workflow_controller.add_job_posting_workflow(employer=_employer_profile,  job=job_data)

    @error_handler
    async def get_saved_candidates(self, user_uid: str) -> list[JobSeekerCV]:
        """
            using user_uid will retrieve a list of candidates
        :param user_uid:
        :return:
        """
        if not (isinstance(user_uid, str) and user_uid.strip()):
            return []

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
        if not (isinstance(user_uid, str) and user_uid.strip()):
            return None
        if not isinstance(save_cv_model, SavedCV):
            return None

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
    async def _get_user_by_uid(session, uid: str) -> User | None:
        """
            :param uid:
            :return:
        """
        if not (isinstance(uid, str) and uid.strip()):
            return None        

        user_orm = session.query(UserORM).filter_by(uid=uid).first()
        return User(**user_orm.to_dict()) if user_orm else None

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

            response = await get_service('send_mail')().send_mail_resend(email=email)

    @error_handler
    async def mark_employer_as_verified(self, employer_id: str) -> bool:

        with self.get_session() as session:
            employer_orm = session.query(EmployerORM).filter_by(employer_id=employer_id).first()

            employer_orm.is_verified = True
            employer_orm.verification_token = None
            employer_orm.verification_token_expires_at = None
            return True

    @error_handler
    async def initiate_company_verification_process(self, company_id: str, document_paths: list, user_id: str):
        """Handle verification workflow"""
        # Store documents in database
        verification_id = await self._store_verification_documents(
            company_id,
            document_paths,
            user_id
        )

        # Run initial AI screening
        ai_result = await self._analyze_documents_with_ai(company_id=company_id)

        if ai_result['is_valid']:
            await self._mark_company_verified(company_id)
            return {'status': 'verified', 'verification_id': verification_id}

        if ai_result['needs_human_review']:
            await self._flag_for_human_review(company_id, verification_id)
            await self._notify_admins(company_id, verification_id)
            return {'status': 'pending_review', 'verification_id': verification_id}

        if await self._reject_verification(company_id, ai_result['reason']):
            return {'status': 'rejected', 'reason': ai_result['reason']}
        return {'status': 'not-rejected', 'reason': ai_result['reason']}
    
    
    @error_handler
    async def _get_company_verification_status_from_db(self, company_id: str):
        """Fetch verification status and related info for a company from the database."""
        with self.get_session() as session:
            company_orm = session.query(CompanyORM).filter_by(company_id=company_id).first()
            if not company_orm:
                return {'company_id': company_id,'verification_status': 'not_found',
                    'is_verified': False,'time_verification_process_started': None}
            
            return {
                'company_id': company_orm.company_id,
                'verification_status': company_orm.verification_status,
                'is_verified': company_orm.is_verified,
                'time_verification_process_started': company_orm.time_verification_process_started.isoformat() if company_orm.time_verification_process_started else None
            }

    @error_handler
    async def get_company_verification_status(self, company_id: str):
        """Get the verification status of a company from the database 
        This function will return the verification status of a company from the database
        :param company_id:
        :return:
        """
        return await self._get_company_verification_status_from_db(company_id=company_id)


    @staticmethod
    async def get_industries():
        industries = [
            "Information Technology", "Finance and Banking", "Mining and Resources",
            "Agriculture", "Manufacturing", "Healthcare", "Education", "Tourism and Hospitality",
            "Retail", "Construction and Engineering", "Telecommunications", "Energy",
            "Transportation and Logistics", "Media and Advertising", "Government",
            "Non-profit", "Consulting", "Automotive", "Real Estate", "Food and Beverage",
            "E-commerce", "Biotechnology", "Pharmaceuticals", "Insurance", "Legal"
        ]
        return industries


    @staticmethod
    async def get_countries():
        countries = [
            "South Africa", "Botswana", "Lesotho", "Eswatini", "Namibia", "Zimbabwe",
            "Zambia", "Mozambique", "Malawi", "Angola", "Kenya", "Nigeria", "Ghana",
            "China", "Russia", "United States", "United Kingdom", "Germany", "Australia",
            "Canada", "United Arab Emirates", "Singapore", "India", "Brazil"
        ]
        return countries

    @staticmethod
    async def get_tech_options():
        tech_options = [
            "Python", "JavaScript", "Java", "C#", "PHP", "C++", "Ruby", "Swift", "Go",
            "TypeScript", "Kotlin", "Rust", "SQL", "HTML/CSS", "React", "Angular", "Vue.js",
            "Node.js", "Django", "Flask", "Spring", "Laravel", "Ruby on Rails", ".NET",
            "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "Terraform", "Ansible"
        ]
        return tech_options

    async def _store_verification_documents(self, company_id: str, document_paths: list, user_id: str) -> str:
        """
        Store verification documents in the database and return a verification ID.
        """
        # Placeholder: Implement actual DB storage logic
        self.logger.info(f"Storing verification documents for company {company_id}: {document_paths}")
        # Return a mock verification ID
        return f"Verifying documents for -{company_id}-{datetime.now().timestamp()}"

    async def get_verification_documents(self, company_id: str) -> list[CompanyVerificationDocument]:
        """
        Retrieve verification documents for a company.
        :param company_id: UUID of the company
        :return: List of CompanyVerificationDocument objects
        """
        if not (isinstance(company_id, str) and company_id.strip()):
            return []

        with self.get_session() as session:
            documents_orm = session.query(CompanyVerificationDocumentORM).filter_by(company_id=company_id).all()
            return [CompanyVerificationDocument(**doc.to_dict()) for doc in documents_orm] if documents_orm else []


    @error_handler
    async def _analyze_documents_with_ai(self, company_id: str ) -> dict:
        """
        Analyze documents using AI/ML to determine validity.
        Returns a dict with keys: is_valid (bool), needs_human_review (bool), reason (str, optional)
        """
        # TODO: Refactor this to work with Actual AI Service at the Moment the AI Service is implemented but not
        # Compatible with the Controller Method
        # self.logger.info(f"Analyzing documents with AI: {document_paths}")
        # Placeholder: Always return needs_human_review for now
        

        return {"is_valid": False, "needs_human_review": True, "reason": "AI review required"}


    @error_handler
    async def auto_verify_company_documents(self):
        """
            THIS IS A CRON ENTRY POINT FOR VERIFYING COMPANY DOCUMENTS
        This task may run in celery or task scheduler.
            fetch documents that have not been reviewed or without recommendations -
            check if company profiles have been properlu completed and verified.
            send the documents to a company agent document verifier.
        :return:
        """
        # This calls an AI Agent that will read all company documents of companies that have not been verified yet
        # if a company documents meet requirements and are not suspicious they will automatically be verified if otherwise
        # they will be marked for review.
        self.logger.info("Executing auto verify company docs from ap scheduler")
        _ = await self.employer_ai_agents.analyze_company_documents_for_authenticity()
        self.logger.info(f"Finished Company Documents Verification")
        # TODO - need to complete the process of uploading company documents for verifications.
        

    @error_handler
    async def _mark_company_verified(self, company_id: str) -> None:
        """
        Mark the company as verified in the database.
        """
        if not (isinstance(company_id, str) and company_id.strip()):
            return None

        with self.get_session() as session:
            company_orm = session.query(CompanyORM).filter_by(company_id=company_id).first()
            if company_orm:
                company_orm.is_verified = True
                company_orm.verification_status = CompanyVerificationStatus.VERIFIED.value
                session.commit()
                self.logger.info(f"Company {company_id} marked as verified.")
            return None
    
    @error_handler
    async def _flag_for_human_review(self, company_id: str, verification_id: str) -> bool:
        """
        Flag the verification for human review in the database.
        """

        if not (isinstance(company_id, str) and company_id.strip()):
            return False

        if not (isinstance(verification_id, str) and verification_id.strip()):
            return False

        self.logger.info(f"Flagging company {company_id} verification {verification_id} for human review.")
        # Placeholder: Implement actual DB flag logic
        with self.get_session() as session:
            company_orm = session.query(CompanyORM).filter_by(company_id=company_id).first()
            if company_orm:
                company_orm.is_verified = False
                company_orm.time_verification_process_started = datetime.now(timezone.utc)
                company_orm.verification_status = CompanyVerificationStatus.HUMAN_REVIEW.value
                session.commit()
                self.logger.info(f"Company {company_id} flagged for human review.")
                return True
            return False

    @error_handler
    async def _notify_admins(self, company_id: str, verification_id: str) -> bool:
        """
        Notify admins that a verification needs human review.
        """
        if not (isinstance(company_id, str) and company_id.strip()):
            return False

        if not (isinstance(verification_id, str) and verification_id.strip()):
            return False

        self.logger.info(f"Notifying admins for company {company_id} verification {verification_id}.")
        # Placeholder: Implement actual notification logic
        with self.get_session() as session:
            company_orm: CompanyORM = session.query(CompanyORM).filter_by(company_id=company_id).first()
            company_profile = Company(**company_orm.to_dict(include_relationships=True))
            for employee in company_profile.employers:
                if employee.is_admin and employee.is_verified:
                    # TODO - create a template to send emails here
                    email = employee.email
                    subject = f"Company {company_profile.name.title()} verification needs human review"
                    message = f"Company {company_profile.name.title()} verification needs human review. You will be notified once the verification is complete. You can also check the verification status on the platform.   "
                    email = EmailModel(to_=str(email), subject_=subject, html_=message)
                    await get_service('send_mail')().send_mail_resend(email=email)
                    return True
            return False

    @error_handler
    async def _reject_verification(self, company_id: str, reason: str) -> bool:
        """
            Mark the verification as rejected in the database and log the reason.
            Reasons for Rejections will be logged into the Documents Models.
        """
        if not (isinstance(company_id, str) and company_id.strip()):
            return False

        if not (isinstance(reason, str) and reason.strip()):
            return False

        with self.get_session() as session:
            company_orm: CompanyORM = session.query(CompanyORM).filter_by(company_id=company_id).first()
            if company_orm:
                company_orm.is_verified = False
                company_orm.verification_status = CompanyVerificationStatus.NOT_VERIFIED.value
                session.commit()
                self.logger.info(f"Company {company_id} verification rejected: {reason}")
                return True
            return False

    @error_handler
    async def get_cipc_record_by_company_id(self, company_id: str) -> CompanyCIPC | None:
        """
        Fetch the CIPC company record by company ID, including associated director details.
        """
        if not (isinstance(company_id, str) and company_id.strip()):
            return None

        with self.get_session() as session:
            cipc_orm = (
                session.query(CompanyCIPCORM)
                .options(joinedload(CompanyCIPCORM.director_details))  # <-- eager load directors
                .filter_by(company_id=company_id)
                .first()
            )
            return CompanyCIPC(**cipc_orm.to_dict()) if isinstance(cipc_orm, CompanyCIPCORM) else None

    @error_handler
    async def update_cipc_record(self, company_id: str, cipc_record: CompanyCIPC) -> CompanyCIPC | None:
        """
        Update the CIPC record and its related directors for a given company.
        """
        if not (isinstance(company_id, str) and company_id.strip()):
            return None
        if not isinstance(cipc_record, CompanyCIPC):
            return None

        with self.get_session() as session:
            cipc_orm = session.query(CompanyCIPCORM).filter_by(company_id=company_id).first()
            if not cipc_orm:
                raise ValueError(f"No CIPC record found for company_id: {company_id}")

            # Update core fields
            update_data = cipc_record.model_dump(exclude_unset=True, exclude={"director_details"})
            for field, value in update_data.items():
                if hasattr(cipc_orm, field):
                    setattr(cipc_orm, field, value)

            # --- Replace director details if provided ---
            if cipc_record.director_details is not None:
                # Clear existing directors
                session.query(DirectorDetailsORM).filter_by(cipc_id=cipc_orm.cipc_id).delete()

                # Re-add new director entries
                for director in cipc_record.director_details:
                    if director:
                        session.add(DirectorDetailsORM(
                            cipc_id=cipc_orm.cipc_id,
                            director_id=director.director_id,
                            full_names=director.full_names,
                            id_number=director.id_number
                        ))
            session.commit()
            session.refresh(cipc_orm)
            return CompanyCIPC(**cipc_orm.to_dict())

    @error_handler
    async def create_cipc_record(self, cipc_data: CompanyCIPC) -> CompanyCIPC | None:
        if not isinstance(cipc_data, CompanyCIPC):
            return None

        with self.get_session() as session:
            # Create the company ORM object
            cipc_orm = CompanyCIPCORM(
                cipc_id=cipc_data.cipc_id,
                company_id=cipc_data.company_id,
                company_name=cipc_data.company_name,
                registration_number=cipc_data.registration_number,
                registration_date=cipc_data.registration_date,
                registered_address=cipc_data.registered_address,
                company_type=cipc_data.company_type,
                tax_pin=cipc_data.tax_pin,
                bee_status=cipc_data.bee_status,
                status=cipc_data.status,
                verified_at=cipc_data.verified_at
            )

            # Handle nested director details if provided
            if cipc_data.director_details:
                for director in cipc_data.director_details:
                    if director:  # skip None values in list
                        cipc_orm.director_details.append(DirectorDetailsORM(
                            cipc_id=cipc_data.cipc_id,
                            director_id=director.director_id,
                            full_names=director.full_names,
                            id_number=director.id_number
                        ))
            session.add(cipc_orm)
            return cipc_data

    @error_handler
    async def create_verification_document(self, ver_document: CompanyVerificationDocument) -> CompanyVerificationDocument:
        """
        :param ver_document:
        :return:
        """
        with self.get_session() as session:
            session.add(CompanyVerificationDocumentORM(**ver_document.model_dump(exclude={'ai_review'})))
            return ver_document

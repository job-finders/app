from typing import Optional, List, Dict

from flask import Flask
from sqlalchemy.orm import Session, joinedload

from src.database.models.employer_models import Employer
from src.database.models.jobs_model import Job, Company, JobStatusEnum, TalentPoolReport, JobApplicationDashboard
from src.database.sql.employer import EmployerORM
from src.logger import init_logger
from src.controllers.controller import Controllers, error_handler
from src.database.sql.jobs_sql import JobsORM, CompanyORM  # Added based on model convention

class CompanyController(Controllers):
    """Handles employer profiles and company-related operations"""
    
    def __init__(self, jobs_controller=None):
        super().__init__()
        self.logger = init_logger("CompanyController")
        self.jobs_controller = jobs_controller  # Injected dependency

    def init_app(self, app: Flask):
        super().init_app(app=app)
        if not self.jobs_controller:
            from src.main import jobs_controller
            self.jobs_controller = jobs_controller

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
        with session:
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
        return await self.jobs_controller.get_company_analytics_dashboard(company_id=company_id)

    async def generate_talent_pool_report(self, company_id: str) -> TalentPoolReport:
        """

        :param company_id:
        :return:
        """
        return await self.jobs_controller.generate_talent_pool_report(company_id=company_id)


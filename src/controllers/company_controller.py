from typing import Optional, List, Dict

from flask import Flask
from sqlalchemy.orm import Session, joinedload

from database.models.employer_models import Employer
from database.models.jobs_model import Job, Company, JobStatusEnum, TalentPoolReport, JobApplicationDashboard
from database.sql.employer import EmployerORM
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
    async def register_employer(self, employer_data: Employer) -> Employer:
        """Create new employer profile with company association
        Links employer to Auth0/Firebase UID and initial company metadata
        """
        with self.get_session() as session:
            if session.query(EmployerORM).filter_by(user_uid=employer_data.user_uid).first():
                raise ValueError("Employer profile exists for this user")
                
            employer = EmployerORM(**employer_data.model_dump())
            session.add(employer)

            return Employer.from_orm(employer)


    @error_handler
    async def _get_employer(self, employer_id: str, session) -> EmployerORM| None:
        with session:
            employer_orm = session.query(EmployerORM).filter_by(employer_id=employer_id).first()
            if isinstance(employer_orm, EmployerORM):
                return employer_orm
            raise ValueError("Employer does not exist")

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


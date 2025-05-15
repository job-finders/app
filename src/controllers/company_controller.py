from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from src.database.models.employer import Employer, EmployerORM
from src.database.models.jobs import Job, JobStatus
from src.database.models.resume import SavedCandidate
from src.controllers.controller import Controllers, error_handler
from src.database.sql.jobs_sql import JobsORM  # Added based on model convention

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
    async def register_employer(self, user_uid: str, company_data: Dict) -> Employer:
        """Create new employer profile with company association
        Links employer to Auth0/Firebase UID and initial company metadata
        """
        with self.get_session() as session:
            if session.query(EmployerORM).filter_by(user_uid=user_uid).first():
                raise ValueError("Employer profile exists for this user")
                
            employer = EmployerORM(user_uid=user_uid, **company_data)
            session.add(employer)

            return Employer.from_orm(employer)

    @error_handler
    async def post_job(self, user_uid: str, job_data: Dict) -> Job:
        """Create job posting using JobsController's core method
        Adds company_id validation before delegation
        """
        with self.get_session() as session:
            employer = self._get_employer(session, user_uid)
            
            if not employer.is_verified:
                raise PermissionError("Unverified companies cannot post jobs")
                
            # Use JobsController's core creation method
            return await self.jobs_controller.create_job(
                job_data | {"company_id": employer.company_id, "posted_by": user_uid}
            )

    @error_handler
    async def get_company_jobs(self, user_uid: str, status: Optional[JobStatus] = None) -> List[Job]:
        """Retrieve company jobs using JobsORM convention
        Leverages existing JobsController filtering logic
        """
        with self.get_session() as session:
            employer = self._get_employer(session, user_uid)
            return await self.jobs_controller.get_jobs_by_company(
                employer.company_id, 
                status=status
            )

    @error_handler
    async def get_application_analytics(self, user_uid: str) -> Dict:
        """Get hiring metrics using JobsController's analytics engine
        Combines company-specific filtering with core analytics logic
        """
        with self.get_session() as session:
            employer = self._get_employer(session, user_uid)
            return await self.jobs_controller.get_company_analytics(
                employer.company_id
            )

    @staticmethod
    def _calculate_avg_hire_time(jobs: List[Job]) -> Optional[float]:
        """Delegate to JobsController's metric calculation
        Maintains single source of truth for business logic
        """
        return self.jobs_controller.calculate_average_hire_time(jobs)

    # Other methods remain unchanged but verified against ORM conventions
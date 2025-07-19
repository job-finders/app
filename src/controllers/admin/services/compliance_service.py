import inspect
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import func, case

from src.controllers.admin.interfaces import AdminServiceInterface
from src.database import CompanyORM, JobsORM, JobApplicationORM, JobSeekerProfileORM


class AdminActionResult(BaseModel):
    success: bool
    message: str
    data: dict | None = Field(default=None)


class ComplianceService(AdminServiceInterface):
    __dict__ = """
        Service for performing compliance and regulatory reporting across the job platform.

        This controller provides tools to assess compliance with South African B-BBEE standards,
        generate employment equity reports, analyze pay equity across gender and experience levels,
        and detect potential bias in the hiring pipeline. It enables administrators to monitor
        and enforce fair employment practices.

        Dependencies:
            - `session_factory` (Callable): A factory that provides a SQLAlchemy session.
            - Models:
                - `JobsORM`
                - `CompanyORM`
                - `JobSeekerProfileORM`
                - `JobApplicationORM`
            - Result Wrapper:
                - `AdminActionResult`: Used for standardized success/failure responses.

        Side Effects:
            - Performs read-only operations on the database.
            - No DB writes, session persistence, or external API usage.

        Methods:
            __init__(session_factory)
                Initializes the service with a SQLAlchemy session factory.

            execute(report_type: str, **kwargs) -> AdminActionResult
                Dispatches the specified compliance reporting method.

                Args:
                    report_type (str): Type of compliance report to generate. Must be one of:
                        - 'bee_compliance'
                        - 'employment_equity'
                        - 'pay_equity'
                        - 'bias_analysis'
                    **kwargs: Arguments required for the specific report method (e.g., `job_id`, `company_id`).

                Returns:
                    AdminActionResult: Encapsulates success state, message, and data (if any).

            _check_bee_compliance(job_id: str) -> AdminActionResult
                Evaluates B-BBEE (Broad-Based Black Economic Empowerment) compliance for a given job's company.

                Args:
                    job_id (str): ID of the job whose company's B-BBEE compliance is to be checked.

                Returns:
                    AdminActionResult: Compliance data including black ownership, skills development, and status.

            _generate_employment_equity_report() -> AdminActionResult
                Creates a snapshot report of gender and disability representation among job seekers.

                Returns:
                    AdminActionResult: Equity statistics including gender breakdown and disability count.

            _generate_pay_equity_report(company_id: str) -> AdminActionResult
                Aggregates salary ranges across different genders and experience levels within a company.

                Args:
                    company_id (str): ID of the company to analyze.

                Returns:
                    AdminActionResult: Grouped salary distribution report by demographic.

            _analyze_application_biases(job_id: str) -> AdminActionResult
                Detects potential bias in the job application process for a given job based on gender rejection rates.

                Args:
                    job_id (str): ID of the job to analyze.

                Returns:
                    AdminActionResult: Breakdown of applications and rejection rates across demographics.
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.__interface_map = {
            'bee_compliance': self._check_bee_compliance,
            'employment_equity': self._generate_employment_equity_report,
            'pay_equity': self._generate_pay_equity_report,
            'bias_analysis': self._analyze_application_biases
        }

    async def execute(self, action: str, *args, **kwargs):
        """
        Dynamically executes a method based on the provided action name.

        Args:
            action (str): The name of the method to execute (must be present in `_interface_schema`).
            *args: Positional arguments for the method.
            **kwargs: Keyword arguments for the method.

        Returns:
            Any: The result of the invoked method.

        Raises:
            ValueError: If the action does not exist in this service's schema
                        or if the found entry is not a callable method.
            RuntimeError: If an unexpected error occurs during the execution
                          of the target method.
        """
        try:
            method_to_execute = self.__interface_map[action]

            if method_to_execute is None:
                raise ValueError(f"Action '{action}' not found in {self.__class__.__name__}.")
            if inspect.iscoroutinefunction(method_to_execute):
                return await method_to_execute(*args, **kwargs)
            else:
                # noinspection PyArgumentList
                return method_to_execute(*args, **kwargs)
        # Catch specific exceptions that might be raised by the lookup or the method itself.
        except ValueError as e:
            # Re-raise the ValueError if it's one of the ones we explicitly raised.
            raise e
        except Exception as e:
            # Catch any other unexpected exceptions and wrap them in a RuntimeError.
            # Using 'from e' maintains the original exception's traceback, which is crucial for debugging.
            raise RuntimeError(f"Error executing action '{action}': {str(e)}") from e

    def _check_bee_compliance(self, job_id: str) -> AdminActionResult:
        """Check B-BBEE compliance for South African jobs"""
        try:
            with self.session_factory() as session:
                job = session.query(JobsORM).get(job_id)
                if not job:
                    return AdminActionResult(success=False, message="Job not found")

                company = session.query(CompanyORM).get(job.company_id)
                if not company:
                    return AdminActionResult(success=False, message="Company not found")

                compliance_data = {
                    'black_ownership': company.black_ownership_percent,
                    'skills_development': company.skills_development_budget,
                    'compliance_status': 'compliant' if company.bbbee_level else 'non-compliant'
                }

                return AdminActionResult(success=True, message="B-BBEE compliance check completed", data=compliance_data)
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error checking B-BBEE compliance: {str(e)}")

    def _generate_employment_equity_report(self) -> AdminActionResult:
        """Generate EE report for regulatory compliance"""
        try:
            with self.session_factory() as session:
                gender_dist = dict(
                    session.query(JobSeekerProfileORM.gender, func.count(JobSeekerProfileORM.user_uid))
                    .group_by(JobSeekerProfileORM.gender).all()
                )

                disability_count = session.query(
                    func.count(case((JobSeekerProfileORM.has_disability == True, 1)))
                ).scalar()

                report_data = {
                    'gender_distribution': gender_dist,
                    'disability_stats': disability_count,
                    'generated_at': datetime.now(timezone.utc).isoformat()
                }

                return AdminActionResult(success=True, message="Employment equity report generated", data=report_data)
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error generating EE report: data={str(e)}")

    def _generate_pay_equity_report(self, company_id: str) -> AdminActionResult:
        """Analyze salary distributions for pay equity"""
        try:
            with self.session_factory() as session:
                salary_data = session.query(
                    JobSeekerProfileORM.gender,
                    func.avg(JobsORM.salary_min),
                    func.avg(JobsORM.salary_max)
                ).join(JobApplicationORM).join(JobsORM).filter(
                    JobsORM.company_id == company_id
                ).group_by(
                    JobSeekerProfileORM.gender,
                ).all()

                report_data = {
                    "salary_distribution": [{
                        "gender": d[0],
                        "experience_level": d[1],
                        "avg_min_salary": float(d[2]) if d[2] else 0,
                        "avg_max_salary": float(d[3]) if d[3] else 0
                    } for d in salary_data]
                }

                return AdminActionResult(success=True, message="Pay equity report generated", data=report_data)
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error generating pay equity report: {str(e)}")

    def _analyze_application_biases(self, job_id: str) -> AdminActionResult:
        """Detect potential discrimination patterns in hiring process"""
        try:
            with self.session_factory() as session:
                demographics = session.query(
                    JobSeekerProfileORM.gender,
                    func.count(JobApplicationORM.application_id),
                    func.avg(case((JobApplicationORM.application_stage == 'REJECTED', 1), else_=0))
                ).join(JobApplicationORM).filter(
                    JobApplicationORM.job_id == job_id
                ).group_by(JobSeekerProfileORM.gender).all()

                bias_data = {
                    "demographic_breakdown": [{
                        "gender": d[0],
                        "applications": d[1],
                        "rejection_rate": float(d[2]) if d[2] else 0
                    } for d in demographics]
                }

                return AdminActionResult(success=True, message="Bias analysis completed", data=bias_data)
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error analyzing biases: {str(e)}")

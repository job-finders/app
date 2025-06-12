import asyncio
from datetime import datetime, timezone, timedelta
from typing import List

from flask import Flask, render_template
from pydantic import BaseModel, Field
from sqlalchemy import func, or_

from src.controllers.admin.services.analytics_service import AnalyticsService
from src.controllers.admin.services.compliance_service import ComplianceService
from src.controllers.admin.services.job_moderation import JobModerationService
from src.controllers.admin.services.job_recommendations import JobRecommendationService, JobRecommenderResult
from src.controllers.admin.services.security_service import SecurityService
from src.controllers.controller import error_handler, Controllers
from src.database.constants import utc_time
from src.database.models.admin_models import FlaggedUser
from src.database.models.jobs_model import Job, JobApprovalStatusEnum
from src.database.models.jobseeker_profile import JobSeekerProfile
from src.database.models.users import RolesEnum, User
from src.database.sql.admin_sql import FlaggedUserORM
from src.database.sql.analytics import UserSearchActivityORM
from src.database.sql.company import CompanyORM
from src.database.sql.jobs_sql import JobsORM, JobApprovalRequestORM, JobApplicationORM
from src.database.sql.jobseeker_profile import JobSeekerProfileORM
from src.database.sql.users import UserORM
from src.emailer import EmailModel
from src.utils.route_helpers import get_service


class AdminActionResult(BaseModel):
    success: bool
    message: str
    data: dict | None = Field(default=None)

class AdminController(Controllers):
    __doc__ ="""
    Controller for administrative operations, moderation, compliance, analytics, and security.

    This controller provides a unified interface for system administrators to perform job moderation,
    compliance checks, analytics, security monitoring, and data export. It orchestrates various
    service classes and exposes methods for both synchronous and asynchronous admin workflows.

    Dependencies:
        - Models: CompanyORM, JobsORM, JobApprovalRequestORM, JobVersionHistoryORM, JobApplicationORM,
          JobSeekerProfileORM, UserORM, UserSearchActivityORM
        - Services: JobModerationService, ComplianceService, AnalyticsService, SecurityService
        - Configuration: SQLAlchemy session factory, Flask app, logging, and controller registry

    Attributes:
        job_moderation_service (JobModerationService): Handles job approval, rejection, flagging, and anomaly detection.
        compliance_service (ComplianceService): Handles B-BBEE, employment equity, pay equity, and bias analysis.
        analytics_service (AnalyticsService): Provides system health, engagement, and audit log analytics.
        security_service (SecurityService): Monitors and flags suspicious user and employer activity.

    Methods:
        __init__(factory)
            Initialize the controller with a session factory and service instances.

        init_app(app: Flask)
            Register the controller with a Flask application.

        cleanup_old_approvals() -> AdminActionResult
            Delete job approval requests older than 30 days.
            Side effects: DB deletes.

        approve_job(job_id: str, reviewer_id: str) -> AdminActionResult
            Approve a flagged job posting.
            Inputs: job_id (str), reviewer_id (str)
            Side effects: DB updates.

        reject_job(job_id: str, reviewer_id: str, reason: str) -> AdminActionResult
            Reject a job posting with a reason.
            Inputs: job_id (str), reviewer_id (str), reason (str)
            Side effects: DB updates.

        flag_job(job_id: str, reason: str, reporter_id: str) -> AdminActionResult
            Flag a job for admin review.
            Inputs: job_id (str), reason (str), reporter_id (str)
            Side effects: DB inserts/updates.

        bulk_update_job_status(job_ids: List[str], new_status: str) -> AdminActionResult
            Bulk update job statuses.
            Inputs: job_ids (List[str]), new_status (str)
            Side effects: DB updates.

        detect_anomalous_job_postings() -> AdminActionResult
            Identify suspicious jobs using multi-factor analysis.
            Output: List of anomalous job postings.

        get_pending_approvals() -> AdminActionResult
            List all jobs needing moderation.
            Output: List of pending jobs.

        check_bee_compliance(job_id: str) -> AdminActionResult
            Check B-BBEE compliance for a job's company.
            Inputs: job_id (str)
            Output: Compliance data.

        generate_employment_equity_report() -> AdminActionResult
            Generate employment equity report.
            Output: Gender and disability statistics.

        generate_pay_equity_report(company_id: str) -> AdminActionResult
            Analyze salary distributions for pay equity.
            Inputs: company_id (str)
            Output: Salary distribution data.

        analyze_application_biases(job_id: str) -> AdminActionResult
            Detect discrimination patterns in hiring.
            Inputs: job_id (str)
            Output: Demographic breakdown and rejection rates.

        generate_system_health_report() -> AdminActionResult
            Monitor platform health metrics.
            Output: Job, user, and performance statistics.

        analyze_platform_engagement() -> AdminActionResult
            Track key engagement metrics.
            Output: User activity and feature usage.

        flag_unusual_user_activity(user_id: str) -> AdminActionResult
            Detect suspicious user behavior patterns.
            Inputs: user_id (str)
            Output: Risk analysis.

        get_job_audit_log(job_id: str) -> AdminActionResult
            Get modification history for a job.
            Inputs: job_id (str)
            Output: List of job version changes.

        export_user_data(user_id: str) -> AdminActionResult
            Export user data for GDPR compliance.
            Inputs: user_id (str)
            Output: User profile, search, and application data.

        export_company_data(company_id: str) -> AdminActionResult
            Export company data for GDPR compliance.
            Inputs: company_id (str)
            Output: Company data with relationships.

        review_company_verifications() -> AdminActionResult
            Identify companies needing verification checks.
            Output: List of unverified or flagged companies.

        get_admin_dashboard_data(user: User) -> AdminActionResult
            Gather and return comprehensive dashboard data for system admins.
            Inputs: user (User)
            Output: Aggregated statistics for dashboard display.

    Returns:
        AdminActionResult: Standardized response object with success status, message, data, and errors.

    Side Effects:
        - Database reads, writes, updates, and deletes.
        - Logging of suspicious activity.
        - May trigger external API calls via services (if implemented).

    """

    def __init__(self, factory):
        super().__init__(factory)
        self.job_moderation_service = JobModerationService(self.get_session, system_admin=self.get_system_admin)
        self.compliance_service = ComplianceService(self.get_session)
        self.analytics_service = AnalyticsService(self.get_session)
        self.security_service = SecurityService(self.get_session)
        self.job_recommendation_service = JobRecommendationService(self.get_session)

    def init_app(self, app: Flask):
        super().init_app(app=app)

    async def cleanup_old_approvals(self) -> AdminActionResult:
        """Cleanup job approvals older than 30 days"""
        try:
            self.logger.info("Scheduler Started Cron Job - cleanup_old_approvals")
            with self.get_session() as session:
                cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                deleted = session.query(JobApprovalRequestORM).filter(
                    JobApprovalRequestORM.requested_at < cutoff).delete()
                session.commit()
                return AdminActionResult(success=True, message=f"Cleaned up {deleted} old approvals",
                                         data={"deleted_count": deleted})
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error cleaning up approvals: {str(e)}")

    @error_handler
    async def send_job_alerts_to_users(self) -> AdminActionResult:
        """Send job alerts to users based on their preferences"""

        self.logger.info("Scheduler Started - Job Alerts Notifications Service - send_job_alerts_to_users")
        results = await self.job_recommendation_service.execute("recommend_jobs")

        if not results.success:
            self.logger.info("There are no Job Alerts to send")
            return AdminActionResult(success=False, message="There are no recommended jobs to send")

        profiles_job_alerts: list[JobRecommenderResult] = results.list_data
        alerts_tasks = []

        for recommendation in profiles_job_alerts:
            email_template = await self._compose_matching_jobs_email_body(recommended_jobs=recommendation.recommended_jobs, profile=recommendation.profile)
            _comp_email = dict(
                _html=email_template, _to=recommendation.profile.email, _subject="Recommended Job Alerts - Jobfinders.site"
            )
            email_message = EmailModel(**_comp_email)
            alerts_tasks.append(self._send_alert(email=email_message))

        results = await asyncio.gather(*alerts_tasks, return_exceptions=True)
        is_success_count = sum(1 for res in results if not isinstance(res, Exception))

        return AdminActionResult(success=is_success_count > 1, message=f" {str(is_success_count)}Job Alerts where Sent")


    @staticmethod
    async def _format_salary(job: Job) -> str:
        """Helper for salary formatting"""
        if job.salary_confidential:
            return "Competitive Salary"
        if job.salary_min and job.salary_max:
            return f"{job.salary_currency} {job.salary_min:,.0f} - {job.salary_max:,.0f}"
        return "Salary Not Disclosed"


    async def _compose_matching_jobs_email_body(self, recommended_jobs: list[Job], profile: JobSeekerProfile) -> str:
        """
        Generate HTML email body using template and job data
        """
        with self.app.app_context():
            job_data = [{
                'job_id': job.job_id,
                'title': job.title,
                'company': job.company.name if job.company else "Confidential",
                'location': job.location,
                'type': job.position_type.replace('_', ' ').title(),
                'remote': job.remote_policy.title(),
                'salary': await self._format_salary(job),
                'description': job.description[:200] + '...' if job.description else "",
                'url': job.application_url,
                'deadline': job.application_deadline.replace(
                    tzinfo=timezone.utc) if job.application_deadline else "ASAP"
            } for job in recommended_jobs if job.is_active]
            context = dict(first_name=profile.first_name, jobs=job_data, count=len(job_data))
            return render_template('jobseekers/email/job_alert.html', **context)

    @staticmethod
    async def _send_alert(email: EmailModel):
        """
        :param email:
        :return:
        """
        await get_service('send_mail')().send_mail_resend(email=email)


    # Job Moderation Methods
    @error_handler
    async def approve_jobs(self) -> AdminActionResult:

        """
        scheduled using task scheduler cron jobs
        Every 30 Minutes the system will run and try to approve jobs that, have been posted by companies
        """
        self.logger.info("Scheduler - Running Approve Jobs - Cron Job")
        results = await self.job_moderation_service.execute('approve')
        return results


    @error_handler
    async def reject_job(self, job_id: str, reviewer_id: str, reason: str) -> AdminActionResult:
        """Reject a job posting with reason"""
        return await self.job_moderation_service.execute('reject', job_id=job_id, reviewer_id=reviewer_id,
                                                         reason=reason)

    @error_handler
    async def flag_job(self, job_id: str, reason: str, reporter_id: str) -> AdminActionResult:
        """Flag a job for admin review"""
        return await self.job_moderation_service.execute('flag', job_id=job_id, reason=reason, reporter_id=reporter_id)

    @error_handler
    async def bulk_update_job_status(self, job_ids: List[str], new_status: str) -> AdminActionResult:
        """Admin bulk status update with validation"""
        return await self.job_moderation_service.execute('bulk_update', job_ids=job_ids, new_status=new_status)

    @error_handler
    async def detect_anomalous_job_postings(self) -> AdminActionResult:
        """Identify suspicious jobs using multi-factor analysis
        Identified Jobs will be shown on the admin interface where the admin could either activate the job or 
        de-activate it.
        """
        self.logger.info("Scheduler Started Service : detect_anomalous_job_postings")
        return await self.job_moderation_service.execute('detect_anomalies')

    # Compliance Methods
    @error_handler
    async def check_bee_compliance(self, job_id: str) -> AdminActionResult:
        """Check B-BBEE compliance for South African jobs"""
        return await self.compliance_service.execute('bee_compliance', job_id=job_id)

    @error_handler
    async def generate_employment_equity_report(self) -> AdminActionResult:
        """Generate EE report for regulatory compliance"""
        return await self.compliance_service.execute('employment_equity')

    @error_handler
    async def generate_pay_equity_report(self, company_id: str) -> AdminActionResult:
        """Analyze salary distributions"""
        return await self.compliance_service.execute('pay_equity', company_id=company_id)

    @error_handler
    async def analyze_application_biases(self, job_id: str) -> AdminActionResult:
        """Detect potential discrimination patterns in hiring process"""
        return await self.compliance_service.execute('bias_analysis', job_id=job_id)

    # Analytics Methods
    @error_handler
    async def generate_system_health_report(self) -> AdminActionResult:
        """Monitor platform health metrics"""
        return await self.analytics_service.execute('system_health')

    @error_handler
    async def analyze_platform_engagement(self) -> AdminActionResult:
        """Track key engagement metrics"""
        return await self.analytics_service.execute('engagement')
    @error_handler
    def get_system_admin(self) -> AdminActionResult:
        """
            returns system admin user
        :return:
        """
        with self.get_session() as session:
            admin_user_orm = session.query(UserORM).filter_by(role=RolesEnum.SYSTEM_ADMIN.value).first()
            data = User(**admin_user_orm.to_dict()) if isinstance(admin_user_orm, UserORM) else None
            return AdminActionResult(success=isinstance(data, User), message="Successfully ran get_system_admin",data=data)


    @error_handler
    async def flag_unusual_user_activity(self, admin_uid: str) -> AdminActionResult:
        """Detect suspicious user behavior patterns"""
        self.logger.info("Scheduler Started Service : flag_unusual_user_activity")
        action_result: AdminActionResult = await self.security_service.execute('flag_unusual_user_activity')
        flagged_users_models = []
        if action_result.success:
            for reference_id, message in action_result.list_data:
                flagged_users_models.append(FlaggedUserORM(**FlaggedUser(reference_id=reference_id, reason=message, flagged_by=admin_uid).model_dump()))

        with self.get_session() as session:
            session.add_all(flagged_users_models)

        return AdminActionResult(success=action_result.success, message=action_result.message, list_data=flagged_users_models)

    @error_handler
    async def evaluate_user_risks(self, admin_uid: str) -> AdminActionResult:
        """
        Run risk evaluations on flagged users and log admin recommendations.
        """
        self.logger.info("Scheduler Started Task : evaluate_user_risks")
        try:
            recommendations = await self.security_service.execute('apply_user_risk_recommendations', admin_uid=admin_uid)
            return recommendations

        except Exception as e:
            return AdminActionResult(
                success=False,
                message=f"Failed to generate risk recommendations: {str(e)}")

    @error_handler
    async def get_job_audit_log(self, job_id: str) -> AdminActionResult:
        """Get complete modification history for a job"""
        return await self.analytics_service.execute('audit_log', job_id=job_id)

    # Legacy compatibility methods (simplified)
    @error_handler
    def export_user_data(self, user_id: str) -> AdminActionResult:
        """GDPR-compliant data export"""
        try:
            with self.get_session() as session:
                profile = session.query(JobSeekerProfileORM).get(user_id)
                activities = session.query(UserSearchActivityORM).filter_by(user_id=user_id).all()
                applications = session.query(JobApplicationORM).filter_by(user_id=user_id).all()

                export_data = {
                    "profile": profile.to_dict() if profile else {},
                    "search_activities": [a.to_dict() for a in activities],
                    "applications": [a.to_dict() for a in applications],
                    "exported_at": datetime.now(timezone.utc).isoformat()
                }

                return AdminActionResult(success=True, message="User data exported successfully", data=export_data)
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error exporting user data: {str(e)}")

    @error_handler
    def export_company_data(self, company_id: str) -> AdminActionResult:
        """GDPR-compliant company data export"""
        from utils.route_helpers import get_controller
        company_controller = get_controller('company')
        company = company_controller.get_company_by_id(company_id)
        export_data = {
            "company_data": company.to_dict(include_relationships=True),
            "exported_at": utc_time()
        }

        return AdminActionResult(success=True, message="Company data exported successfully", data=export_data)

    @error_handler
    async def review_company_verifications(self) -> AdminActionResult:
        """Identify companies needing verification checks"""
        # noinspection PyBroadException
        try:
            with self.get_session() as session:
                unverified_companies = session.query(CompanyORM).filter(
                    or_(
                        CompanyORM.is_verified == False,
                        CompanyORM.company_id.in_(
                            session.query(JobsORM.company_id)
                            .join(JobApprovalRequestORM)
                            .filter(JobApprovalRequestORM.status == JobApprovalStatusEnum.FLAGGED)
                            .group_by(JobsORM.company_id)
                            .having(func.count(JobsORM.job_id) > 3)
                        )
                    )
                ).all()

                companies_data = [{
                    "company_id": company.id,
                    "name": company.name,
                    "is_verified": company.is_verified,
                    "flagged_jobs_count": getattr(company, 'flagged_jobs_count', 0)
                } for company in unverified_companies]

                return AdminActionResult(
                    success=True,
                    message=f"Found {len(unverified_companies)} companies needing verification",data={"companies": companies_data})

        except Exception as e:
            return AdminActionResult(success=False,message=f"Error reviewing company verifications: {str(e)}")

    @error_handler
    async def get_admin_dashboard_data(self):
        """
        Gather and return comprehensive dashboard data for system admins.
        Uses detailed data from other controller methods/services.
        """
        try:
            # User stats
            user_stats_result = await self.analytics_service.execute('system_health')
            user_stats = user_stats_result.data.get("user_stats", {}) if user_stats_result.success else {}

            # Resume stats
            ee_report_result = await self.compliance_service.execute('employment_equity')
            resume_stats = {
                "total": ee_report_result.data.get("gender_distribution", {}).get("total", None),
                "completed": None  # Add more detailed resume stats if available from another service
            } if ee_report_result.success else {}

            # Job stats
            job_stats_result = await self.analytics_service.execute('system_health')
            job_stats = job_stats_result.data.get("job_stats", {}) if job_stats_result.success else {}

            # Company stats
            company_stats = {
                "total": None,
                "verified": None
            }
            # noinspection PyBroadException
            try:
                with self.get_session() as session:
                    company_stats["total"] = session.query(func.count(CompanyORM.company_id)).scalar()
                    company_stats["verified"] = session.query(func.count(CompanyORM.company_id)).filter_by(verified=True).scalar()
            except Exception:
                pass

            # Application stats
            application_stats = {
                "total": None
            }
            # noinspection PyBroadException
            try:
                with self.get_session() as session:
                    application_stats["total"] = session.query(func.count(JobApplicationORM.application_id)).scalar()
            except Exception:
                pass

            # System health
            system_health = user_stats_result.data if user_stats_result.success else {}

            # Engagement
            engagement_result = await self.analytics_service.execute('engagement')
            engagement = engagement_result.data if engagement_result.success else {}

            dashboard_data = {
                "user_stats": user_stats,
                "resume_stats": resume_stats,
                "job_stats": job_stats,
                "company_stats": company_stats,
                "application_stats": application_stats,
                "system_health": system_health,
                "engagement": engagement,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            return AdminActionResult(success=True, message="Admin dashboard data loaded", data=dashboard_data)
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error loading dashboard data: {str(e)}")


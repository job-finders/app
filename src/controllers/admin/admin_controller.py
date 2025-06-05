from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from flask import Flask
from sqlalchemy import func, case, or_, text

from src.database.sql.company import CompanyORM
from src.database.sql.analytics import UserSearchActivityORM
from src.database.sql.users import UserORM
from src.database.sql.jobseeker_profile import JobSeekerProfileORM
from src.controllers.controller import error_handler, Controllers
from src.database.models.jobs_model import Job, Company, JobApplication, JobApprovalStatusEnum
from src.database.sql.jobs_sql import JobsORM, JobApprovalRequestORM, JobVersionHistoryORM, JobApplicationORM


class AdminPermissionLevel(Enum):
    """Define admin permission levels"""
    VIEWER = "viewer"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


@dataclass
class AdminActionResult:
    """Standardized response for admin actions"""
    success: bool
    message: str
    data: Optional[Dict] = None
    errors: Optional[List[str]] = None


class AdminServiceInterface(ABC):
    """Interface for admin services"""

    @abstractmethod
    def execute(self, *args, **kwargs) -> AdminActionResult:
        pass


class JobModerationService(AdminServiceInterface):
    """Service for job moderation operations"""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def execute(self, action: str, **kwargs) -> AdminActionResult:
        """Execute job moderation action"""
        actions = {
            'approve': self._approve_job,
            'reject': self._reject_job,
            'flag': self._flag_job,
            'bulk_update': self._bulk_update_status,
            'detect_anomalies': self._detect_anomalous_postings
        }

        if action not in actions:
            return AdminActionResult(False, f"Unknown action: {action}")

        return actions[action](**kwargs)

    def _approve_job(self, job_id: str, reviewer_id: str) -> AdminActionResult:
        """Approve a flagged job posting"""
        try:
            with self.session_factory() as session:
                request = session.query(JobApprovalRequestORM).filter_by(job_id=job_id).first()
                if not request:
                    return AdminActionResult(False, "No approval request exists for this job")

                job = session.query(JobsORM).get(job_id)
                if not job:
                    return AdminActionResult(False, "Job not found")

                job.status = "active"
                request.status = JobApprovalStatusEnum.APPROVED
                request.reviewer_id = reviewer_id
                request.reviewed_at = datetime.utcnow()

                session.commit()
                return AdminActionResult(True, "Job approved successfully", {"job_id": job_id})
        except Exception as e:
            return AdminActionResult(False, f"Error approving job: {str(e)}")

    def _reject_job(self, job_id: str, reviewer_id: str, reason: str) -> AdminActionResult:
        """Reject a job posting with reason"""
        try:
            with self.session_factory() as session:
                request = session.query(JobApprovalRequestORM).filter_by(job_id=job_id).first()
                if not request:
                    return AdminActionResult(False, "No approval request exists for this job")

                job = session.query(JobsORM).get(job_id)
                if not job:
                    return AdminActionResult(False, "Job not found")

                job.status = "archived"
                request.status = JobApprovalStatusEnum.REJECTED
                request.reviewer_id = reviewer_id
                request.review_notes = reason
                request.reviewed_at = datetime.utcnow()

                session.commit()
                return AdminActionResult(True, "Job rejected successfully", {"job_id": job_id, "reason": reason})
        except Exception as e:
            return AdminActionResult(False, f"Error rejecting job: {str(e)}")

    def _flag_job(self, job_id: str, reason: str, reporter_id: str) -> AdminActionResult:
        """Flag a job for admin review"""
        try:
            with self.session_factory() as session:
                job = session.query(JobsORM).get(job_id)
                if not job:
                    return AdminActionResult(False, "Job not found")

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
                return AdminActionResult(True, "Job flagged successfully", {"job_id": job_id})
        except Exception as e:
            return AdminActionResult(False, f"Error flagging job: {str(e)}")

    def _bulk_update_status(self, job_ids: List[str], new_status: str) -> AdminActionResult:
        """Bulk update job statuses"""
        valid_statuses = ['active', 'archived', 'pending_review']
        if new_status not in valid_statuses:
            return AdminActionResult(False, f"Invalid status. Allowed: {valid_statuses}")

        try:
            with self.session_factory() as session:
                updated = session.query(JobsORM).filter(JobsORM.job_id.in_(job_ids)).update(
                    {JobsORM.status: new_status}
                )
                session.commit()
                return AdminActionResult(True, f"Updated {updated} jobs", {"updated_count": updated})
        except Exception as e:
            return AdminActionResult(False, f"Error updating jobs: {str(e)}")

    def _detect_anomalous_postings(self) -> AdminActionResult:
        """Detect suspicious job postings"""
        try:
            with self.session_factory() as session:
                anomalies = []

                # Unverified companies
                unverified = session.query(JobsORM).join(CompanyORM).filter(
                    CompanyORM.verified == False
                ).all()

                # Spam patterns
                spam_keywords = ["earn fast", "work from home", "no experience needed"]
                spam_jobs = session.query(JobsORM).filter(
                    or_(*[JobsORM.description.ilike(f"%{kw}%") for kw in spam_keywords])
                ).all()

                # Combine results
                all_anomalies = list({j.job_id: j for j in unverified + spam_jobs}.values())

                return AdminActionResult(
                    True,
                    f"Found {len(all_anomalies)} anomalous postings",
                    {"anomalies": [{"job_id": j.job_id, "title": j.title} for j in all_anomalies]}
                )
        except Exception as e:
            return AdminActionResult(False, f"Error detecting anomalies: {str(e)}")


class ComplianceService(AdminServiceInterface):
    """Service for compliance and regulatory operations"""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def execute(self, report_type: str, **kwargs) -> AdminActionResult:
        """Execute compliance report generation"""
        reports = {
            'bee_compliance': self._check_bee_compliance,
            'employment_equity': self._generate_employment_equity_report,
            'pay_equity': self._generate_pay_equity_report,
            'bias_analysis': self._analyze_application_biases
        }

        if report_type not in reports:
            return AdminActionResult(False, f"Unknown report type: {report_type}")

        return reports[report_type](**kwargs)

    def _check_bee_compliance(self, job_id: str) -> AdminActionResult:
        """Check B-BBEE compliance for South African jobs"""
        try:
            with self.session_factory() as session:
                job = session.query(JobsORM).get(job_id)
                if not job:
                    return AdminActionResult(False, "Job not found")

                company = session.query(CompanyORM).get(job.company_id)
                if not company:
                    return AdminActionResult(False, "Company not found")

                compliance_data = {
                    'black_ownership': company.black_ownership_percent,
                    'skills_development': company.skills_development_budget,
                    'compliance_status': 'compliant' if company.bbbee_level else 'non-compliant'
                }

                return AdminActionResult(True, "B-BBEE compliance check completed", compliance_data)
        except Exception as e:
            return AdminActionResult(False, f"Error checking B-BBEE compliance: {str(e)}")

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
                    'generated_at': datetime.utcnow().isoformat()
                }

                return AdminActionResult(True, "Employment equity report generated", report_data)
        except Exception as e:
            return AdminActionResult(False, f"Error generating EE report: {str(e)}")

    def _generate_pay_equity_report(self, company_id: str) -> AdminActionResult:
        """Analyze salary distributions for pay equity"""
        try:
            with self.session_factory() as session:
                salary_data = session.query(
                    JobSeekerProfileORM.gender,
                    JobSeekerProfileORM.experience_level,
                    func.avg(JobsORM.salary_min),
                    func.avg(JobsORM.salary_max)
                ).join(JobApplicationORM).join(JobsORM).filter(
                    JobsORM.company_id == company_id
                ).group_by(
                    JobSeekerProfileORM.gender,
                    JobSeekerProfileORM.experience_level
                ).all()

                report_data = {
                    "salary_distribution": [{
                        "gender": d[0],
                        "experience_level": d[1],
                        "avg_min_salary": float(d[2]) if d[2] else 0,
                        "avg_max_salary": float(d[3]) if d[3] else 0
                    } for d in salary_data]
                }

                return AdminActionResult(True, "Pay equity report generated", report_data)
        except Exception as e:
            return AdminActionResult(False, f"Error generating pay equity report: {str(e)}")

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

                return AdminActionResult(True, "Bias analysis completed", bias_data)
        except Exception as e:
            return AdminActionResult(False, f"Error analyzing biases: {str(e)}")


class AnalyticsService(AdminServiceInterface):
    """Service for analytics and reporting"""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def execute(self, metric_type: str, **kwargs) -> AdminActionResult:
        """Execute analytics operations"""
        metrics = {
            'system_health': self._generate_system_health_report,
            'engagement': self._analyze_platform_engagement,
            'user_activity': self._flag_unusual_user_activity,
            'audit_log': self._get_job_audit_log
        }

        if metric_type not in metrics:
            return AdminActionResult(False, f"Unknown metric type: {metric_type}")

        return metrics[metric_type](**kwargs)

    def _generate_system_health_report(self) -> AdminActionResult:
        """Monitor platform health metrics"""
        try:
            with self.session_factory() as session:
                health_data = {
                    "job_stats": {
                        "total": session.query(func.count(JobsORM.job_id)).scalar(),
                        "active": session.query(func.count(JobsORM.job_id)).filter_by(status='active').scalar()
                    },
                    "user_stats": {
                        "total": session.query(func.count(UserORM.uid)).scalar(),
                        "active": session.query(func.count(UserORM.uid)).filter(
                            UserORM.last_login > datetime.now(timezone.utc) - timedelta(days=30)
                        ).scalar()
                    },
                    "performance_metrics": {
                        "avg_response_time": 0.25,  # Placeholder
                        "error_rate": 0.01  # Placeholder
                    },
                    "generated_at": datetime.utcnow().isoformat()
                }

                return AdminActionResult(True, "System health report generated", health_data)
        except Exception as e:
            return AdminActionResult(False, f"Error generating system health report: {str(e)}")

    def _analyze_platform_engagement(self) -> AdminActionResult:
        """Track key engagement metrics"""
        try:
            with self.session_factory() as session:
                engagement_data = {
                    "daily_active_users": session.query(func.count(UserORM.uid))
                    .filter(UserORM.last_login > datetime.now(timezone.utc) - timedelta(days=1))
                    .scalar(),
                    "weekly_retention": self._calculate_retention(session),
                    "feature_usage": {
                        "searches": session.query(func.count(UserSearchActivityORM.id)).scalar(),
                        "applications": session.query(func.count(JobApplicationORM.application_id)).scalar()
                    },
                    "generated_at": datetime.utcnow().isoformat()
                }

                return AdminActionResult(True, "Platform engagement analysis completed", engagement_data)
        except Exception as e:
            return AdminActionResult(False, f"Error analyzing platform engagement: {str(e)}")

    def _flag_unusual_user_activity(self, user_id: str) -> AdminActionResult:
        """Detect suspicious user behavior patterns"""
        try:
            with self.session_factory() as session:
                # Check application patterns
                app_stats = session.query(
                    func.count(JobApplicationORM.application_id),
                    func.min(JobApplicationORM.applied_date),
                    func.max(JobApplicationORM.applied_date)
                ).filter_by(user_id=user_id).first()

                # Check search activity
                search_stats = session.query(
                    func.count(UserSearchActivityORM.id),
                    func.avg(UserSearchActivityORM.result_count)
                ).filter_by(user_id=user_id).first()

                activity_data = {
                    "application_metrics": {
                        "total": app_stats[0] if app_stats else 0,
                        "time_span": (app_stats[2] - app_stats[1]).total_seconds() if app_stats and app_stats[
                            0] > 0 else 0
                    },
                    "search_metrics": {
                        "total_searches": search_stats[0] if search_stats else 0,
                        "avg_results": float(search_stats[1]) if search_stats and search_stats[1] else 0
                    },
                    "risk_score": self._calculate_risk_score(app_stats, search_stats)
                }

                return AdminActionResult(True, "User activity analysis completed", activity_data)
        except Exception as e:
            return AdminActionResult(False, f"Error analyzing user activity: {str(e)}")

    def _get_job_audit_log(self, job_id: str) -> AdminActionResult:
        """Get complete modification history for a job"""
        try:
            with self.session_factory() as session:
                versions = session.query(JobVersionHistoryORM).filter_by(job_id=job_id) \
                    .order_by(JobVersionHistoryORM.modified_at.desc()).all()

                audit_data = {
                    "job_id": job_id,
                    "history": [{
                        'modified_at': v.modified_at.isoformat() if v.modified_at else None,
                        'user_id': v.modified_by,
                        'changes': v.changes
                    } for v in versions]
                }

                return AdminActionResult(True, "Job audit log retrieved", audit_data)
        except Exception as e:
            return AdminActionResult(False, f"Error retrieving audit log: {str(e)}")

    def _calculate_retention(self, session):
        """Calculate weekly user retention rate"""
        try:
            retention_data = session.query(
                func.count().label('signups'),
                func.sum(
                    case(
                        (UserORM.last_login >= func.now() - text("INTERVAL '7 DAYS'"), 1),
                        else_=0
                    )
                ).label('active')
            ).filter(
                UserORM.created_at.between(
                    func.now() - text("INTERVAL '14 DAYS'"),
                    func.now() - text("INTERVAL '7 DAYS'")
                )
            ).first()

            signups = retention_data.signups if retention_data else 0
            active_users = retention_data.active if retention_data else 0

            return active_users / signups if signups > 0 else 0
        except Exception:
            return 0

    def _calculate_risk_score(self, app_stats, search_stats):
        """Calculate composite risk score 0-100"""
        try:
            if not app_stats or not search_stats:
                return 0

            app_rate = app_stats[0] / ((app_stats[2] - app_stats[1]).total_seconds() / 3600 + 1) if app_stats[
                                                                                                        0] > 0 else 0
            search_intensity = search_stats[0] / (search_stats[1] or 1)
            return min(100, int(app_rate * 10 + search_intensity * 5))
        except Exception:
            return 0


class AdminController(Controllers):
    """Refactored Admin Controller with service-oriented architecture"""

    def __init__(self, factory):
        super().__init__(factory)
        self.job_moderation_service = JobModerationService(self.get_session)
        self.compliance_service = ComplianceService(self.get_session)
        self.analytics_service = AnalyticsService(self.get_session)

    def init_app(self, app: Flask):
        super().init_app(app=app)

    def cleanup_old_approvals(self) -> AdminActionResult:
        """Cleanup job approvals older than 30 days"""
        try:
            with self.get_session() as session:
                cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                deleted = session.query(JobApprovalRequestORM).filter(
                    JobApprovalRequestORM.requested_at < cutoff
                ).delete()
                session.commit()

                return AdminActionResult(True, f"Cleaned up {deleted} old approvals", {"deleted_count": deleted})
        except Exception as e:
            return AdminActionResult(False, f"Error cleaning up approvals: {str(e)}")

    # Job Moderation Methods
    @error_handler
    def approve_job(self, job_id: str, reviewer_id: str) -> AdminActionResult:
        """Approve a flagged job posting"""
        return self.job_moderation_service.execute('approve', job_id=job_id, reviewer_id=reviewer_id)

    @error_handler
    def reject_job(self, job_id: str, reviewer_id: str, reason: str) -> AdminActionResult:
        """Reject a job posting with reason"""
        return self.job_moderation_service.execute('reject', job_id=job_id, reviewer_id=reviewer_id, reason=reason)

    @error_handler
    def flag_job(self, job_id: str, reason: str, reporter_id: str) -> AdminActionResult:
        """Flag a job for admin review"""
        return self.job_moderation_service.execute('flag', job_id=job_id, reason=reason, reporter_id=reporter_id)

    @error_handler
    def bulk_update_job_status(self, job_ids: List[str], new_status: str) -> AdminActionResult:
        """Admin bulk status update with validation"""
        return self.job_moderation_service.execute('bulk_update', job_ids=job_ids, new_status=new_status)

    @error_handler
    def detect_anomalous_job_postings(self) -> AdminActionResult:
        """Identify suspicious jobs using multi-factor analysis"""
        return self.job_moderation_service.execute('detect_anomalies')

    @error_handler
    def get_pending_approvals(self) -> AdminActionResult:
        """List all jobs needing moderation"""
        try:
            with self.get_session() as session:
                pending_jobs = session.query(JobsORM).join(JobApprovalRequestORM).filter(
                    JobApprovalRequestORM.status == JobApprovalStatusEnum.PENDING
                ).all()

                pending_data = [{
                    "job_id": job.job_id,
                    "title": job.title,
                    "company_id": job.company_id,
                    "requested_at": job.approval_request.requested_at.isoformat() if job.approval_request.requested_at else None
                } for job in pending_jobs]

                return AdminActionResult(True, f"Found {len(pending_jobs)} pending approvals",
                                         {"pending_jobs": pending_data})
        except Exception as e:
            return AdminActionResult(False, f"Error retrieving pending approvals: {str(e)}")

    # Compliance Methods
    @error_handler
    def check_bee_compliance(self, job_id: str) -> AdminActionResult:
        """Check B-BBEE compliance for South African jobs"""
        return self.compliance_service.execute('bee_compliance', job_id=job_id)

    @error_handler
    def generate_employment_equity_report(self) -> AdminActionResult:
        """Generate EE report for regulatory compliance"""
        return self.compliance_service.execute('employment_equity')

    @error_handler
    def generate_pay_equity_report(self, company_id: str) -> AdminActionResult:
        """Analyze salary distributions"""
        return self.compliance_service.execute('pay_equity', company_id=company_id)

    @error_handler
    def analyze_application_biases(self, job_id: str) -> AdminActionResult:
        """Detect potential discrimination patterns in hiring process"""
        return self.compliance_service.execute('bias_analysis', job_id=job_id)

    # Analytics Methods
    @error_handler
    def generate_system_health_report(self) -> AdminActionResult:
        """Monitor platform health metrics"""
        return self.analytics_service.execute('system_health')

    @error_handler
    def analyze_platform_engagement(self) -> AdminActionResult:
        """Track key engagement metrics"""
        return self.analytics_service.execute('engagement')

    @error_handler
    def flag_unusual_user_activity(self, user_id: str) -> AdminActionResult:
        """Detect suspicious user behavior patterns"""
        return self.analytics_service.execute('user_activity', user_id=user_id)

    @error_handler
    def get_job_audit_log(self, job_id: str) -> AdminActionResult:
        """Get complete modification history for a job"""
        return self.analytics_service.execute('audit_log', job_id=job_id)

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
                    "exported_at": datetime.utcnow().isoformat()
                }

                return AdminActionResult(True, "User data exported successfully", export_data)
        except Exception as e:
            return AdminActionResult(False, f"Error exporting user data: {str(e)}")

    @error_handler
    def export_company_data(self, company_id: str) -> AdminActionResult:
        """GDPR-compliant company data export"""
        try:
            with self.get_session() as session:
                company = session.query(CompanyORM).get(company_id)

                if not company:
                    return AdminActionResult(False, "Company not found")

                export_data = {
                    "company_data": company.to_dict(include_relationships=True),
                    "exported_at": datetime.utcnow().isoformat()
                }

                return AdminActionResult(True, "Company data exported successfully", export_data)
        except Exception as e:
            return AdminActionResult(False, f"Error exporting company data: {str(e)}")

    @error_handler
    def review_company_verifications(self) -> AdminActionResult:
        """Identify companies needing verification checks"""
        try:
            with self.get_session() as session:
                unverified_companies = session.query(CompanyORM).filter(
                    or_(
                        CompanyORM.is_verified == False,
                        CompanyORM.id.in_(
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
                    True,
                    f"Found {len(unverified_companies)} companies needing verification",
                    {"companies": companies_data}
                )
        except Exception as e:
            return AdminActionResult(False, f"Error reviewing company verifications: {str(e)}")
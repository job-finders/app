
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

from flask import Flask
from sqlalchemy import func, case, or_

from src.database.sql.analytics import UserSearchActivityORM
from src.database.sql.users import UserORM
from src.database.sql.jobseeker_profile import JobSeekerProfileORM
from src.controllers.controller import error_handler, Controllers
from src.database.models.jobs_model import Job, Company, JobApplication, JobApprovalStatusEnum
from src.database.sql.jobs_sql import JobsORM, CompanyORM, JobApprovalRequestORM, JobVersionHistoryORM, \
    JobApplicationORM


class AdminController(Controllers):
    def __init__(self):
        super().__init__()

    def init_app(self, app: Flask):
        super().init_app(app=app)

    # Add permission checks to critical methods
    def _admin_only(self):
        if not current_user.has_role('admin'):
            raise PermissionError("Admin privileges required")

    def cleanup_old_approvals(self):
        """
            will cleanup job approvals older than 30 days
        :return:
        """
        with self.get_session() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            session.query(JobApprovalRequestORM).filter(JobApprovalRequestORM.requested_at < cutoff).delete()

    # --- Requested Methods ---
    @error_handler
    async def check_bee_compliance(self, job_id: str) -> dict:
        """Check B-BBEE compliance for South African jobs"""
        with self.get_session() as session:
            job = session.query(JobsORM).get(job_id)
            company = session.query(CompanyORM).get(job.company_id)

            return {
                'black_ownership': company.black_ownership_percent,
                'skills_development': company.skills_development_budget,
                'compliance_status': 'compliant' if company.bbbee_level else 'non-compliant'
            }

    @error_handler
    async def get_job_audit_log(self, job_id: str) -> list[dict]:
        """Get complete modification history for a job"""
        with self.get_session() as session:
            versions = session.query(JobVersionHistoryORM).filter_by(job_id=job_id) \
                .order_by(JobVersionHistoryORM.modified_at.desc()).all()

            return [{
                'modified_at': v.modified_at,
                'user_id': v.modified_by,
                'changes': v.changes
            } for v in versions]

    def audit_job_post_evolution(self, job_id: str) -> dict:
        """Track historical changes to a job post"""
        with self.get_session() as session:
            versions = session.query(JobVersionHistoryORM).filter_by(job_id=job_id) \
                .order_by(JobVersionHistoryORM.version.desc()).all()

            return {
                "current": Job.from_orm(session.query(JobsORM).get(job_id)),
                "history": [{
                    "version": v.version,
                    "modified_at": v.modified_at,
                    "changes": v.changes,
                    "modified_by": v.modifier.email if v.modifier else None
                } for v in versions]
            }


    @error_handler
    async def bulk_update_job_status(self, job_ids: list[str], new_status: str) -> dict:
        """Admin bulk status update with validation"""
        with self.get_session() as session:
            valid_statuses = ['active', 'archived', 'pending_review']
            if new_status not in valid_statuses:
                raise ValueError(f"Invalid status. Allowed: {valid_statuses}")

            updated = session.query(JobsORM) \
                .filter(JobsORM.job_id.in_(job_ids)) \
                .update({JobsORM.status: new_status})

            session.commit()
            return {'updated_count': updated}

    @error_handler
    async def generate_employment_equity_report(self) -> dict:
        """Generate EE report for regulatory compliance"""
        with self.get_session() as session:
            return {
                'gender_distribution': dict(
                    session.query(JobSeekerProfileORM.gender, func.count(JobSeekerProfileORM.user_uid))
                    .group_by(JobSeekerProfileORM.gender).all()
                ),
                'disability_stats': session.query(
                    func.count(case((JobSeekerProfileORM.has_disability == True, 1)))
                ).scalar()
            }
    
    @error_handler
    def detect_anomalous_job_postings(self) -> list[Job]:
        """
        Identify suspicious jobs using multi-factor analysis
        Returns jobs needing review with anomaly scores
        """
        with self.get_session() as session:
            # 1. Find jobs from unverified companies
            unverified = session.query(JobsORM).join(CompanyORM).filter(
                CompanyORM.verified == False
            ).all()

            # 2. Detect spam patterns in title/description
            spam_keywords = ["earn fast", "work from home", "no experience needed"]
            spam_jobs = session.query(JobsORM).filter(
                or_(*[JobsORM.description.ilike(f"%{kw}%") for kw in spam_keywords])
            ).all()

            # 3. Detect salary anomalies
            avg_salaries = self._get_average_salaries()
            salary_anomalies = session.query(JobsORM).filter(
                JobsORM.salary_min < (avg_salaries.get(JobsORM.position_type, 0) * 0.5)
            ).all()

            # Combine and deduplicate
            return list({j.job_id: j for j in unverified + spam_jobs + salary_anomalies}.values())

    @error_handler
    def approve_job(self, job_id: str, reviewer_id: str) -> Job:
        """Approve a flagged job posting"""
        with self.get_session() as session:
            request = session.query(JobApprovalRequestORM).filter_by(job_id=job_id).first()
            if not request:
                raise ValueError("No approval request exists for this job")

            job = session.query(JobsORM).get(job_id)
            job.status = "active"

            request.status = JobApprovalStatusEnum.APPROVED
            request.reviewer_id = reviewer_id
            request.reviewed_at = datetime.utcnow()

            session.commit()
            return Job.from_orm(job)

    @error_handler
    def reject_job(self, job_id: str, reviewer_id: str, reason: str) -> Job:
        """Reject a job posting with reason"""
        with self.get_session() as session:
            request = session.query(JobApprovalRequestORM).filter_by(job_id=job_id).first()
            if not request:
                raise ValueError("No approval request exists for this job")

            job = session.query(JobsORM).get(job_id)
            job.status = "archived"

            request.status = JobApprovalStatusEnum.REJECTED
            request.reviewer_id = reviewer_id
            request.review_notes = reason
            request.reviewed_at = datetime.utcnow()

            session.commit()
            return Job.from_orm(job)

    @error_handler
    def get_pending_approvals(self) -> list[Job]:
        """List all jobs needing moderation"""
        with self.get_session() as session:
            return session.query(JobsORM).join(JobApprovalRequestORM).filter(
                JobApprovalRequestORM.status == JobApprovalStatusEnum.PENDING
            ).all()

    @error_handler
    def flag_job(self, job_id: str, reason: str, reporter_id: str):
        """Flag a job for admin review"""
        with self.get_session() as session:
            job = session.query(JobsORM).get(job_id)
            if not job.approval_request:
                request = JobApprovalRequestORM(
                    job_id=job_id,
                    status=JobApprovalStatusEnum.FLAGGED,
                    flags={"manual_flag": True},
                    review_notes=reason
                )
                session.add(request)
            else:
                job.approval_request.status = JobApprovalStatusEnum.FLAGGED
                job.approval_request.review_notes = reason

            session.commit()

    def _analyze_salary_equity(self, session) -> dict:
        """Gender pay gap analysis"""
        # Requires integration with user demographics
        return {
            "gender_gap": session.query(
                func.avg(JobsORM.salary_min).filter_by(gender="male"),
                func.avg(JobsORM.salary_min).filter_by(gender="female")
            ).first()
        }

    @error_handler
    def flag_unusual_user_activity(self, user_id: str) -> Dict:
        """
        Detect suspicious user behavior patterns
        """
        with self.get_session() as session:
            # Check application patterns
            app_stats = session.query(
                func.count(JobApplicationORM.application_id),
                func.min(JobApplicationORM.applied_date),
                func.max(JobApplicationORM.applied_date)
            ).filter_by(user_id=user_id).first()

            # Check search activity
            search_stats = session.query(
                func.count(SearchActivityORM.id),
                func.avg(UserSearchActivityORM.result_count)
            ).filter_by(user_id=user_id).first()

            return {
                "application_metrics": {
                    "total": app_stats[0],
                    "time_span": (app_stats[2] - app_stats[1]).total_seconds() if app_stats[0] > 0 else 0
                },
                "search_metrics": {
                    "total_searches": search_stats[0],
                    "avg_results": search_stats[1]
                },
                "risk_score": self._calculate_risk_score(app_stats, search_stats)
            }

    @error_handler
    async def review_company_verifications(self) -> List[Company]:
        """
        Identify companies needing verification checks
        """
        with self.get_session() as session:
            return session.query(CompanyORM).filter(
                or_(
                    CompanyORM.verified == False,
                    CompanyORM.id.in_(
                        session.query(JobsORM.company_id)
                        .join(JobApprovalRequestORM)
                        .filter(JobApprovalRequestORM.status == JobApprovalStatusEnum.FLAGGED)
                        .group_by(JobsORM.company_id)
                        .having(func.count(JobsORM.job_id) > 3)
                    )
                )
            ).all()

    @error_handler
    async def analyze_application_biases(self, job_id: str) -> Dict:
        """
            Detect potential discrimination patterns in hiring process
        """
        with self.get_session() as session:
            demographics = session.query(
                JobSeekerProfileORM.gender,
                func.count(JobApplicationORM.application_id),
                func.avg(case((JobApplicationORM.application_stage == 'REJECTED', 1), else_=0))
            ).join(JobApplicationORM).filter(
                JobApplicationORM.job_id == job_id
            ).group_by(
                JobSeekerProfileORM.gender,
            ).all()

            return {
                "demographic_breakdown": [{
                    "gender": d[0],
                    "applications": d[2],
                    "rejection_rate": d[3]
                } for d in demographics]
            }

    @error_handler
    def generate_system_health_report(self) -> Dict:
        """
        Monitor platform health metrics
        """
        with self.get_session() as session:
            return {
                "job_stats": {
                    "total": session.query(func.count(JobsORM.job_id)).scalar(),
                    "active": session.query(func.count(JobsORM.job_id)).filter_by(status='active').scalar()
                },
                "user_stats": {
                    "total": session.query(func.count(UserORM.uid)).scalar(),
                    "active": session.query(func.count(UserORM.uid)).filter(
                        UserORM.last_login > datetime.now(timezone.utc) - timedelta(days=30)).scalar()
                },
                "performance_metrics": {
                    "avg_response_time": self._get_avg_response_time(),
                    "error_rate": self._get_error_rate()
                }
            }

    @error_handler
    def manage_content_flags(self, content_type: str, content_id: str) -> Dict:
        """
        Handle user-flagged content moderation
        """
        with self.get_session() as session:
            content_map = {
                "job": JobsORM,
                "company": CompanyORM,
                "user": UserORM
            }

            model = content_map.get(content_type.lower())
            if not model:
                raise ValueError("Invalid content type")

            flagged_content = session.query(model).get(content_id)
            return {
                "content_type": content_type,
                "content_id": content_id,
                "status": flagged_content.status if hasattr(flagged_content, 'status') else 'active',
                "flags": getattr(flagged_content, 'flags', [])
            }

    @error_handler
    def export_user_data(self, user_id: str) -> Dict:
        """
        GDPR-compliant data export
        """
        with self.get_session() as session:
            profile = session.query(JobSeekerProfileORM).get(user_id)
            activities = session.query(UserSearchActivityORM).filter_by(user_id=user_id).all()
            applications = session.query(JobApplicationORM).filter_by(user_id=user_id).all()

            return {
                "profile": profile.to_dict() if profile else {},
                "search_activities": [a.to_dict() for a in activities],
                "applications": [a.to_dict() for a in applications],
                "documents": self._get_user_documents(user_id)
            }

    @error_handler
    def analyze_platform_engagement(self) -> Dict:
        """
        Track key engagement metrics
        """
        with self.get_session() as session:
            return {
                "daily_active_users": session.query(func.count(UserORM.id))
                .filter(UserORM.last_login > datetime.now(timezone.utc) - timedelta(days=1))
                .scalar(),
                "weekly_retention": self._calculate_retention(),
                "feature_usage": {
                    "searches": session.query(func.count(UserSearchActivityORM.id)).scalar(),
                    "applications": session.query(func.count(JobApplicationORM.id)).scalar()
                }
            }

    @error_handler
    def review_automated_decisions(self) -> List[JobApplication]:
        """
        Audit AI-driven decisions for compliance
        """
        with self.get_session() as session:
            return session.query(JobApplicationORM).filter(
                or_(
                    JobApplicationORM.ats_score < 50,
                    JobApplicationORM.status == 'REJECTED',
                    JobApplicationORM.review_summary.contains('AI Recommendation')
                )
            ).limit(100).all()

    @error_handler
    def monitor_service_level_agreements(self) -> Dict:
        """
        Track platform performance against SLAs
        """
        return {
            "uptime": self._get_uptime_metrics(),
            "response_times": {
                "api": self._get_api_response_times(),
                "support": self._get_support_response_times()
            },
            "incidents": self._get_recent_incidents()
        }

    @error_handler
    def generate_pay_equity_report(self, company_id: str) -> Dict:
        """
        Analyze salary distributions
        """
        with self.get_session() as session:
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

            return {
                "salary_distribution": [{
                    "gender": d[0],
                    "experience_level": d[1],
                    "avg_min_salary": d[2],
                    "avg_max_salary": d[3]
                } for d in salary_data]
            }

    # Helper methods
    def _calculate_risk_score(self, app_stats, search_stats):
        """Calculate composite risk score 0-100"""
        app_rate = app_stats[0] / ((app_stats[2] - app_stats[1]).total_seconds() / 3600 + 1) if app_stats[0] > 0 else 0
        search_intensity = search_stats[0] / (search_stats[1] or 1)
        return min(100, int(app_rate * 10 + search_intensity * 5))

    def _get_avg_response_time(self):
        """Placeholder for actual response time calculation"""
        return 0.25

    def _get_error_rate(self):
        """Placeholder for error rate calculation"""
        return 0.01

    from sqlalchemy import case, text

    def _calculate_retention(self):
        """Calculate weekly user retention rate using database timestamps"""
        with self.get_session() as session:
            # Single query to get both metrics using conditional aggregation
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

    def _get_user_documents(self, user_id):
        """Retrieve user documents from storage"""
        # Implementation would vary based on storage system
        return []


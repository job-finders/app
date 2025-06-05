import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from enum import Enum
from functools import partial
from typing import List, Dict, Optional

from flask import Flask, render_template, session
from pydantic import BaseModel, Field
from sqlalchemy import func, case, or_, text

from controllers.admin.user_security_engines import JobSeekerRuleEngine, EmployerRuleEngine
from database.models.admin_models import UserStatusFlagEnum, FlaggedUser, AdminModel, RiskRecommendation
from database.models.employer_models import Employer
from database.models.resume import JobSeekerCV
from database.models.users import RolesEnum
from database.sql.admin_sql import FlaggedUserORM, AdminRecommendationORM, AdminORM
from emailer import EmailModel
from src.controllers.controller import error_handler, Controllers
from src.database.constants import utc_time
from src.database.models.jobs_model import Job, Company, JobApprovalStatusEnum, JobStatusEnum
from src.database.models.jobseeker_profile import JobSeekerProfile
from src.database.sql.analytics import UserSearchActivityORM
from src.database.sql.company import CompanyORM
from src.database.sql.jobs_sql import JobsORM, JobApprovalRequestORM, JobVersionHistoryORM, JobApplicationORM, \
    JobCategoryORM
from src.database.sql.jobseeker_profile import JobSeekerProfileORM
from src.database.sql.users import UserORM
from src.utils.route_helpers import get_controller, get_service


class JobRecommenderResult(BaseModel):
    profile : JobSeekerProfile
    recommended_jobs: List[Job]

class AdminPermissionLevel(Enum):
    """
    Enum representing different levels of administrative access.

    These levels are used to control access to administrative features across the system,
    allowing fine-grained role-based permission enforcement.

    Members:
        VIEWER (str): Read-only access, typically used for monitoring or auditing.
        MODERATOR (str): Can perform moderation tasks such as reviewing flagged content.
        ADMIN (str): Has broader access, including managing users and content.
        SUPER_ADMIN (str): Full access, including system-level configurations and overrides.
    """
    VIEWER = "viewer"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class AdminActionResult(BaseModel):
    """
    Standardized structure for returning results from admin service actions.

    This object is returned by all admin services and encapsulates the outcome of
    an operation, including whether it succeeded, a user-readable message, and
    optionally any resulting data or error details.

    Attributes:
        success (bool): Indicates whether the operation was successful.
        message (str): A human-readable message describing the result.
        data (Optional[Dict]): Additional payload data from the action (e.g., a report or entity info).
        errors (Optional[List[str]]): A list of errors encountered during the operation, if any.
    """
    success: bool
    message: str
    data: Optional[Dict] = None
    list_data: Optional[list[JobRecommenderResult]] = Field(default_factory=list)
    errors: Optional[List[str]] = None


class AdminServiceInterface(ABC):
    """
    Abstract base class for defining administrative service interfaces.

    This interface enforces a common structure for all admin-related services,
    such as compliance checks, moderation workflows, and reporting utilities.

    Subclasses must implement the `execute()` method to define the service's
    core behavior, typically triggered via an admin command or UI action.

    Expected Usage:
        This interface should be inherited by concrete service classes like:
            - ComplianceService
            - JobModerationService
            - UserAuditTrailService
        These services should encapsulate admin operations that involve complex
        business logic, data aggregation, or multi-step workflows.

    Dependencies:
        - AdminActionResult: A standardized result wrapper used by all admin services
          to return success/failure status, messages, and optional payloads.

    Side Effects:
        - Implementation-dependent (e.g., may include DB writes, external API calls, or
          real-time notifications, depending on subclass implementation).

    Methods:
        execute(*args, **kwargs)
            Abstract method to be implemented by subclasses.

            Args:
                *args: Positional arguments specific to the implementing service.
                **kwargs: Keyword arguments required for execution logic.

            Returns:
                AdminActionResult: Structured result indicating the outcome of the operation.

            Raises:
                NotImplementedError: If called directly from the interface without subclass implementation.
    """

    @abstractmethod
    def execute(self, *args, **kwargs) -> AdminActionResult:
        """
        Execute the main logic of the admin service.

        :param args: Variable positional arguments specific to the implementing class.
        :param kwargs: Keyword arguments required for executing the admin operation.
        :return: AdminActionResult containing success status, message, and optional data.
        :rtype: AdminActionResult
        :raises NotImplementedError: If the method is not implemented by a subclass.
        """
        pass


class JobRecommendationService(AdminServiceInterface):
    """

    """
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.job_seekers_profile_controller = get_controller('job_seeker_profile')
        self.users_controller = get_controller('users')
        self.resume_controller = get_controller('resume')
        self.logger = get_service('logger')(self.__class__.__name__)


    def execute(self, action: str, **kwargs) -> AdminActionResult:
        """Execute job moderation action"""
        actions = {
            'recommend_jobs': self.all_jobseekers_recommendations_executor,
        }

        if action not in actions:
            return AdminActionResult(success=False, message=f"Unknown action: {action}")

        # noinspection PyTypeChecker
        return actions[action](**kwargs)



    @error_handler
    async def all_jobseekers_recommendations_executor(self) -> AdminActionResult:
        """
        :return:
        """
        job_seeker_profiles: list[JobSeekerProfile] = self.job_seekers_profile_controller.list_profiles_by_role(role=RolesEnum.JOBSEEKER.value)

        profiles_we_can_send_recommendations = [profile for profile in job_seeker_profiles if profile.can_send_job_recommendations]

        errors = []

        success : list[JobRecommenderResult] = []

        for i in range(0, len(profiles_we_can_send_recommendations), 50):
            batch = profiles_we_can_send_recommendations[i:i + 50]
            tasks = [self.get_personalized_job_recommendations(profile=profile) for profile in batch]
            batch_results: list[Exception | JobRecommenderResult] = await asyncio.gather(*tasks, return_exceptions=True)
            for res in batch_results:
                if isinstance(res, Exception):
                    errors.append(res)
                else:
                    success.append(res)


        for error in errors:
            self.logger.error(error)

        # returns a list of Profiles and Recommended Jobs so the Admin Controller can send the Emails.
        return AdminActionResult(success=len(success) > 1,message="Job Recommendations Processed", list_data=success)


    @error_handler
    async def get_personalized_job_recommendations(self, profile: JobSeekerProfile) -> JobRecommenderResult:
        """
            For each Profile this Method Returns Jobs Of Interest.
        :param profile:
        :return:
        """

        resume = await self.resume_controller.get_primary_resume(user_id=profile.user_uid)
        if not resume:
            return []

        with self.session_factory() as session:

            query = self._get_base_job_query(session=session)

            applied_job_ids = self._get_applied_job_ids(session=session, user_id=profile.user_uid)

            if applied_job_ids:
                query = query.filter(JobsORM.job_id.notin_(applied_job_ids))

            self._apply_user_preferences(query=query, profile=profile, resume=resume)

            similar_titles = self._get_similar_job_titles(session, applied_job_ids)
            if similar_titles:
                self._apply_similar_titles_filter(query, similar_titles)

            results = query.order_by(
                JobsORM.posted_at.desc(),
                JobsORM.is_featured.desc(),
                JobsORM.application_count.desc()
            ).limit(100).all()

            _result_dict = JobRecommenderResult(profile=profile, recommended_jobs=[Job(**job.to_dict()) for job in results])
            return _result_dict

    @error_handler
    def _get_base_job_query(self, session):
        return session.query(JobsORM).filter(
            JobsORM.status == JobStatusEnum.ACTIVE.value,
            JobsORM.expires_at > datetime.now(timezone.utc)
        )

    @error_handler
    def _get_applied_job_ids(self, session, user_id: str) -> list[str]:
        applied_jobs = session.query(JobApplicationORM).filter_by(user_id=user_id).all()
        return [job.job_id for job in applied_jobs if job]

    @error_handler
    def _get_similar_job_titles(self, session, applied_job_ids: list[str]) -> list[str]:
        if not applied_job_ids:
            return []

        applied_jobs = session.query(JobsORM).filter(JobsORM.job_id.in_(applied_job_ids)).all()
        titles = [job.title for job in applied_jobs if job.title]
        return list(set(titles))  # Deduplicate

    @error_handler
    def _apply_user_preferences(self, query, profile: JobSeekerProfile, resume: JobSeekerCV):
        """
            Apply User Preferences takes Profiles and Resumes Into Account in order to match Jobs.
        :param query:
        :param profile:
        :param resume:
        :return:
        """

        if profile.job_titles_of_interest:
            title_conds = [JobsORM.title.ilike(f"%{title}%") for title in profile.job_titles_of_interest]
            query = query.filter(or_(*title_conds))

        if profile.industries_of_interest:
            # Supports Partial Matches Between Industries and Categories
            filters = []
            for value in profile.industries_of_interest:
                filters.append(JobCategoryORM.name.ilike(f"%{value}%"))
                filters.append(JobCategoryORM.slug.ilike(f"%{value}%"))
            query = query.join(JobsORM.category).filter(or_(*filters))

        location_conds = []
        if profile.location:
            location_conds.extend([
                JobsORM.city.ilike(f"%{profile.location}%"),
                JobsORM.province.ilike(f"%{profile.location}%")
            ])
        for loc in profile.locations_of_interest or []:
            location_conds.extend([
                JobsORM.city.ilike(f"%{loc}%"),
                JobsORM.province.ilike(f"%{loc}%")
            ])
        # noinspection DuplicatedCode
        if location_conds:
            query = query.filter(or_(*location_conds))

        if profile.remote_preference:
            query = query.filter(JobsORM.remote_policy.in_(["REMOTE", "HYBRID"]))

        if resume.skills:
            skill_conds = [cond for skill in resume.skills for cond in [
                JobsORM.required_skills.contains([skill]),JobsORM.preferred_skills.contains([skill])]]

            query = query.filter(or_(*skill_conds))

        if profile.expected_salary:
            query = query.filter(
                JobsORM.salary_min >= profile.expected_salary * 0.7,
                JobsORM.salary_max <= profile.expected_salary * 1.3
            )

    @error_handler
    def _apply_similar_titles_filter(self, query, similar_titles: list[str]):
        if similar_titles:
            title_conds = [JobsORM.title.ilike(f"%{title}%") for title in similar_titles]
            query = query.filter(or_(*title_conds))


class JobModerationService(AdminServiceInterface):
    """
    Service class responsible for job moderation workflows within the admin interface.

    This service allows administrators to manage job postings through actions such as
    approving, rejecting, flagging, and bulk updating job statuses. It also provides
    mechanisms to detect suspicious or anomalous job listings based on company verification
    and known spam patterns.

    Dependencies:
        - session_factory (Callable): A function that returns a SQLAlchemy session context.
        - Models:
            - JobsORM
            - CompanyORM
            - JobApprovalRequestORM
        - Enums:
            - JobApprovalStatusEnum
        - Response Wrapper:
            - AdminActionResult

    Side Effects:
        - Writes to the database (status changes, audit trails).
        - May modify or create job approval request records.
        - No external API calls.

    Methods:
        __init__(session_factory)
            Initializes the service with a SQLAlchemy session factory.

        execute(action, **kwargs)
            Dispatches the moderation action based on the provided string key.

            Args:
                action (str): Action to perform. Must be one of:
                    - 'approve'
                    - 'reject'
                    - 'flag'
                    - 'bulk_update'
                    - 'detect_anomalies'
                **kwargs: Additional arguments required by the specific action.

            Returns:
                AdminActionResult: Encapsulated result of the operation.

        _approve_job(job_id, reviewer_id)
            Approves a job that has been flagged or is pending review.

            Args:
                job_id (str): ID of the job to approve.
                reviewer_id (str): Admin ID performing the approval.

            Returns:
                AdminActionResult: Result of the approval process.

        _reject_job(job_id, reviewer_id, reason)
            Rejects a job posting and provides a reason.

            Args:
                job_id (str): ID of the job to reject.
                reviewer_id (str): Admin ID performing the rejection.
                reason (str): Reason for rejecting the job.

            Returns:
                AdminActionResult: Result of the rejection process.

        _flag_job(job_id, reason, reporter_id)
            Flags a job for further review by administrators.

            Args:
                job_id (str): ID of the job to flag.
                reason (str): Justification for the flag.
                reporter_id (str): ID of the user/admin flagging the job.

            Returns:
                AdminActionResult: Result of the flagging operation.

        _bulk_update_status(job_ids, new_status)
            Updates the statuses of multiple jobs at once.

            Args:
                job_ids (List[str]): List of job IDs to update.
                new_status (str): New status to apply. Must be one of:
                    ['active', 'archived', 'pending_review']

            Returns:
                AdminActionResult: Summary of the bulk update operation.

        _detect_anomalous_postings()
            Identifies potentially suspicious job postings.

            Returns:
                AdminActionResult: A list of jobs flagged as anomalous based on spam keywords
                or company verification status.
    """

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
    """
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
    """
    Service for executing administrative analytics operations on the JobFinders platform.

    This service provides a unified interface for gathering system-level and user engagement metrics,
    retrieving audit logs, and producing reports to assist administrators in monitoring platform health
    and user behavior.

    Dependencies:
        - `session_factory`: A callable that returns a SQLAlchemy session.
        - Models:
            - `JobsORM`
            - `UserORM`
            - `UserSearchActivityORM`
            - `JobApplicationORM`
            - `JobVersionHistoryORM`
        - `AdminActionResult`: A standardized result object indicating success, message, and optional payload.

    Side Effects:
        - Read-only DB queries for all analytics.
        - No writes or session modifications.
        - No external API calls.

    Methods:
        __init__(session_factory)
            Initialize the service with a SQLAlchemy session factory.

        execute(metric_type: str, **kwargs) -> AdminActionResult
            Dispatches the analytics task based on the given metric type.

            Args:
                metric_type (str): One of ['system_health', 'engagement', 'audit_log', 'company_stats'].
                **kwargs: Additional keyword arguments passed to the corresponding method.

            Returns:
                AdminActionResult: Object containing success status, message, and optional data payload.

        _generate_system_health_report() -> AdminActionResult
            Collects platform-wide system health statistics including job count, user activity, and mock performance metrics.

            Returns:
                AdminActionResult: System health report with timestamp and summary statistics.

        _analyze_platform_engagement() -> AdminActionResult
            Measures engagement levels, including DAU (Daily Active Users), feature usage, and weekly retention.

            Returns:
                AdminActionResult: Engagement metrics with usage and retention insights.

        _get_job_audit_log(job_id: str) -> AdminActionResult
            Retrieves the version history and modification log of a specific job post.

            Args:
                job_id (str): Unique identifier for the job.

            Returns:
                AdminActionResult: Chronological audit history including timestamps, change sets, and modifying users.

        _calculate_retention(session) -> float
            Computes the weekly user retention rate.

            Args:
                session: Active SQLAlchemy session used to query user records.

            Returns:
                float: A decimal representing the weekly retention rate, or 0 if no data is available.
    """


    def __init__(self, session_factory):
        self.session_factory = session_factory

    def execute(self, metric_type: str, **kwargs) -> AdminActionResult:
        """Execute analytics operations"""
        metrics = {
            'system_health': self._generate_system_health_report,
            'engagement': self._analyze_platform_engagement,
            'audit_log': self._get_job_audit_log,
            'company_stats': self._company_statistics,

        }

        if metric_type not in metrics:
            return AdminActionResult(False, f"Unknown metric type: {metric_type}")

        # noinspection PyArgumentList
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

    @staticmethod
    def _calculate_retention(session):
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


class SecurityService(AdminServiceInterface):
    __doc__="""
    SecurityService is responsible for detecting, analyzing, and flagging suspicious or risky behavior
    by both jobseekers and employers on the platform. It provides analytics and heuristic evaluations
    to assist administrators in identifying abuse patterns such as spam applications, fraudulent job posts,
    and other forms of platform misuse.

    This service builds on AdminServiceInterface and leverages internal ORM models and analytics rules
    to return actionable admin results.

    Attributes:
        session_factory (Callable): A factory function that returns a SQLAlchemy session instance.
        db (DatabaseService): Inherited or injected dependency used for accessing user/employer/jobseeker records.
        logger (Logger): Inherited or injected logging utility for recording security events.

    Methods:
        execute(security_event: str, **kwargs) -> AdminActionResult:
            Dispatches execution to the appropriate security handler based on the event type.

        _analyze_jobseeker_risk(user_id: str) -> AdminActionResult:
            Analyzes application frequency and search patterns to assign a composite risk score to a jobseeker.

        _calculate_risk_score(app_stats, search_stats) -> int:
            Calculates a normalized risk score based on application rate and search activity intensity.

        _flag_unusual_employer_activity(employer: EmployerORM, company: CompanyORM) -> list[tuple[str, str]]:
            Applies predefined rules to detect suspicious behavior by employer accounts.

        _flag_unusual_jobseeker_activity(jobseeker: JobSeekerORM) -> list[tuple[str, str]]:
            Applies predefined rules to detect abusive or bot-like activity by jobseekers.

        _flag_unusual_user_activity() -> list[tuple[str, str]]:
            Iterates through all users and applies relevant heuristics to flag unusual behavior.
            Logs flagged cases for administrative review.

    Dependencies:
        - JobApplicationORM: ORM model for tracking job applications.
        - UserSearchActivityORM: ORM model for logging job search behavior.
        - JobSeekerORM, EmployerORM, CompanyORM: ORM models representing user roles and entities.
        - get_controller: Used to access other controllers like users, resumes, and job workflow logic.

    Side Effects:
        - Logs suspicious activity using `self.logger`.
        - Reads from the database to compute stats and evaluate conditions.
        - Returns structured results for admin panel consumption.

    Example:
        >>> service = SecurityService(session_factory)
        >>> result = service.execute("jobseeker_risk", user_id="abc123")
        >>> print(result.success, result.message, result.data)
    """



    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.company_controller = get_controller('company')
        self.users_controller = get_controller('users')
        self.jobseekers_controller = get_controller('job_seeker_profile')
        self.logger = get_service("logger")(self.__class__.__name__)

    async def execute(self, security_event: str, **kwargs) -> AdminActionResult:
        """Execute analytics operations"""
        security_events = {
            'flag_unusual_user_activity' : self._flag_unusual_user_activity,
            'apply_user_risk_recommendations': self._apply_user_risk_recommendations,
        }

        if security_event not in security_events:
            return AdminActionResult(success=False, message=f"Unknown security event type: {security_event}")
        # noinspection PyTypeChecker
        return await security_events[security_event](**kwargs)

    async def _apply_user_risk_recommendations(self, admin_uid: str) -> AdminActionResult:
        """
        Applies risk recommendations for all flagged users by storing them as recommended actions.

        This does not change user account status. Instead, it logs a recommendation that an admin can act on.
        Returns a list of (reference_id, recommended_action) tuples.

        # Several Algorithms will be affected by the recommendations stored here.
        """
        with self.session_factory() as session:
            admin_orm = session.query(AdminORM).first()
            admin_model: AdminModel = AdminModel(**admin_orm.to_dict(include_relationships=True)) if admin_orm else None

            actions_to_store = []
            for ref_id, recommendation in admin_model.user_risk_recommendations.items():
                action = AdminRecommendationORM(
                    reference_id=ref_id,
                    recommended_action=recommendation.value,
                    recommended_by=admin_uid,
                    recommended_at=utc_time(),
                    reason="Automated risk assessment based on flag history"
                )
                actions_to_store.append(action)
            # Storing User Recommendations.
            session.add_all(actions_to_store)
        _message = f"Successfully applied User Recommendations in Bulk {len(actions_to_store)} Where Affected by this action"
        return AdminActionResult(success=True, message=_message, data=admin_model.user_risk_recommendations)

    async def _flag_unusual_user_activity(self) -> AdminActionResult:
        flagged_users = []
        employer_user_accounts = await self.users_controller.get_users_by_role(role=RolesEnum.EMPLOYER.value)
        jobseekers_user_accounts = await self.users_controller.get_users_by_role(role=RolesEnum.JOBSEEKER.value)

        for user in employer_user_accounts:
            employer = await self.company_controller.get_employer_by_uid(user_id=user.uid)
            company = await  self.company_controller.get_company_by_employer_id(employer.employer_id) if employer else None

            if employer and company:
                flagged_users.extend(self._flag_unusual_employer_activity(employer, company))

        for user in jobseekers_user_accounts:
            jobseeker = self.jobseekers_controller.get_profile_by_uid(user_uid=user.uid)
            if jobseeker:
                flagged_users.extend(self._flag_unusual_jobseeker_activity(jobseeker))

        if flagged_users:
            for uid, reason in flagged_users:
                self.logger.warning(f"[Suspicious Activity] User {uid}: {reason}")
        else:
            self.logger.info("No unusual activity detected.")

        return AdminActionResult(success=True,message="succcessfully flagged users", list_data=flagged_users)


    def should_flag_user(
            session,
            reference_id: str,
            reason: str,
            cooldown_days: int = 7
    ) -> bool:
        """
        Checks whether a flag for the given user and reason has been raised
        within the cooldown period. Returns True if it's safe to flag again.

        Args:
            session: SQLAlchemy session
            reference_id: The ID of the user (employer or jobseeker)
            reason: The reason for flagging
            cooldown_days: Days to wait before re-flagging the same issue

        Returns:
            bool: True if the user should be flagged again
        """
        recent_flag = (
            session.query(FlaggedUserORM)
            .filter(
                FlaggedUserORM.reference_id == reference_id,
                FlaggedUserORM.reason == reason
            )
            .order_by(FlaggedUserORM.date_flagged_at.desc())
            .first()
        )

        if recent_flag:
            delta = datetime.utcnow() - recent_flag.date_flagged_at
            if delta.days < cooldown_days:
                return False  # Too soon to re-flag for the same reason
        return True

    @error_handler
    def _flag_unusual_employer_activity(self, employer: Employer, company: Company) -> list[tuple[str, str]]:
        with self.session_factory() as session:
            should_flag_user = partial(self.should_flag_user, session=session, reference_id=employer.employer_id)
            engine = EmployerRuleEngine(employer, company)
            return engine.evaluate(should_flag_user)

    @error_handler
    def _flag_unusual_jobseeker_activity(self, jobseeker: JobSeekerProfile) -> list[tuple[str, str]]:
        with self.session_factory() as session:
            should_flag_user = partial(self.should_flag_user, session=session, reference_id=jobseeker.uid)
            engine = JobSeekerRuleEngine(jobseeker)
            return engine.evaluate(should_flag_user)


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
        self.job_moderation_service = JobModerationService(self.get_session)
        self.compliance_service = ComplianceService(self.get_session)
        self.analytics_service = AnalyticsService(self.get_session)
        self.security_service = SecurityService(self.get_session)
        self.job_recommendation_service = JobRecommendationService(self.get_session)

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
                return AdminActionResult(success=True, message=f"Cleaned up {deleted} old approvals", data={"deleted_count": deleted})
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error cleaning up approvals: {str(e)}")

    @error_handler
    async def send_job_alerts_to_users(self, job_ids: List[str]) -> AdminActionResult:
        """Send job alerts to users based on their preferences"""
        profiles_job_alerts: list[JobRecommenderResult] = await self.job_recommendation_service.execute("recommend_jobs")
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
                'title': job.title,
                'company': job.company.name if job.company else "Confidential",
                'location': job.location,
                'type': job.position_type.replace('_', ' ').title(),
                'remote': job.remote_policy.title(),
                'salary': await self._format_salary(job),
                'description': job.description[:200] + '...' if job.description else "",
                'url': job.application_url,
                'deadline': job.application_deadline.strftime('%Y-%m-%d') if job.application_deadline else "ASAP"
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
    async def flag_unusual_user_activity(self, admin_uid: str) -> AdminActionResult:
        """Detect suspicious user behavior patterns"""
        action_result: AdminActionResult = await self.security_service.execute('flag_unusual_user_activity')
        flagged_users_models = []
        if action_result.success:
            for reference_id, message in action_result.list_data:
                flagged_users_models.append(FlaggedUserORM(**FlaggedUser(reference_id=reference_id, reason=message,flagged_by=admin_uid).model_dump()))

        with self.get_session() as session:
            session.add_all(flagged_users_models)

        return AdminActionResult(success=action_result.success, message=action_result.message, list_data=flagged_users_models)

    @error_handler
    async def evaluate_user_risks(self, admin_uid: str) -> AdminActionResult:
        """
        Run risk evaluations on flagged users and log admin recommendations.
        """
        try:
            recommendations = await self.security_service.execute('apply_user_risk_recommendations', admin_uid=admin_uid)

            return AdminActionResult(
                success=True,
                message="Risk recommendations generated.",
                list_data=recommendations)

        except Exception as e:
            return AdminActionResult(
                success=False,
                message=f"Failed to generate risk recommendations: {str(e)}")

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
        from utils.route_helpers import get_controller
        company_controller = get_controller('company')
        company = company_controller.get_company_by_id(company_id)
        export_data = {
            "company_data": company.to_dict(include_relationships=True),
            "exported_at": utc_time()
        }

        return AdminActionResult(True, "Company data exported successfully", export_data)

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
                    success=True,
                    message=f"Found {len(unverified_companies)} companies needing verification",data={"companies": companies_data})

        except Exception as e:
            return AdminActionResult(success=False,message=f"Error reviewing company verifications: {str(se)}")


    @error_handler
    async def get_admin_dashboard_data(self, user: "User"):
        """
        Gather and return comprehensive dashboard data for system admins.
        Uses detailed data from other controller methods/services.
        """
        try:
            # User stats
            user_stats_result = self.analytics_service.execute('system_health')
            user_stats = user_stats_result.data.get("user_stats", {}) if user_stats_result.success else {}

            # Resume stats
            ee_report_result = self.compliance_service.execute('employment_equity')
            resume_stats = {
                "total": ee_report_result.data.get("gender_distribution", {}).get("total", None),
                "completed": None  # Add more detailed resume stats if available from another service
            } if ee_report_result.success else {}

            # Job stats
            job_stats_result = self.analytics_service.execute('system_health')
            job_stats = job_stats_result.data.get("job_stats", {}) if job_stats_result.success else {}

            # Company stats
            company_stats = {
                "total": None,
                "verified": None
            }
            try:
                with self.get_session() as session:
                    company_stats["total"] = session.query(func.count(CompanyORM.id)).scalar()
                    company_stats["verified"] = session.query(func.count(CompanyORM.id)).filter_by(verified=True).scalar()
            except Exception:
                pass

            # Application stats
            application_stats = {
                "total": None
            }
            try:
                with self.get_session() as session:
                    application_stats["total"] = session.query(func.count(JobApplicationORM.application_id)).scalar()
            except Exception:
                pass

            # System health
            system_health = user_stats_result.data if user_stats_result.success else {}

            # Engagement
            engagement_result = self.analytics_service.execute('engagement')
            engagement = engagement_result.data if engagement_result.success else {}

            dashboard_data = {
                "user_stats": user_stats,
                "resume_stats": resume_stats,
                "job_stats": job_stats,
                "company_stats": company_stats,
                "application_stats": application_stats,
                "system_health": system_health,
                "engagement": engagement,
                "generated_at": datetime.utcnow().isoformat(),
            }
            return AdminActionResult(True, "Admin dashboard data loaded", dashboard_data)
        except Exception as e:
            return AdminActionResult(False, f"Error loading dashboard data: {str(e)}")


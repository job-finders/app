from datetime import datetime

from sqlalchemy import or_

from src.database.models.users import User
from src.database.models.jobs_model import JobApprovalStatusEnum
from src.database.sql.company import CompanyORM
from src.database.sql.jobs_sql import JobApprovalRequestORM, JobsORM
from src.controllers.admin.interfaces import AdminServiceInterface, AdminActionResult
from src.utils.route_helpers import get_controller


class JobModerationService(AdminServiceInterface):
    __doc__ = """
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

    def __init__(self, session_factory, system_admin):
        self.session_factory = session_factory
        self.jobs_workflow = get_controller('jobs_workflow')
        self.system_admin: User = system_admin

    def execute(self, action: str, **kwargs) -> AdminActionResult:
        """Execute job moderation action"""
        actions = {
            'approve': self._approve_jobs,
            'reject': self._reject_jobs,
            'flag': self._flag_job,
            'bulk_update': self._bulk_update_status,
            'detect_anomalies': self._detect_anomalous_postings
        }

        if action not in actions:
            return AdminActionResult(success=False, message=f"Unknown action: {action}")

        return actions[action](**kwargs)

    async def _reject_jobs(self):
        """
            This feature is not needed
        :return:
        """
        raise NotImplementedError("This action is not implemented yet.")

    async def _approve_jobs(self) -> AdminActionResult:
        """
        Automatically validates and approves job posts that meet quality standards.
        Limits the number of approvals in a single batch to avoid system overload.

        If an employer edits a job, they can seek approval again. This creates an
        Approval Request entry which is handled by another scheduled job.
        """
        approval_batch_max = 20  # Reasonable cap to avoid approving too many jobs at once

        try:
            jobs_needing_approval = await self.jobs_workflow.get_pending_approvals()

            if not jobs_needing_approval:
                return AdminActionResult(success=True, message="No jobs pending approval.")

            # Apply the limit
            jobs_to_process = jobs_needing_approval[:approval_batch_max]
            results = []

            for job in jobs_to_process:
                validation_result = await self.jobs_workflow.validate_job_post(job=job)

                if validation_result.get('valid', False):
                    approved_job = await self.jobs_workflow.activate_job_listing(
                        job_id=job.job_id, reviewer_id=self.system_admin.uid
                    )
                    results.append(approved_job)
                else:
                    rejected_job = await self.jobs_workflow.reject_job_listing(
                        job_id=job.job_id, reviewer=self.system_admin.uid
                    )
                    results.append(rejected_job)

            return AdminActionResult(
                success=True,
                message=f"Successfully evaluated {len(results)} job approval requests.",
                list_data=results
            )

        except Exception as e:
            return AdminActionResult(success=False, message=f"Error approving jobs: {str(e)}")

    def _flag_job(self, job_id: str, reason: str, reporter_id: str) -> AdminActionResult:
        """Flag a job for admin review"""
        try:
            with self.session_factory() as session:
                job = session.query(JobsORM).get(job_id)
                if not job:
                    return AdminActionResult(success=False, message="Job not found")

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
                return AdminActionResult(success=True, message="Job flagged successfully", data={"job_id": job_id})
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error flagging job: {str(e)}")

    def _bulk_update_status(self, job_ids: list[str], new_status: str) -> AdminActionResult:
        """Bulk update job statuses"""
        valid_statuses = ['active', 'archived', 'pending_review']
        if new_status not in valid_statuses:
            return AdminActionResult(success=False, message=f"Invalid status. Allowed: {valid_statuses}")

        try:
            with self.session_factory() as session:
                updated = session.query(JobsORM).filter(JobsORM.job_id.in_(job_ids)).update(
                    {JobsORM.status: new_status}
                )
                session.commit()
                return AdminActionResult(success=True, message=f"Updated {updated} jobs", data={"updated_count": updated})
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error updating jobs: {str(e)}")

    def _detect_anomalous_postings(self) -> AdminActionResult:
        """Detect suspicious job postings"""
        try:
            with self.session_factory() as session:
                anomalies = []

                # Unverified companies
                unverified = session.query(JobsORM).join(CompanyORM).filter(
                    CompanyORM.is_verified == False
                ).all()

                # Spam patterns
                spam_keywords = ["earn fast", "work from home", "no experience needed"]
                spam_jobs = session.query(JobsORM).filter(
                    or_(*[JobsORM.description.ilike(f"%{kw}%") for kw in spam_keywords])
                ).all()

                # Combine results
                all_anomalies = list({j.job_id: j for j in unverified + spam_jobs}.values())

                return AdminActionResult(
                    success=True,
                    message=f"Found {len(all_anomalies)} anomalous postings",
                    data={"anomalies": [{"job_id": j.job_id, "title": j.title} for j in all_anomalies]}
                )
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error detecting anomalies: {str(e)}")


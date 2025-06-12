from sqlalchemy import or_

from src.controllers.admin.interfaces import AdminServiceInterface, AdminActionResult
from src.database.models.users import User
from src.database.sql.company import CompanyORM
from src.database.sql.jobs_sql import JobsORM
from src.utils.route_helpers import get_controller, get_service


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
        self.logger = get_service("logger")()(self.__class__.__qualname__)

    def execute(self, action: str, **kwargs) -> AdminActionResult:
        """Execute job moderation action"""
        actions = {
            'approve': self._approve_jobs,
            'reject': self._reject_jobs,
            'flag': self._flag_jobs,
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
        approval_batch_max = 100  # Reasonable cap to avoid approving too many jobs at once

        try:
            jobs_needing_approval = await self.jobs_workflow.get_pending_approvals()

            if not jobs_needing_approval:
                self.logger.info("There are no Jobs in Need of Approval/ Validation")
                return AdminActionResult(success=True, message="No jobs pending approval.")

            # Apply the limit
            to = min(approval_batch_max, len(jobs_needing_approval))
            jobs_to_process = jobs_needing_approval[:to]
            results = []
            self.logger.info(f"We will start approving {len(jobs_to_process)} out of {len(jobs_needing_approval)} Jobs needing Approcal")
            for job in jobs_to_process:
                
                # This is where we actucally validate a job post
                validation_result = await self.jobs_workflow.validate_job_post(job=job)
                self.logger.init(f"Job Approval Result : {validation_result}")

                if validation_result.get('valid', False):
                    # If Job is validated then it is activated here - activated jobs will be listed on the portal
                    approved_job = await self.jobs_workflow.activate_job_listing(validation_result=validation_result,
                        job_id=job.job_id, reviewer_id=self.system_admin.uid)

                    results.append(approved_job)
                else:
                    rejected_job = await self.jobs_workflow.reject_job_listing(validation_result=validation_result,
                        job_id=job.job_id, reviewer=self.system_admin.uid)
                    results.append(rejected_job)

            return AdminActionResult(
                success=True,
                message=f"Successfully evaluated {len(results)} job approval requests.",
                list_data=results)

        except Exception as e:
            return AdminActionResult(success=False, message=f"Error approving jobs: {str(e)}")

    def _flag_jobs(self, job_id: str, reporter_id: str) -> AdminActionResult:
        """Flag a job for admin review based on multiple heuristics"""
        try:
            
            with self.session_factory() as session:
                job = session.query(JobsORM).filter_by(job_id=job_id).first()
                if not job:
                    return AdminActionResult(success=False, message="Job not found")

                company = session.query(CompanyORM).filter_by(company_id=job.company_id).first()
                spam_keywords = ["work from home", "quick money", "no experience needed", "earn fast"]
                suspicious = False
                reasons = []

                # Spam keyword detection
                if any(kw in (job.title or "").lower() or kw in (job.description or "").lower() for kw in spam_keywords):
                    suspicious = True
                    reasons.append("Contains spam keywords")

                # Unverified company
                if company and not company.is_verified:
                    suspicious = True
                    reasons.append("Unverified company")

                # Unrealistic salary (example: > 10x median, or < minimum wage)
                if hasattr(job, "salary") and (job.salary and (job.salary > 1_000_000 or job.salary < 1000)):
                    suspicious = True
                    reasons.append("Unrealistic salary")

                # Missing required fields
                if not job.description or not job.location:
                    suspicious = True
                    reasons.append("Missing required fields")

                # Duplicate postings (using workflow controller)
                if hasattr(self.jobs_workflow, "is_duplicate_posting"):
                    if self.jobs_workflow.is_duplicate_posting(job):
                        suspicious = True
                        reasons.append("Duplicate posting")

                # Too many external links
                if job.description and job.description.count("http") > 3:
                    suspicious = True
                    reasons.append("Too many external links")

                # Contact info in description
                import re
                if job.description and (re.search(r"\b\d{10,}\b", job.description) or re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", job.description)):
                    suspicious = True
                    reasons.append("Contact info in description")

                # New employer with many postings
                if company and hasattr(self.jobs_workflow, "count_company_jobs"):
                    if self.jobs_workflow.count_company_jobs(company.company_id) > 10 and not company.is_verified:
                        suspicious = True
                        reasons.append("New employer with many postings")

                if suspicious:
                    # Optionally, create a flag record or update job status
                    if hasattr(self.jobs_workflow, "flag_job_listing"):
                        self.jobs_workflow.flag_job_listing(job_id=job.job_id, reason="; ".join(reasons), reporter_id=reporter_id)
                    return AdminActionResult(
                        success=True,
                        message="Job flagged for review: " + "; ".join(reasons),
                        data={"job_id": job.job_id, "reasons": reasons}
                    )
                else:
                    return AdminActionResult(success=False, message="No suspicious patterns detected", data={"job_id": job_id})

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
        """Detect suspicious job postings
        
            The Admin calls this endpoint , then make decisions , The decision will be to either 
            activate or de-active the job
        """
        try:
            with self.session_factory() as session:
                anomalies = []

                # Unverified companies
                unverified = session.query(JobsORM).join(CompanyORM).filter(
                    CompanyORM.is_verified == False
                ).all()
                self.logger.info(f"Found {len(unverified)} Jobs from Unverified Companies")
                # Spam patterns

                #TODO- Use Config Table on the database to store anomalous job Titles.               
                spam_keywords = ["earn fast", "work from home", "no experience needed"]

                spam_jobs = session.query(JobsORM).filter(
                    or_(*[JobsORM.description.ilike(f"%{kw}%") for kw in spam_keywords])
                ).all()

                self.logger.info(f"Found {len(spam_jobs)} Spam Jobs")
                # Combine results
                all_anomalies = list({j.job_id: j for j in unverified + spam_jobs}.values())

                return AdminActionResult(
                    success=True,
                    message=f"Found {len(all_anomalies)} anomalous postings",
                    data={"anomalies": [{"job_id": j.job_id, "title": j.title} for j in all_anomalies]}
                )
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error detecting anomalies: {str(e)}")


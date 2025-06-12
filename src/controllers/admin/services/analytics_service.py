import inspect
from datetime import datetime, timezone, timedelta

from sqlalchemy import func, case, text

from src.controllers.admin.interfaces import AdminServiceInterface, AdminActionResult
from src.database.sql.analytics import UserSearchActivityORM
from src.database.sql.jobs_sql import JobsORM, JobVersionHistoryORM, JobApplicationORM
from src.database.sql.users import UserORM


class AnalyticsService(AdminServiceInterface):
    __doc__ = """
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
        self.__interface_map = {
            'system_health': self._generate_system_health_report,
            'engagement': self._analyze_platform_engagement,
            'audit_log': self._get_job_audit_log,
            'company_stats': self._company_statistics,
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
                # noinspection PyArgumentList
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

    def _company_statistics(self, company_id: str) -> AdminActionResult:
        """

        :return:
        """
        pass


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
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }

                return AdminActionResult(success=True, message="System health report generated",data=health_data)
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error generating system health report: {str(e)}")

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
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }

                return AdminActionResult(success=True, message="Platform engagement analysis completed",data=engagement_data)
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error analyzing platform engagement: {str(e)}")

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

                return AdminActionResult(success=True, message="Job audit log retrieved", data=audit_data)
        except Exception as e:
            return AdminActionResult(success=False, message=f"Error retrieving audit log: {str(e)}")

    @staticmethod
    def _calculate_retention(session):
        """Calculate weekly user retention rate"""
        try:
            retention_data = session.query(
                func.count().label('signups'),
                func.sum(
                    # what happens when func.now() does not return time in the required timezone ?
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

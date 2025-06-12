from datetime import datetime
from functools import partial

from src.controllers.admin.interfaces import AdminServiceInterface, AdminActionResult
from src.controllers.admin.security_rules import JobSeekerRuleEngine, EmployerRuleEngine
from src.controllers.controller import error_handler
from src.database.constants import utc_time
from src.database.models.admin_models import AdminModel
from src.database.models.employer_models import Employer
from src.database.models.jobs_model import Company
from src.database.models.jobseeker_profile import JobSeekerProfile
from src.database.models.users import RolesEnum
from src.database.sql.admin_sql import FlaggedUserORM, AdminRecommendationORM, AdminORM
from src.utils.route_helpers import get_controller, get_service


class SecurityService(AdminServiceInterface):
    __doc__ = """
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
        self.logger = get_service("logger")()(self.__class__.__name__)

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

    @staticmethod
    def should_flag_user(session, reference_id: str, reason: str, cooldown_days: int = 7) -> bool:
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
            delta = datetime.now(timezone.utc) - recent_flag.date_flagged_at
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

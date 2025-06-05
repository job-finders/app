from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Any, List

from src.database.models.jobseeker_profile import JobSeekerProfile


@dataclass
class SecurityRule:
    reason: str
    evaluator: Callable[[Any], bool]

class JobSeekerRuleEngine:
    def __init__(self, jobseeker: JobSeekerProfile):
        self.jobseeker = jobseeker
        self.rules: List[SecurityRule] = self._register_rules()

    def _register_rules(self) -> List[SecurityRule]:
        return [
            SecurityRule("Too many job applications in 24h", self._too_many_recent_apps),
            SecurityRule("Repeated applications to same job", self._repeated_job_apps),
            # More rules can be added here.
        ]

    def evaluate(self, should_flag_user: Callable[[str], bool]) -> List[tuple[str, str]]:
        flags = []
        for rule in self.rules:
            if rule.evaluator(self) and should_flag_user(reason=rule.reason):
                flags.append((self.jobseeker.uid, rule.reason))
        return flags

    def _too_many_recent_apps(self) -> bool:
        apps = self.jobseeker.applications or []
        recent_apps = [app for app in apps if (datetime.now(timezone.utc) - app.applied_at).days <= 1]
        return len(recent_apps) > 10

    def _repeated_job_apps(self) -> bool:
        job_app_map = {}
        for app in self.jobseeker.applications or []:
            job_app_map.setdefault(app.job_id, []).append(app)
        return any(len(apps) > 2 for apps in job_app_map.values())

from typing import Callable, List, Tuple
from dataclasses import dataclass


@dataclass
class SecurityRule:
    """
    Represents a security evaluation rule.

    Attributes:
        reason (str): A human-readable reason describing the rule.
        evaluator (Callable[[], bool]): A no-argument function that returns True if the rule is triggered.
    """
    reason: str
    evaluator: Callable[[], bool]


class EmployerRuleEngine:
    """
    Risk analysis engine for evaluating employer-related behaviors on the job platform.

    This class encapsulates a collection of pluggable rule evaluators that inspect
    an employer and their associated company for suspicious or policy-violating activity.

    Rules are evaluated based on their own logic and a separate flag duplication filter
    (via the `should_flag_user` callback) to prevent repeated flagging of the same condition.

    Attributes:
        employer (Employer): The employer object under evaluation.
        company (Company): The company associated with the employer.
        rules (List[SecurityRule]): The registered list of rules to be evaluated.

    Example Usage:
        engine = EmployerRuleEngine(employer, company)
        flags = engine.evaluate(should_flag_user)

    Adding New Rules:
        1. Define a new private method on this class that returns a boolean.
        2. Add a new `SecurityRule` in `_register_rules()` with:
            - A descriptive string reason
            - A reference to the method you just created
    """

    def __init__(self, employer, company):
        """
        Initialize the rule engine with the employer and their associated company.

        Args:
            employer (Employer): The employer being analyzed.
            company (Company): The company entity tied to the employer.
        """
        self.employer = employer
        self.company = company
        self.rules: List[SecurityRule] = self._register_rules()

    def _register_rules(self) -> List[SecurityRule]:
        """
        Register all security rules for evaluating the employer.

        Returns:
            List[SecurityRule]: A list of rule objects with corresponding evaluators.
        """
        return [
            SecurityRule("Unverified company posting jobs", self._unverified_company_posting_jobs),
            SecurityRule("High job volume from new account", self._high_volume_on_new_account),
            SecurityRule("Low application response rate", self._low_response_rate),
            SecurityRule("Suspiciously short hiring times", self._fast_hiring_times),
            SecurityRule("Saving candidates without job posts", self._saving_candidates_without_jobs),
        ]

    def evaluate(self, should_flag_user: Callable[[str], bool]) -> List[Tuple[str, str]]:
        """
        Run all registered rules and return triggered flags.

        Each rule is checked using its evaluator method. If the result is True and
        `should_flag_user(reason)` also returns True (e.g., not flagged before), then
        a (user_id, reason) tuple is returned.

        Args:
            should_flag_user (Callable[[str], bool]): A callback to check for duplicate flags.

        Returns:
            List[Tuple[str, str]]: A list of (employer_id, reason) for triggered flags.
        """
        flags = []
        for rule in self.rules:
            if rule.evaluator() and should_flag_user(reason=rule.reason):
                flags.append((self.employer.employer_id, rule.reason))
        return flags

    # --- Individual Rule Evaluators ---

    def _unverified_company_posting_jobs(self) -> bool:
        """
        Detects if an unverified company is actively posting jobs.

        Returns:
            bool: True if condition is met.
        """
        return not self.company.is_verified and self.company.total_jobs > 0

    def _high_volume_on_new_account(self) -> bool:
        """
        Detects if a new employer account has an unusually high number of job postings.

        Returns:
            bool: True if employer account age is <= 2 days and 5+ jobs are posted.
        """
        return self.employer.account_age <= 2 and self.company.total_jobs >= 5

    def _low_response_rate(self) -> bool:
        """
        Flags companies that receive applications but fail to respond.

        Returns:
            bool: True if 10+ applications exist and the response rate is < 1%.
        """
        return self.company.total_applications >= 10 and self.company.application_response_rate < 1

    def _fast_hiring_times(self) -> bool:
        """
        Detects employers that close hiring cycles suspiciously fast.

        Returns:
            bool: True if hiring time is under 1 day across at least 3 job posts.
        """
        return self.company.avg_hiring_time < 1 and self.company.total_jobs >= 3

    def _saving_candidates_without_jobs(self) -> bool:
        """
        Flags employers who are saving candidate profiles without ever posting jobs.

        Returns:
            bool: True if total_jobs == 0 and 5+ candidates saved.
        """
        return self.company.total_jobs == 0 and self.company.total_saved_candidates > 5

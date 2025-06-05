from typing import Callable, List, Tuple
import yaml
from src.controllers.admin.security_rules.security_rules_registry import EMPLOYER_RULE_REGISTRY, JOBSEEKER_RULE_REGISTRY


class SecurityRule:
    def __init__(self, reason: str, evaluator: Callable[[], bool]):
        self.reason = reason
        self.evaluator = evaluator


class EmployerRuleEngine:
    def __init__(self, employer, company, config_path="rules.yaml"):
        self.employer = employer
        self.company = company
        self.context = self
        self.rules = self._load_rules(config_path)

    def _load_rules(self, config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return [
            SecurityRule(rule["reason"], lambda r=rule["reason"]: EMPLOYER_RULE_REGISTRY[r](self.context))
            for rule in config.get("employer_rules", [])
            if rule.get("enabled", False)
        ]

    def evaluate(self, should_flag_user: Callable[[str], bool]) -> List[Tuple[str, str]]:
        return [
            (self.employer.employer_id, rule.reason)
            for rule in self.rules
            if rule.evaluator() and should_flag_user(rule.reason)
        ]


class JobseekerRuleEngine:
    def __init__(self, jobseeker, security_service, config_path="rules.yaml"):
        self.jobseeker = jobseeker
        self.security_service = security_service
        self.context = self
        self.rules = self._load_rules(config_path)

    def group_applications_by_job(self):
        apps = self.jobseeker.applications or []
        job_map = {}
        for app in apps:
            job_map.setdefault(app.job_id, []).append(app)
        return job_map

    def _load_rules(self, config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return [
            SecurityRule(rule["reason"], lambda r=rule["reason"]: JOBSEEKER_RULE_REGISTRY[r](self.context))
            for rule in config.get("jobseeker_rules", [])
            if rule.get("enabled", False)
        ]

    def evaluate(self, should_flag_user: Callable[[str], bool]) -> List[Tuple[str, str]]:
        return [
            (self.jobseeker.uid, rule.reason)
            for rule in self.rules
            if rule.evaluator() and should_flag_user(rule.reason)
        ]


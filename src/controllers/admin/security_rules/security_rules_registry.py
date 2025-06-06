# Common wrapper for both employer and jobseeker contexts
from datetime import datetime

EMPLOYER_RULE_REGISTRY = {
    "Unverified company posting jobs": lambda ctx: not ctx.company.is_verified and ctx.company.total_jobs > 0,
    "High job volume from new account": lambda ctx: ctx.employer.account_age <= 2 and ctx.company.total_jobs >= 5,
    "Low application response rate": lambda ctx: ctx.company.total_applications >= 10 and ctx.company.application_response_rate < 1,
    "Suspiciously short hiring times": lambda ctx: ctx.company.avg_hiring_time < 1 and ctx.company.total_jobs >= 3,
    "Saving candidates without job posts": lambda ctx: ctx.company.total_jobs == 0 and ctx.company.total_saved_candidates > 5,
    "Copy-paste job ads": lambda ctx: ctx.company.has_duplicate_job_descriptions,  # assume method exists
    "Inconsistent location data": lambda ctx: ctx.employer.ip_address !=  ctx.company.ip_address,
    "Rapid edits to job posts": lambda ctx: ctx.company.has_multiple_edits_in_last_hour,  # assumes helper
}

JOBSEEKER_RULE_REGISTRY = {
    "Too many job applications in 24h": lambda ctx: len([app for app in ctx.jobseeker.applications if (datetime.utcnow() - app.applied_at).days <= 1]) > 10,
    "Repeated applications to same job": lambda ctx: any(len(apps) > 2 for apps in ctx.group_applications_by_job().values()),
    "Multiple accounts from same IP": lambda ctx: ctx.jobseeker.detect_multiple_accounts,
    "Unrealistic application timing": lambda ctx: ctx.jobseeker.detect_burst_applications,
    "Suspicious resume content": lambda ctx: ctx.resume.resume_has_boilerplate,
}


from collections import Counter

from src.controllers.controller import error_handler
from src.database.models.jobs_model import JobApplicationStatusEnum
from src.database.models import Job
from src.database.models.resume import JobSeekerCV
from src.agents.employer.ats_suggestion_agent import KeywordTool, KeywordSourceType, ATSOptimisationInput
from src.utils import tokenize
from src.utils.route_helpers import get_controller


class IndustryTaxonomyTool(KeywordTool):
    source_type = KeywordSourceType.INDUSTRY_TAXONOMY

    @error_handler
    async def fetch(self, job: ATSOptimisationInput) -> list[tuple[str, int]]:
        # TODO please add industrial taxonomy controller to the factory
        ctl = get_controller("industry_taxonomy")
        return await ctl.fetch_keywords(
            title=job.title,
            description=job.description,
            skills=job.required_skills + job.preferred_skills,
        )

class PeerJobsTool(KeywordTool):
    """
    AI-readable TASK list (only `jobs_workflow` controller):

    1. Acquire controller
        j_ctl = get_controller("jobs_workflow")

    2. Fetch similar jobs
        similar_jobs: list[Job] = await j_ctl.get_similar_jobs(job.id)

    3. Compute success metrics via controller helpers
        – applications_count  = job.total_applications
        – hired_count         = await j_ctl.count_applications_by_stage(job.job_id, "hired")
        – average_ats_score   = job.job_ats_score or 0

    4. Keep only jobs where
        (hired_count ≥ 1 OR applications_count ≥ 30)
        AND average_ats_score ≥ 70

    5. Tokenize & aggregate keywords
        Use job.ats_description for rich, pre-formatted text.

    6. Return list[tuple[str, int]] sorted by descending frequency.
    """
    source_type = KeywordSourceType.PEER_JOBS

    @error_handler
    async def fetch(self, job: ATSOptimisationInput) -> list[tuple[str, int]]:
        job_search_ctl = get_controller("jobs_search")
        job_workflow_ctl = get_controller("jobs_workflow")
        similar_jobs: list[Job] = await job_search_ctl.get_similar_jobs(job_id=job.job_id, limit=20)

        successful_jobs = []

        for j in similar_jobs:
            success_count = await job_workflow_ctl.count_applications_by_stage(
                job_id=j.job_id, success_stages=JobApplicationStatusEnum.success_stages())

            apps_count  = j.total_applications
            avg_score   = j.job_ats_score or 0

            if (success_count >= 1 or apps_count >= 30) and avg_score >= 70:
                successful_jobs.append(j)

        counter = Counter()
        for j in successful_jobs:
            counter.update(tokenize(j.ats_description))

        return counter.most_common()


class ParsedCVsTool(KeywordTool):
    """
    Refined algorithm leveraging the full JobSeekerCV context.

    1.  Acquire controllers
        resume_controller  = get_controller("resume")
        job_controller     = get_controller("jobs_workflow")

    2.  Obtain similar jobs that have applications
        similar_jobs = await job_controller.get_similar_jobs(job.id)
        relevant_jobs = [j for j in similar_jobs if getattr(j, "applications_count", 0) > 0]

    3.  For each job, fetch the most-successful resumes
        – outcome in ["interviewed", "hired"]
        – min_ats_score ≥ 70
        – trust_score ≥ 60   (optional quality gate)

    4.  Aggregate weighted keywords from the **entire resume context**:
        – skills (highest weight)
        – professional_title
        – summary
        – experience
        – projects
        – certifications
        – languages

    5.  Return keywords sorted by (tf-idf * trust_score) descending.
    """
    source_type = KeywordSourceType.PARSED_CVS

    @error_handler
    async def fetch(self, job: ATSOptimisationInput) -> list[tuple[str, int]]:
        resume_controller = get_controller("resume")
        job_controller = get_controller("jobs_search")

        # 2 ─ similar jobs with applications
        similar_jobs = await job_controller.get_similar_jobs(job_id=job.job_id, limit=20)
        relevant_jobs = [j for j in similar_jobs if getattr(j, "applications_count", 0) > 0]

        # 3 ─ collect successful resumes
        resumes: list[JobSeekerCV] = []
        for j in relevant_jobs:
            batch = await resume_controller.get_successful_resumes_by_job(
                job_id=j.job_id,
                outcome=["interviewed", "hired"],
                min_ats_score=70,
                limit=20
            )
            resumes.extend(r for r in batch if r.trust_score >= 60)

        if not resumes:
            return []

        # 4 ─ weighted keyword extraction
        counter = Counter()
        for r in resumes:
            weight = max(1, r.trust_score // 10)  # 6–10 multiplier

            # High-value fields
            counter.update({k: weight * 3 for k in tokenize(" ".join(r.skills))})
            counter.update({k: weight * 2 for k in tokenize(r.professional_title)})
            counter.update({k: weight * 2 for k in tokenize(r.summary or "")})

            # Medium-value fields
            for exp in r.experience:
                counter.update({k: weight for k in tokenize(exp.description or "")})
            for proj in r.projects or []:
                counter.update({k: weight for k in tokenize(proj.description or "")})
                counter.update({k: weight for k in tokenize(" ".join(proj.technologies or []))})

            for cert in r.certifications or []:
                counter.update({k: weight for k in tokenize(cert.name)})
            for lang in r.languages or []:
                counter.update({k: weight for k in tokenize(lang.name)})

        # 5 ─ return top keywords
        return counter.most_common()


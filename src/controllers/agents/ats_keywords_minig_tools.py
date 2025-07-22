
from collections import Counter

from src.controllers.controller import error_handler

from src.database.models import (Job, JobApplicationStatusEnum, JobSeekerCV, KeywordTool,
                                 KeywordSourceType, ATSOptimisationInput)
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
        (hired_count ≥ min_success OR applications_count ≥ min_applications)
        AND average_ats_score ≥ min_ats_score

    5. Tokenize & aggregate keywords
        Use job.ats_description for rich, pre-formatted text.

    6. Return list[tuple[str, int]] sorted by descending frequency.
    """

    source_type = KeywordSourceType.PEER_JOBS

    def __init__(
        self,
        *,
        min_success: int = 1,
        min_applications: int = 15,
        min_ats_score: int = 70,
        similar_jobs_limit: int = 20,
    ) -> None:
        self.min_success = min_success
        self.min_applications = min_applications
        self.min_ats_score = min_ats_score
        self.similar_jobs_limit = similar_jobs_limit

    @error_handler
    async def fetch(self, job: ATSOptimisationInput) -> list[tuple[str, int]]:
        job_search_ctl = get_controller("jobs_search")
        job_workflow_ctl = get_controller("jobs_workflow")

        similar_jobs: list[Job] = await job_search_ctl.get_similar_jobs(
            job_id=job.job_id,
            limit=self.similar_jobs_limit,
        )

        successful_jobs = [
            j
            for j in similar_jobs
            if (
                await job_workflow_ctl.count_applications_by_stage(
                    job_id=j.job_id,
                    success_stages=JobApplicationStatusEnum.success_stages(),
                )
                >= self.min_success
                or j.total_applications >= self.min_applications
            )
            and (j.job_ats_score or 0) >= self.min_ats_score
        ]

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
        – outcome in success_outcomes
        – min_ats_score ≥ min_resume_ats_score
        – trust_score ≥ min_trust_score   (optional quality gate)

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

    def __init__(
        self,
        *,
        success_outcomes: list[str] | None = None,
        min_resume_ats_score: int = 70,
        min_trust_score: int = 60,
        similar_jobs_limit: int = 20,
        resumes_per_job_limit: int = 20,
        weight_skills: int = 3,
        weight_title: int = 2,
        weight_summary: int = 2,
        weight_other: int = 1,
    ) -> None:
        self.success_outcomes = success_outcomes or ["interviewed", "hired"]
        self.min_resume_ats_score = min_resume_ats_score
        self.min_trust_score = min_trust_score
        self.similar_jobs_limit = similar_jobs_limit
        self.resumes_per_job_limit = resumes_per_job_limit
        self.weight_skills = weight_skills
        self.weight_title = weight_title
        self.weight_summary = weight_summary
        self.weight_other = weight_other

    @error_handler
    async def fetch(self, job: ATSOptimisationInput) -> list[tuple[str, int]]:
        resume_controller = get_controller("resume")
        job_controller = get_controller("jobs_search")

        # 2 ─ similar jobs with applications
        similar_jobs = await job_controller.get_similar_jobs(
            job_id=job.job_id,
            limit=self.similar_jobs_limit,
        )
        relevant_jobs = [
            j for j in similar_jobs
            if getattr(j, "applications_count", 0) > 0
        ]

        # 3 ─ collect successful resumes
        resumes: list[JobSeekerCV] = []
        for j in relevant_jobs:
            batch = await resume_controller.get_successful_resumes_by_job(
                job_id=j.job_id,
                outcome=self.success_outcomes,
                min_ats_score=self.min_resume_ats_score,
                limit=self.resumes_per_job_limit,
            )
            resumes.extend(r for r in batch if r.trust_score >= self.min_trust_score)

        if not resumes:
            return []

        # 4 ─ weighted keyword extraction
        counter = Counter()
        for r in resumes:
            multiplier = max(1, r.trust_score // 10)

            counter.update({
                k: multiplier * self.weight_skills
                for k in tokenize(" ".join(r.skills))
            })
            counter.update({
                k: multiplier * self.weight_title
                for k in tokenize(r.professional_title)
            })
            counter.update({
                k: multiplier * self.weight_summary
                for k in tokenize(r.summary or "")
            })

            for exp in r.experience:
                counter.update({
                    k: multiplier * self.weight_other
                    for k in tokenize(exp.description or "")
                })

            for proj in r.projects or []:
                counter.update({
                    k: multiplier * self.weight_other
                    for k in tokenize(proj.description or "")
                })
                counter.update({
                    k: multiplier * self.weight_other
                    for k in tokenize(" ".join(proj.technologies or []))
                })

            for cert in r.certifications or []:
                counter.update({
                    k: multiplier * self.weight_other
                    for k in tokenize(cert.name)
                })

            for lang in r.languages or []:
                counter.update({
                    k: multiplier * self.weight_other
                    for k in tokenize(lang.name)
                })

        # 5 ─ return top keywords
        return counter.most_common()
        
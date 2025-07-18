
import re
from collections import Counter
from src.utils import tokenizer
from src.utils.route_tools import get_controller


class IndustryTaxonomyTool(KeywordTool):
    """sumary_line
        should use get_controller to get the controller for this tool then use the controller to get
        keywords from the industry taxonomy service. 
        this could be a service that provides keywords for different industries and roles.
        the keywords should be relevant to the job being optimised.
    """

    source_type = KeywordSourceType.INDUSTRY_TAXONOMY

    def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        # TODO: query your taxonomy service here
        return [("python", 42), ("django", 18)]


class PeerJobsTool(KeywordTool):
    """
    High-level TASK list (AI-readable):

    1.  Acquire controller
        controller = get_controller("jobs_workflow")

    2.  Fetch similar jobs
        similar_jobs = await controller.get_similar_jobs(job.id)

    3.  Filter for success
        Keep only jobs where
            status == "filled" OR applications_count >= 30
            AND average_ats_score >= 70   (from job model)

    4.  Tokenize & aggregate
        For every retained job → tokenize(title + description)
        Flatten into a single Counter.

    5.  Return top keywords
        Return list[tuple[str, int]] sorted by descending frequency.
    """
    source_type = KeywordSourceType.PEER_JOBS

    async def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        # --- 1 & 2 ---
        controller = get_controller("jobs_workflow")
        # Fetch similar jobs using the controller - ensure this is an async call and its implemented as needed here
        similar_jobs = await controller.get_similar_jobs(job.id)

        # --- 3 --- filter is based on hired and applications count and also ats score
        successful_jobs = [
            j for j in similar_jobs
            if (j.status == "filled" or j.applications_count >= 30)
            and j.average_ats_score >= 70
        ]

        # --- 4 --- tokenize and aggregate keywords
        counter = Counter()
        for j in successful_jobs:
            text = f"{j.title} {j.description or ''}"
            counter.update(tokenize(text))

        # --- 5 --- return top keywords
        # Return the most common keywords as a list of tuples (keyword, frequency)
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

    async def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        resume_controller = get_controller("resume")
        job_controller    = get_controller("jobs_workflow")

        # 2 ─ similar jobs with applications
        similar_jobs = await job_controller.get_similar_jobs(job.id)
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


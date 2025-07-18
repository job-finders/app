
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
    """sumary_line
        could use get_controller to get the controller for this tool then use the controller to get 
        resumes that applied for similar roles successfully and extract keywords from them.

        success can be determined by the number of successful applications or the number of interviews scheduled.

        success can also be detarmined by the ats score for the resume for jobs similar to the job being optimised.

    Keyword arguments:
    argument -- description
    Return: return_description
    """
    
    source_type = KeywordSourceType.PARSED_CVS

    def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        # TODO: aggregate keywords from CVs of similar roles
        return [("fastapi", 20), ("asyncio", 12)]

        
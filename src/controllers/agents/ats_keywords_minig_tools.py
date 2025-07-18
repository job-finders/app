
import re
from collections import Counter
from src.utils import tokenizer



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
    """sumary_line
        should use get_controller to get the controller for this tool then use the controller to get
        historical jobs that are similar to the job being optimised and extract keywords from them.
        for similar jobs find the ones that have been successful in the past, i.e. those that have been filled or have received a high number of applications.
        and also find the jobs that have a higher average ats score. for resumes. (the average ats score can be found from the applications the job received its already calculated in the job model).

    Keyword arguments:
    argument -- description
    Return: return_description
    """
    
    source_type = KeywordSourceType.PEER_JOBS

    def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        # TODO: run a similarity search against historical jobs
        return [("rest api", 30), ("postgresql", 25)]


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

        
# src/controllers/agents.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from src.database.constants import utc_time
from src.routes.utils import to_aware

from src.agents.ats_optimization_agent import ATSOptimiseAgent,ATSOptimisationInput, ATSOptimisationOutput
from src.controllers.controller import Controllers, error_handler
from src.utils.route_helpers import get_service


class EmployerATSOptimizationController(Controllers):
    """sumary_line
    
    Keyword arguments:
    argument -- description
    Return: return_description
    """
    def __init__(self, factory):
        super().__init__(factory)
    
    def init_app(self, app):
        super().init_app(app)
        # App-specific initialization
        # self.cache.init_app(app)

    @error_handler
    async def suggest_industry_keywords(self, job: Job) -> ATSOptimisationOutput:
        """Given a Job Model, return ats keyword suggestions based on the job description and title. 
        and industry standard job categories.
        """

        agent = ATSOptimiseAgent()
        payload = ATSOptimisationInput(
            job_id=job.job_id,
            title=job.title,
            description=job.description,
            required_skills=job.required_skills or [],
            preferred_skills=job.preferred_skills or [],
            city=job.city,
            province=job.province,
            country=job.country,
        )
        result: ATSOptimisationOutput = await agent.run(payload)
        suggestions = result.suggestions

    
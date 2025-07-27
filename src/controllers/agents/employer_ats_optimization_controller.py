# src/controllers/agents.py
from collections import defaultdict

from src.agents.base import TaskType, UserRole
from src.controllers.agents.ats_keywords_minig_tools import IndustryTaxonomyTool, PeerJobsTool, ParsedCVsTool
from src.controllers.controller import Controllers, error_handler

from src.database.models import KeywordSourceType  # Make sure this import is in your file


from src.database.models import (Job, AIATSReport, KeywordSource, ATSScoreBreakdown, AIEnhancementSuggestion,
                                 SuggestionImpact, ATSOptimisationOutput, ATSOptimisationInput)

from src.agents.employer.ats_suggestion_agent import ATSKeywordSuggestionAgent


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
        """
            Given a Job Model, return ats keyword suggestions based on the job description and title. 
            and industry standard job categories.

        """
        system_admin = await self.get_system_admin()
        tools_list = [
                IndustryTaxonomyTool(),
                PeerJobsTool(),
                ParsedCVsTool(),
        ]
        self.logger.info("WE GOT HERE")
        agent = ATSKeywordSuggestionAgent(user_id=system_admin.uid, tools=tools_list, fallback_threshold=5)
        self.logger.info("after ATSKeyword Suggestion Initialization")
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
        # TODO - keyword mining tools should be used to generate keywords then passed to the agent
        # noinspection PyTypeChecker
        result: ATSOptimisationOutput = await agent.run(input_model=payload, user_role=UserRole.EMPLOYER,
                                                        task_type=TaskType.OPTIMIZE.value)
        return result

    @error_handler
    async def compile_ats_report(self, job: Job) -> AIATSReport | None:

        self.logger.info("Will now compile industry keywords")
        raw = await self.suggest_industry_keywords(job)
        if raw is None:
            return None

        job_text = " ".join([
            job.title or "",
            job.description or "",
            " ".join(job.required_skills or []),
            " ".join(job.preferred_skills or []),
        ]).lower()

        matched_keywords_set = set()
        missing_keywords_set = set()

        for suggestion in raw.suggestions:
            for keyword in suggestion.keywords_added:
                if keyword.lower() in job_text:
                    matched_keywords_set.add(keyword)
                else:
                    missing_keywords_set.add(keyword)

        default_source_type = KeywordSourceType.INDUSTRY_TAXONOMY  # fallback source

        matched = [
            KeywordSource(
                keyword=k,
                frequency=0,
                source_type=default_source_type,
                weight=1.0,
            )
            for k in matched_keywords_set
        ]

        missing = [
            KeywordSource(
                keyword=k,
                frequency=0,
                source_type=default_source_type,
                weight=1.0,
            )
            for k in missing_keywords_set
        ]

        field_to_score = defaultdict(float)
        for s in raw.suggestions:
            field_to_score[s.field] += s.impact.estimated_score_increase

        score_breakdown = ATSScoreBreakdown(
            title_score=field_to_score.get("title", 0),
            skills_score=field_to_score.get("required_skills", 0) + field_to_score.get("preferred_skills", 0),
            description_score=field_to_score.get("description", 0),
            formatting_score=field_to_score.get("formatting", 0),
            experience_level_score=field_to_score.get("experience_level", 0),
        )

        suggestions = raw.suggestions

        return AIATSReport(
            job_id=str(job.job_id),
            score_breakdown=score_breakdown,
            matched_keywords=matched,
            missing_keywords=missing,
            suggestions=suggestions,
            keyword_corpora=["industry_taxonomy", "peer_jobs", "parsed_cvs"],
        )

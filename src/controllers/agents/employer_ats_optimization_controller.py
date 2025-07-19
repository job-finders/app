# src/controllers/agents.py
from src.controllers.agents.ats_keywords_minig_tools import IndustryTaxonomyTool, PeerJobsTool, ParsedCVsTool
from src.controllers.controller import Controllers, error_handler

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
        result: ATSOptimisationOutput = await agent.run(input_model=payload)
        return result

    @error_handler
    async def compile_ats_report(self, job: Job) -> AIATSReport:
        self.logger.info(f"will now compile industry keywords")
        raw = await self.suggest_industry_keywords(job)
        matched = [
            KeywordSource(keyword=k.keyword, frequency=k.frequency,
                          source_type=k.source_type.value, weight=k.weight)
            for k in raw.matched_keywords
        ]
        missing = [
            KeywordSource(keyword=k.keyword, frequency=k.frequency,
                          source_type=k.source_type.value, weight=k.weight)
            for k in raw.missing_keywords
        ]

        score_breakdown = ATSScoreBreakdown(
            title_score=getattr(raw.score_breakdown, "title_score", 0),
            skills_score=getattr(raw.score_breakdown, "skills_score", 0),
            description_score=getattr(raw.score_breakdown, "description_score", 0),
            formatting_score=getattr(raw.score_breakdown, "formatting_score", 0),
            experience_level_score=getattr(raw.score_breakdown, "experience_level_score", 0),
        )

        suggestions = [
            AIEnhancementSuggestion(
                field=s.field,
                action=s.action,
                current=s.current,
                recommended=s.recommended,
                keywords_added=s.keywords_added,
                impact=SuggestionImpact(
                    estimated_score_increase=s.impact.estimated_score_increase,
                    confidence=s.impact.confidence,
                    reasoning=s.impact.reasoning,
                ),
            )
            for s in raw.suggestions
        ]

        return AIATSReport(
            job_id=str(job.job_id),
            score_breakdown=score_breakdown,
            matched_keywords=matched,
            missing_keywords=missing,
            suggestions=suggestions,
            keyword_corpora=["industry_taxonomy", "peer_jobs", "parsed_cvs"],
        )

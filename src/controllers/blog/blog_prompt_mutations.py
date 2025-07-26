from src.database import BlogPromptORM, PromptMutationLogORM, ArticleORM, PerformanceORM
from src.agents.blog.prompts import PromptMutatorAgent
from src.controllers.controller import Controllers
from src.utils.route_helpers import get_service


class PromptMutationController(Controllers):
    def __init__(self, factory):
        super().__init__(factory=factory)
        self.factory = factory
        self.mutator = PromptMutatorAgent(user_id="system")
        self.logger  = get_service("logger")()(self.__class__.__name__)

    def init_app(self, app):
        super().init_app(app)
        if self.logger:
            self.logger.info("PromptMutationController initialized")

    # ---------- daily cron ----------
    async def daily_mutate_prompts(self) -> dict:
        """
        1. Collect PerformanceORM rows
        2. Feed them to PromptMutatorAgent
        3. Save new prompt + mutation log
        """
        summary = {"mutated": 0}
        with self.get_session() as session:
            for agent_name in [
                "TopicDiscoveryAgent",
                "ArticlePlannerAgent",
                "ContentGeneratorAgent",
            ]:
                latest = (
                    session.query(BlogPromptORM)
                    .filter_by(agent_name=agent_name)
                    .order_by(BlogPromptORM.version.desc())
                    .first()
                )
                if not latest:
                    continue  # seed prompts not yet inserted

                perf = self._aggregate_performance(session, agent_name)
                mutation = await self.mutator.run(
                    self.mutator.Input(
                        agent_name=agent_name,
                        prompt_version=latest.version,
                        performance_summary=perf["summary"],
                        examples=perf["examples"],
                    )
                )

                new_prompt = BlogPromptORM(
                    agent_name=agent_name,
                    version=latest.version + 1,
                    system_prompt=mutation.system_prompt,
                    prompt=mutation.prompt,
                )
                session.add(new_prompt)
                session.flush()  # to obtain new_prompt.id

                session.add(
                    PromptMutationLogORM(
                        agent_name=agent_name,
                        old_prompt_id=latest.id,
                        new_prompt_id=new_prompt.id,
                        mutation_reason=mutation.reason,
                    )
                )
                summary["mutated"] += 1
        return summary

    # ---------- helper ----------
    def _aggregate_performance(self, session, agent_name: str) -> dict:
        """Return {summary: {...}, examples: [...]} for the requested agent."""
        rows = (
            session.query(ArticleORM, PerformanceORM)
            .join(PerformanceORM, PerformanceORM.article_id == ArticleORM.id)
            .order_by(PerformanceORM.collected_at.desc())
            .limit(20)
            .all()
        )
        if not rows:
            return {"summary": {}, "examples": []}

        summary = {
            "avg_views": sum(r[1].views for r in rows) / len(rows),
            "avg_read_time": sum(r[1].read_time for r in rows) / len(rows),
            "avg_reactions": sum(r[1].reactions for r in rows) / len(rows),
        }
        examples = [
            {
                "article_id": r[0].id,
                "title": r[0].title,
                "views": r[1].views,
                "read_time": r[1].read_time,
                "reactions": r[1].reactions,
            }
            for r in rows
        ]
        return {"summary": summary, "examples": examples}

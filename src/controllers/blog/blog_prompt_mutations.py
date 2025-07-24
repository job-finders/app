

from src.agents.prompts import PromptMutatorAgent
from src.database import {
    PromptORM,
    PromptMutationLogORM,
    ArticleORM,
    PerformanceORM,

}


class PromptMutationController(Controllers):
    def __init__(self, factory):
        super().__init__(factory=factory)
        self.factory = factory
        # The Agent to mutate prompts for blog agents based on performance
        self.mutator = PromptMutatorAgent(user_id="system")
        # Initialize the logger
        self.logger  = get_service("logger")()(self.__class__.__name__)

    def init_app(self, app):
        super().init_app(app)   
        self.logger.info("PromptMutationController initialized")

        
    async def daily_mutate_prompts(self) -> dict:
        """Daily mutation of prompts for blog agents based on performance."""
        
        summary = {"mutated": 0}
        with self.get_session() as s:
            # TODO - ensure the agents matches the Agents that can be Mutated
            for agent_name in ["TopicDiscoveryAgent", "ArticlePlannerAgent", "ContentGeneratorAgent"]:
                # 1. load latest prompt
                latest = (
                    s.query(PromptORM)
                    .filter_by(agent_name=agent_name)
                    .order_by(PromptORM.version.desc())
                    .first()
                )
                if not latest:
                    continue  # seed prompts not loaded yet

                # 2. gather performance summary for this agent
                perf = self._aggregate_performance(s, agent_name)

                # 3. mutate
                mutation = await self.mutator.run(
                    PromptMutatorAgent.Input(
                        agent_name=agent_name,
                        prompt_version=latest.version,
                        performance_summary=perf["summary"],
                        examples=perf["examples"],
                    )
                )

                # 4. store new prompt
                new_prompt = PromptORM(
                    agent_name=agent_name,
                    version=latest.version + 1,
                    system_jinja=mutation.new_system_jinja,
                    user_jinja=mutation.new_user_jinja,
                )
                s.add(new_prompt)
                s.add(
                    PromptMutationLogORM(
                        agent_name=agent_name,
                        old_prompt_id=latest.id,
                        new_prompt_id=new_prompt.id,
                        mutation_reason=mutation.reason,
                    )
                )
                summary["mutated"] += 1
        return summary

    def _aggregate_performance(self, session, agent_name: str) -> dict:
        """Return summary dict + last N examples for the agent."""
        # Example: join Article → Performance tables and compute averages
        rows = (
            session.query(ArticleORM, PerformanceORM)
            .join(PerformanceORM, PerformanceORM.article_id == ArticleORM.id)
            .order_by(PerformanceORM.collected_at.desc())
            .limit(20)
            .all()
        )
        summary = {
            "avg_views": sum(r[1].views for r in rows) / max(len(rows), 1),
            "avg_read_time": sum(r[1].read_time for r in rows) / max(len(rows), 1),
        }
        examples = [
            {
                "title": r[0].title,
                "views": r[1].views,
                "read_time": r[1].read_time,
            }
            for r in rows
        ]
        return {"summary": summary, "examples": examples}


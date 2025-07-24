from __future__ import annotations
from datetime import datetime, timezone
from typing import List

import httpx
from xml.etree import ElementTree as ET

from src.controllers.controller import Controllers, error_handler
from src.logger import init_logger
from src.database import BlogPromptORM, BlogFeedbackResulORM, BlogTopicORM
from src.database.models import BlogFeedbackInput, BlogFeedbackOutput, BlogTopic
from src.services.hashnode.hashnode_service import HashnodeService, CreatePostInput, UpdatePostInput
from src.config import config_instance

# ---- orchestration helpers (agents remain pure) ----
from src.agents.blog.agent import (
    TopicDiscoveryAgent,
    ArticlePlannerAgent,
    ContentGeneratorAgent,
    SEOAuditAgent,
    PublishingDecisionAgent,
    SocialAmplifierAgent,
    ABTestDesignerAgent,
    ArchiveCuratorAgent,
    PerformanceMonitorAgent,
    RefinerAgent,
)
from src.agents.base import UserRole


class BlogAgentController(Controllers):
    """
    Controller for managing blog generation agents **and** Hashnode persistence.
    All mutations (create/update/delete) are performed via the injected HashnodeService.
    Agents return pure data; this class orchestrates the flow and writes to Hashnode.
    """

    def __init__(self, factory):
        super().__init__(factory)
        self.logger = init_logger("BlogAgentController")

        # --- Hashnode wiring ---
        token = config_instance().HASHNODE_TOKEN
        self.hashnode = HashnodeService(token) if token else None
        if not self.hashnode:
            self.logger.warning("HASHNODE_TOKEN missing – Hashnode features disabled")

        # --- agent singletons ---
        self.agents = {
            "topic_discovery": TopicDiscoveryAgent(user_id="system"),
            "article_planner": ArticlePlannerAgent(user_id="system"),
            "content_generator": ContentGeneratorAgent(user_id="system"),
            "seo_audit": SEOAuditAgent(user_id="system"),
            "publishing_decision": PublishingDecisionAgent(user_id="system"),
            "social_amplifier": SocialAmplifierAgent(user_id="system"),
            "ab_designer": ABTestDesignerAgent(user_id="system"),
            "archive_curator": ArchiveCuratorAgent(user_id="system"),
            "performance_monitor": PerformanceMonitorAgent(user_id="system"),
            "refiner": RefinerAgent(user_id="system"),
        }

    # ------------------------------------------------------------------
    # Existing DB-layer methods (unchanged)
    # ------------------------------------------------------------------
    @error_handler
    async def create_blog_topic(self, topic_in: BlogTopic) -> BlogTopic:
        with self.get_session() as session:
            existing = (
                session.query(BlogTopic)
                .filter(BlogTopic.title == topic_in.title)
                .first()
            )
            if existing:
                raise ValueError(f"Blog topic '{topic_in.title}' already exists")
            topic = BlogTopic(title=topic_in.title, created_at=datetime.utcnow())
            session.add(topic)
            return topic_in

    @error_handler
    async def add_blog_prompt(self, prompt_in: BlogPromptORM) -> BlogPromptORM:
        with self.get_session() as session:
            topic = (
                session.query(BlogTopicORM)
                .filter(BlogTopicORM.id == prompt_in.topic_id)
                .first()
            )
            if not topic:
                raise ValueError(f"Blog topic id {prompt_in.topic_id} not found")
            prompt = BlogPromptORM(
                content=prompt_in.content,
                topic_id=prompt_in.topic_id,
                created_at=datetime.now(timezone.utc),
                feedback_score=0.0,
            )
            session.add(prompt)
            return prompt_in

    @error_handler
    async def get_prompts_for_topic(self, topic_id: int) -> List[BlogPromptORM]:
        with self.get_session() as session:
            prompts = (
                session.query(BlogPromptORM)
                .filter(BlogPromptORM.topic_id == topic_id)
                .all()
            )
            return [BlogPromptORM(**p.__dict__) for p in prompts]

    @error_handler
    async def update_feedback_score(
        self, feedback_in: BlogFeedbackInput
    ) -> BlogFeedbackOutput:
        from src.controllers.blog.blog_feedback_controller import BlogFeedbackController

        feedback_controller = BlogFeedbackController()
        return await feedback_controller.submit_feedback(feedback_in)

    # ------------------------------------------------------------------
    # NEW: Hashnode read-only helpers
    # ------------------------------------------------------------------
    async def list_hashnode_posts(self, page: int = 0, limit: int = 10):
        """
        Return live posts from Hashnode (cached in Redis for 60s).
        """
        if not self.hashnode:
            raise RuntimeError("Hashnode not configured")
        pub_info = await self.hashnode.get_user_info()
        pub_id = pub_info["data"]["me"]["publication"]["id"]
        return await self.hashnode.list_publication_posts(
            publication_id=pub_id, page=page, limit=limit
        )

    async def get_hashnode_analytics(self, post_id: str):
        """
        Pull real-time analytics for a single post.
        """
        if not self.hashnode:
            raise RuntimeError("Hashnode not configured")
        pub_info = await self.hashnode.get_user_info()
        pub_id = pub_info["data"]["me"]["publication"]["id"]
        return await self.hashnode.get_post_analytics(publication_id=pub_id, post_id=post_id)

    # ------------------------------------------------------------------
    # NEW: orchestration flows (agent → Hashnode)
    # ------------------------------------------------------------------
    async def generate_and_publish_post(
        self,
        site_map: dict,
        publication_id: str,
        publish: bool = False,
    ):
        """
        End-to-end flow:
        1. Discover topics
        2. Plan outline
        3. Generate content
        4. SEO audit
        5. Decide publish
        6. Optionally push to Hashnode
        Returns the Hashnode response or draft ID.
        """
        if not self.hashnode:
            raise RuntimeError("Hashnode not configured")

        # --- pure data pipeline ---
        topics = await self.agents["topic_discovery"].run(site_map)
        outline = await self.agents["article_planner"].run(topics[0])
        content = await self.agents["content_generator"].run(outline)
        seo = await self.agents["seo_audit"].run(content)
        decision = await self.agents["publishing_decision"].run(seo)

        if decision.action != "publish":
            return {"status": "held", "reason": decision.reasoning, "outline_slug": outline.slug}

        # --- Hashnode mutation ---
        hashnode_input = CreatePostInput(
            publication_id=publication_id,
            title=content.title,
            content_markdown=content.markdown,
            is_draft=not publish,
        )
        hashnode_resp = await self.hashnode.create_post(hashnode_input)
        return {
            "status": "published" if publish else "draft_created",
            "hashnode_id": hashnode_resp["data"]["createStory"]["post"]["id"],
            "slug": hashnode_resp["data"]["createStory"]["post"]["slug"],
            "url": f"https://{pub_info['data']['me']['publication']['domain']}/{hashnode_resp['data']['createStory']['post']['slug']}",
        }

    async def refine_existing_post(self, post_id: str):
        """
        Pull analytics → run RefinerAgent → optionally update post.
        Returns the orchestrator result, *not* the new Hashnode post.
        """
        if not self.hashnode:
            raise RuntimeError("Hashnode not configured")

        pub_info = await self.hashnode.get_user_info()
        pub_id = pub_info["data"]["me"]["publication"]["id"]

        metrics = await self.hashnode.get_post_analytics(publication_id=pub_id, post_id=post_id)
        refinement = await self.agents["refiner"].run(metrics)
        return {
            "post_id": post_id,
            "refinement": refinement.model_dump(),
            "action_required": refinement.action,
        }

    async def fetch_hashnode_sitemap(self) -> dict[str, list[str]]:
        """
        Returns { "section_slug": [ "post-slug-1", ... ] } by parsing Hashnode's sitemap.xml.
        """
        if not self.hashnode:
            return {}

        pub_info = await self.hashnode.get_user_info()
        domain = pub_info["data"]["me"]["publication"]["domain"]
        sitemap_url = f"https://{domain}/sitemap.xml"

        async with httpx.AsyncClient() as client:
            xml_text = (await client.get(sitemap_url)).text

        root = ET.fromstring(xml_text)
        urls = [
            url.text.strip()
            for url in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        ]

        # naive grouping by path segment
        site_map = {}
        for url in urls:
            slug = url.rstrip("/").split("/")[-1]
            site_map.setdefault("posts", []).append(slug)
        return site_map


    # ---------- 00:05 UTC ----------
    async def cron_topic_generator(self) -> int:
        """Discover new topics, store in DB."""
        sitemap = await self.fetch_hashnode_sitemap()
        topics  = await self.agents["topic_discovery"].run(sitemap)
        with self.get_session() as s:
            for t in topics:
                if not s.query(TopicORM).filter_by(title=t.title).first():
                    s.add(TopicORM(title=t.title, keywords=t.keywords))
        return len(topics)

    # ---------- 02:00 UTC ----------
    async def cron_article_creator(self) -> int:
        """Turn every unprocessed topic into an Article draft."""
        created = 0
        with self.get_session() as s:
            for topic in s.query(TopicORM).all():
                if not s.query(ArticleORM).filter_by(topic_id=topic.id).first():
                    outline = await self.agents["article_planner"].run(topic)
                    content = await self.agents["content_generator"].run(outline)
                    draft_resp = await self.hashnode.create_post(
                        CreatePostInput(
                            publication_id=(await self.hashnode.get_user_info())["data"]["me"]["publication"]["id"],
                            title=content.title,
                            content_markdown=content.markdown,
                            is_draft=True,
                        )
                    )
                    s.add(
                        ArticleORM(
                            topic_id=topic.id,
                            title=content.title,
                            markdown=content.markdown,
                            draft_hashnode_id=draft_resp["data"]["createStory"]["post"]["id"],
                        )
                    )
                    created += 1
        return created

    # ---------- 03:00 UTC ----------
    async def cron_draft_scheduler(self) -> int:
        """Create ScheduledPost rows for every unscheduled draft."""
        scheduled = 0
        start = datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0)
        interval = timedelta(hours=4)  # four posts / day
        with self.get_session() as s:
            for i, article in enumerate(
                s.query(ArticleORM).outerjoin(ScheduledPostORM).filter(ScheduledPostORM.id.is_(None))
            ):
                scheduled_time = start + i * interval
                s.add(
                    ScheduledPostORM(
                        article_id=article.id,
                        scheduled_at=scheduled_time,
                        hashnode_post_id=article.draft_hashnode_id,
                    )
                )
                scheduled += 1
        return scheduled

    # ---------- 09:00 UTC ----------
    async def cron_feedback_gatherer(self) -> int:
        """Collect analytics for every live post and store locally."""
        collected = 0
        pub_id = (await self.hashnode.get_user_info())["data"]["me"]["publication"]["id"]
        with self.get_session() as s:
            for scheduled in s.query(ScheduledPostORM).filter_by(status="live").all():
                metrics = await self.hashnode.get_post_analytics(pub_id, scheduled.hashnode_post_id)
                s.add(
                    PerformanceORM(
                        article_id=scheduled.article_id,
                        views=metrics["data"]["publication"]["post"]["analytics"]["views"],
                        reactions=metrics["data"]["publication"]["post"]["analytics"]["reactions"],
                        read_time=metrics["data"]["publication"]["post"]["analytics"]["readTime"],
                    )
                )
                collected += 1
        return collected

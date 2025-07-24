from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

import httpx
from xml.etree import ElementTree as ET

from flask import Flask

from src.controllers.controller import Controllers, error_handler
from src.logger import init_logger
from src.database import BlogTopicORM, ArticleORM, ScheduledPostORM, PerformanceORM
from src.services.hashnode import HashnodeService
from src.services.hashnode.schema import CreatePostInput
from src.config import config_instance
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

from .utils import generate_cover_image, generate_social_card


class BlogAgentController(Controllers):
    """
    Central orchestrator for the entire blog pipeline.
    Main flow = 4 daily crons (topic → draft → schedule → analytics).
    Utility helpers below are **deprecated**; they exist only for
    CLI / admin use and do **not** participate in the automated pipeline.
    """

    def __init__(self, factory):
        super().__init__(factory)
        self.logger = init_logger("BlogAgentController")
        token = config_instance().HASHNODE_TOKEN
        self.hashnode = HashnodeService(token) if token else None
        if not self.hashnode:
            self.logger.warning("HASHNODE_TOKEN missing – Hashnode features disabled")

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

    def init_app(self, app: Flask):
        super().init_app(app=app)

    # ---------- daily crons (canonical flow) ----------
    async def cron_topic_generator(self) -> int:
        """00:05 UTC – discover topics & persist them (canonical)."""
        sitemap = await self.fetch_hashnode_sitemap()
        topics = await self.agents["topic_discovery"].run(sitemap)
        with self.get_session() as session:
            for topic in topics:
                if not session.query(BlogTopicORM).filter_by(title=topic.title).first():
                    session.add(BlogTopicORM(title=topic.title, keywords=topic.keywords))
            return len(topics)

    async def cron_article_creator(self) -> int:
        """02:00 UTC – create article drafts & persist them (canonical)."""
        created = 0
        with self.get_session() as session:
            for topic in session.query(BlogTopicORM).all():
                if session.query(ArticleORM).filter_by(topic_id=topic.id).first():
                    continue
                outline = await self.agents["article_planner"].run(topic)
                content = await self.agents["content_generator"].run(outline)
                cover = await generate_cover_image(content.title)
                social = await generate_social_card(content.title)

                draft = await self.hashnode.create_post(
                    CreatePostInput(
                        publication_id=(await self.hashnode.get_user_info())["data"]["me"]["publication"]["id"],
                        title=content.title,
                        content_markdown=content.markdown,
                        is_draft=True,
                        cover_image_url=cover,
                        social_image_url=social,
                    )
                )
                session.add(
                    ArticleORM(
                        topic_id=topic.id,
                        title=content.title,
                        markdown=content.markdown,
                        draft_hashnode_id=draft["data"]["createStory"]["post"]["id"],
                    )
                )
                created += 1
        return created

    async def cron_draft_scheduler(self) -> int:
        """03:00 UTC – schedule drafts (canonical)."""
        scheduled = 0
        start = datetime.utcnow().replace(hour=9, minute=0)
        interval = timedelta(hours=4)
        with self.get_session() as session:
            for i, art in enumerate(
                    session.query(ArticleORM)
                            .outerjoin(ScheduledPostORM)
                            .filter(ScheduledPostORM.id.is_(None))
            ):
                session.add(
                    ScheduledPostORM(
                        article_id=art.id,
                        scheduled_at=start + i * interval,
                        hashnode_post_id=art.draft_hashnode_id,
                    )
                )
                scheduled += 1
        return scheduled

    async def cron_feedback_gatherer(self) -> int:
        """09:00 UTC – pull Hashnode analytics into PerformanceORM (canonical)."""
        collected = 0
        pub_id = (await self.hashnode.get_user_info())["data"]["me"]["publication"]["id"]
        with self.get_session() as session:
            for scheduled in session.query(ScheduledPostORM).filter_by(status="live").all():
                metrics = await self.hashnode.get_post_analytics(pub_id, scheduled.hashnode_post_id)
                session.add(
                    PerformanceORM(
                        article_id=scheduled.article_id,
                        views=metrics["data"]["publication"]["post"]["analytics"]["views"],
                        reactions=metrics["data"]["publication"]["post"]["analytics"]["reactions"],
                        read_time=metrics["data"]["publication"]["post"]["analytics"]["readTime"],
                        comments=metrics["data"]["publication"]["post"]["analytics"]["comments"],
                        shares=metrics["data"]["publication"]["post"]["analytics"]["shares"],
                    )
                )
                collected += 1
        return collected

    # ---------- utility helpers (deprecated / kept for CLI / admin) ----------
    async def fetch_hashnode_sitemap(self) -> Dict[str, List[str]]:
        """DEPRECATED: raw sitemap fetch; only used by daily crons above."""
        if not self.hashnode:
            return {}
        domain = (await self.hashnode.get_user_info())["data"]["me"]["publication"]["domain"]
        url = f"https://{domain}/sitemap.xml"
        async with httpx.AsyncClient() as client:
            xml = await client.get(url)
        root = ET.fromstring(xml.text)
        slugs = [loc.text.strip().split("/")[-1] for loc in
                 root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        return {"posts": slugs}

    async def list_hashnode_posts(self, page: int = 0, limit: int = 10) -> Dict[str, Any]:
        """DEPRECATED: list posts; kept for admin dashboard."""
        if not self.hashnode:
            raise RuntimeError("Hashnode not configured")
        pub_id = (await self.hashnode.get_user_info())["data"]["me"]["publication"]["id"]
        return await self.hashnode.list_publication_posts(publication_id=pub_id, page=page, limit=limit)

    async def get_hashnode_analytics(self, post_id: str) -> Dict[str, Any]:
        """DEPRECATED: single-post analytics; superseded by cron_feedback_gatherer."""
        if not self.hashnode:
            raise RuntimeError("Hashnode not configured")
        pub_id = (await self.hashnode.get_user_info())["data"]["me"]["publication"]["id"]
        return await self.hashnode.get_post_analytics(publication_id=pub_id, post_id=post_id)

    async def generate_and_publish_post(
            self,
            site_map: Dict[str, List[str]],
            publication_id: str,
            publish: bool = False,
    ) -> Dict[str, Any]:
        """
        DEPRECATED: full end-to-end flow now split into crons.
        Kept for CLI / admin one-off use.
        """
        if not self.hashnode:
            raise RuntimeError("Hashnode not configured")

        topics = await self.agents["topic_discovery"].run(site_map)
        outline = await self.agents["article_planner"].run(topics[0])
        content = await self.agents["content_generator"].run(outline)
        seo = await self.agents["seo_audit"].run(content)
        decision = await self.agents["publishing_decision"].run(seo)

        if decision.action != "publish":
            return {"status": "held", "reason": decision.reasoning, "outline_slug": outline.slug}

        draft = await self.hashnode.create_post(
            CreatePostInput(
                publication_id=publication_id,
                title=content.title,
                content_markdown=content.markdown,
                is_draft=not publish,
                cover_image_url=await generate_cover_image(content.title),
                social_image_url=await generate_social_card(content.title),
            )
        )
        return {
            "status": "published" if publish else "draft_created",
            "hashnode_id": draft["data"]["createStory"]["post"]["id"],
            "slug": draft["data"]["createStory"]["post"]["slug"],
        }

    async def refine_existing_post(self, post_id: str) -> Dict[str, Any]:
        """
        DEPRECATED: manual refinement; superseded by cron_feedback_gatherer.
        Kept for CLI / admin one-off use.
        """
        if not self.hashnode:
            raise RuntimeError("Hashnode not configured")
        pub_id = (await self.hashnode.get_user_info())["data"]["me"]["publication"]["id"]
        metrics = await self.hashnode.get_post_analytics(publication_id=pub_id, post_id=post_id)
        refinement = await self.agents["refiner"].run(metrics)
        return {"post_id": post_id, "refinement": refinement.model_dump()}


from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

import httpx
from xml.etree import ElementTree as ET

from flask import Flask

from src.agents.base import TaskType, UserRole
from src.database.models import User
from src.controllers.controller import Controllers

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
from src.utils.route_helpers import get_service

from .utils import generate_cover_image, generate_social_card
import asyncio

from ..controller import error_handler


class BlogAgentController(Controllers):
    def __init__(self, factory):
        super().__init__(factory)
        # ----- synchronous, lightweight setup -----
        self.logger = get_service('logger')()(self.__class__.__name__)
        token = config_instance().HASHNODE_TOKEN
        self.hashnode = HashnodeService(token) if token else None
        # ----- run the async part now -----
        self.agents = {}

    async def async_init(self):
        """Build all agents asynchronously."""
        system_admin: User = await self.get_system_admin()
        user_id = system_admin.uid if system_admin else "system"

        self.agents = {
            "topic_discovery": TopicDiscoveryAgent(user_id=user_id),
            "article_planner": ArticlePlannerAgent(user_id=user_id),
            "content_generator": ContentGeneratorAgent(user_id=user_id),
            "seo_audit": SEOAuditAgent(user_id=user_id),
            "publishing_decision": PublishingDecisionAgent(user_id=user_id),
            "social_amplifier": SocialAmplifierAgent(user_id=user_id),
            "ab_designer": ABTestDesignerAgent(user_id=user_id),
            "archive_curator": ArchiveCuratorAgent(user_id=user_id),
            "performance_monitor": PerformanceMonitorAgent(user_id=user_id),
            "refiner": RefinerAgent(user_id=user_id),
        }

    # Remove the old init_app override – it is no longer needed.
    def init_app(self, app: Flask):
        super().init_app(app=app)
        # 1. create a brand-new event loop
        if not self.hashnode:
            self.logger.warning("HASHNODE_TOKEN missing – Hashnode features disabled")

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)  # optional, keeps warnings quiet
            # 2. run async_init and block until it finishes
            loop.run_until_complete(self.async_init())
        finally:
            # 3. always clean up
            loop.close()
            asyncio.set_event_loop(None)  # remove the temporary loop

    # ---------- daily  (canonical flow) ----------
    async def cron_topic_generator(self) -> int:
        """00:05 UTC – discover topics & persist them (canonical)."""
        sitemap = await self.fetch_hashnode_sitemap()
        topics = await self.agents["topic_discovery"].run(sitemap=sitemap, user_role=UserRole.SYSTEM_ADMIN,
                                                          task_type=TaskType.STRATEGY.value)
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
                outline = await self.agents["article_planner"].run(topic=topic, user_role=UserRole.SYSTEM_ADMIN,
                                                                   task_type=TaskType.PLAN.value)
                content = await self.agents["content_generator"].run(outline=outline, user_role=UserRole.SYSTEM_ADMIN,
                                                                     task_type=TaskType.WRITING.value)
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
        start = datetime.now(timezone.utc).replace(hour=9, minute=0)
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

    @error_handler
    async def cron_feedback_gatherer(self) -> int | None:
        """09:00 UTC – pull Hashnode analytics into PerformanceORM (canonical)."""
        collected = 0

        user_info = await self.hashnode.get_user_info()
        if user_info is None:
            self.logger.error("Failed to retrieve user info from Hashnode – skipping feedback gathering.")
            return None  # or 0 if you prefer a consistent return type
        try:
            pub_id = user_info["data"]["me"]["publication"]["id"]
        except (KeyError, TypeError) as e:
            self.logger.error(f"Malformed user info structure received: {user_info} – error: {e}")
            return None  # or 0

        with self.get_session() as session:
            for scheduled in session.query(ScheduledPostORM).filter_by(status="live").all():
                if not scheduled.hashnode_post_id:
                    self.logger.warning(f"Scheduled post {scheduled.id} has no hashnode_post_id set.")
                    continue
                try:
                    metrics = await self.hashnode.get_post_analytics(pub_id, scheduled.hashnode_post_id)
                    if not metrics:
                        self.logger.warning(f"No metrics returned for post {scheduled.hashnode_post_id}.")
                        continue

                    # Defensive access to nested fields
                    analytics = (
                        metrics.get("data", {})
                        .get("publication", {})
                        .get("post", {})
                        .get("analytics", {})
                    )

                    if not analytics:
                        self.logger.warning(
                            f"Analytics missing or malformed for post {scheduled.hashnode_post_id}. Raw: {metrics}")
                        continue

                    session.add(
                        PerformanceORM(
                            article_id=scheduled.article_id,
                            views=analytics.get("views", 0),
                            reactions=analytics.get("reactions", 0),
                            read_time=analytics.get("readTime", 0),
                            comments=analytics.get("comments", 0),
                            shares=analytics.get("shares", 0),
                        )
                    )
                    collected += 1

                except Exception as e:
                    self.logger.error(
                        f"Error processing analytics for post {scheduled.hashnode_post_id}: {e}",
                        exc_info=True  # logs traceback
                    )
                    continue

        return collected

    @error_handler
    async def fetch_hashnode_sitemap(self) -> Dict[str, List[str]]:
        """DEPRECATED: raw sitemap fetch; only used by daily crons above."""
        if not self.hashnode:
            self.logger.warning("Hashnode client not initialized. Skipping sitemap fetch.")
            return {"posts": []}

        try:
            user_info = await self.hashnode.get_user_info()
            domain = (
                user_info.get("data", {})
                .get("me", {})
                .get("publication", {})
                .get("domain")
            )
            if not domain:
                self.logger.error(f"Could not extract domain from user_info: {user_info}")
                return {"posts": []}

            url = f"https://{domain}/sitemap.xml"
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                response.raise_for_status()
                xml_text = response.text

            try:
                root = ET.fromstring(xml_text)
                slugs = [
                    loc.text.strip().split("/")[-1]
                    for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                    if loc.text
                ]
                return {"posts": slugs}
            except ET.ParseError as e:
                self.logger.error(f"Failed to parse sitemap XML from {url}: {e}")
                return {"posts": []}

        except httpx.RequestError as e:
            self.logger.error(f"HTTP error fetching sitemap from {url if 'url' in locals() else '[unknown]'}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during sitemap fetch: {e}", exc_info=True)

        return {"posts": []}

    @error_handler
    async def list_hashnode_posts(self, page: int = 0, limit: int = 10) -> Dict[str, Any]:
        """DEPRECATED: list posts; kept for admin dashboard."""
        if not self.hashnode:
            raise RuntimeError("Hashnode not configured")

        try:
            user_info = await self.hashnode.get_user_info()
            pub_id = (
                user_info.get("data", {})
                .get("me", {})
                .get("publication", {})
                .get("id")
            )

            if not pub_id:
                self.logger.error(f"Could not extract publication ID from user info: {user_info}")
                return {"posts": []}

            return await self.hashnode.list_publication_posts(
                publication_id=pub_id,
                page=page,
                limit=limit
            )

        except Exception as e:
            self.logger.error(f"Failed to list Hashnode posts: {e}", exc_info=True)
            return {"posts": []}

    @error_handler
    async def get_hashnode_analytics(self, post_id: str) -> Dict[str, Any]:
        """DEPRECATED: single-post analytics; superseded by cron_feedback_gatherer."""
        if not self.hashnode:
            raise RuntimeError("Hashnode not configured")

        try:
            user_info = await self.hashnode.get_user_info()
            pub_id = (
                user_info.get("data", {})
                .get("me", {})
                .get("publication", {})
                .get("id")
            )

            if not pub_id:
                self.logger.error(f"Could not extract publication ID from user info: {user_info}")
                return {}

            analytics = await self.hashnode.get_post_analytics(publication_id=pub_id, post_id=post_id)
            if not analytics:
                self.logger.warning(f"No analytics returned for post_id={post_id}.")
                return {}

            return analytics

        except Exception as e:
            self.logger.error(f"Error fetching analytics for post_id={post_id}: {e}", exc_info=True)
            return {}

    @error_handler
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

        try:
            topics = await self.agents["topic_discovery"].run(site_map=site_map, user_role=UserRole.SYSTEM_ADMIN,
                                                              task_type=TaskType.WRITING.value)
            if not topics:
                self.logger.warning("Topic discovery agent returned no topics.")
                return {"status": "failed", "reason": "no_topics"}

            outline = await self.agents["article_planner"].run(topic=topics[0], user_role=UserRole.SYSTEM_ADMIN,
                                                               task_type=TaskType.EVALUATION.value)
            if not outline:
                self.logger.warning("Article planner agent returned no outline.")
                return {"status": "failed", "reason": "no_outline"}

            content = await self.agents["content_generator"].run(outline=outline, user_role=UserRole.SYSTEM_ADMIN,
                                                                 task_type=TaskType.WRITING.value)
            if not content or not getattr(content, "markdown", None):
                self.logger.warning("Content generator agent returned empty or invalid content.")
                return {"status": "failed", "reason": "invalid_content"}

            seo = await self.agents["seo_audit"].run(content=content, user_role=UserRole.SYSTEM_ADMIN,
                                                     task_type=TaskType.EVALUATION.value)
            decision = await self.agents["publishing_decision"].run(seo)

            if decision.action != "publish":
                return {
                    "status": "held",
                    "reason": decision.reasoning,
                    "outline_slug": getattr(outline, "slug", None),
                }

            # Defensive fallback values for generated assets
            cover_url = await generate_cover_image(content.title)
            social_url = await generate_social_card(content.title)

            draft = await self.hashnode.create_post(
                CreatePostInput(
                    publication_id=publication_id,
                    title=content.title,
                    content_markdown=content.markdown,
                    is_draft=not publish,
                    cover_image_url=cover_url or "",
                    social_image_url=social_url or "",
                )
            )

            post_data = (
                draft.get("data", {})
                .get("createStory", {})
                .get("post", {})
            )

            if not post_data:
                self.logger.error(f"Post creation response malformed: {draft}")
                return {"status": "failed", "reason": "post_creation_failed"}

            return {
                "status": "published" if publish else "draft_created",
                "hashnode_id": post_data.get("id"),
                "slug": post_data.get("slug"),
            }

        except Exception as e:
            self.logger.error(f"Failed to generate and publish post: {e}", exc_info=True)
            return {"status": "failed", "reason": str(e)}

    @error_handler
    async def refine_existing_post(self, post_id: str) -> Dict[str, Any]:
        """
        DEPRECATED: manual refinement; superseded by cron_feedback_gatherer.
        Kept for CLI / admin one-off use.
        """
        if not self.hashnode:
            raise RuntimeError("Hashnode not configured")

        try:
            user_info = await self.hashnode.get_user_info()
            pub_id = (
                user_info.get("data", {})
                .get("me", {})
                .get("publication", {})
                .get("id")
            )

            if not pub_id:
                self.logger.error(f"Could not extract publication ID from user info: {user_info}")
                return {"post_id": post_id, "status": "failed", "reason": "no_publication_id"}

            metrics = await self.hashnode.get_post_analytics(publication_id=pub_id, post_id=post_id)
            if not metrics:
                self.logger.warning(f"No analytics returned for post {post_id}")
                return {"post_id": post_id, "status": "failed", "reason": "no_metrics"}

            refinement = await self.agents["refiner"].run(metrics)
            if not refinement or not hasattr(refinement, "model_dump"):
                self.logger.warning(f"Refinement agent returned invalid output for post {post_id}")
                return {"post_id": post_id, "status": "failed", "reason": "invalid_refinement"}

            return {
                "post_id": post_id,
                "status": "refined",
                "refinement": refinement.model_dump()
            }

        except Exception as e:
            self.logger.error(f"Error refining post {post_id}: {e}", exc_info=True)
            return {"post_id": post_id, "status": "failed", "reason": str(e)}

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .schema import {
    CreatePostInput,
    UpdatePostInput,
    DeletePostInput,
    SchedulePostInput,
    AddTagsInput,
    CreateSeriesInput,
    AddPostToSeriesInput
}

from src.services.hashnode.hashnode_client import HashnodeClient

# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------
class HashnodeService:
    """
    High-level façade over Hashnode GraphQL API.

    All methods are async, pure-data in/out, and safe for AI agents.
    """

    def __init__(self, token: str) -> None:
        self.client = HashnodeClient(token)

    # ---------- User / Publication ----------
    async def get_user_info(self) -> Dict[str, Any]:
        query = """
        query {
          me {
            id
            username
            name
            publication {
              id
              title
              domain
            }
          }
        }
        """
        return await self.client.query(query)

    # ---------- Posts ----------
    async def create_post(self, data: CreatePostInput) -> Dict[str, Any]:
        mutation = """
        mutation CreateStory($input: CreateStoryInput!) {
          createStory(input: $input) {
            post {
              id
              title
              slug
              dateAdded
            }
          }
        }
        """
        payload = {
            "title": data.title,
            "contentMarkdown": data.content_markdown,
            "isPartOfPublication": {"publicationId": data.publication_id},
            "isDraft": data.is_draft,
        }
        if data.slug:
            payload["slug"] = data.slug
        return await self.client.query(mutation, {"input": payload})

    async def update_post(self, data: UpdatePostInput) -> Dict[str, Any]:
        mutation = """
        mutation UpdateStory($input: UpdateStoryInput!) {
          updateStory(input: $input) {
            code
            success
            message
          }
        }
        """
        return await self.client.query(mutation, {"input": data.dict()})

    async def get_post(self, publication_id: str, post_id: str) -> Dict[str, Any]:
        query = """
        query GetPost($publicationId: ObjectId!, $postId: ObjectId!) {
          publication(id: $publicationId) {
            post(id: $postId) {
              id
              title
              slug
              brief
              contentMarkdown
              tags
              isDraft
              scheduledDate
            }
          }
        }
        """
        return await self.client.query(query, {"publicationId": publication_id, "postId": post_id})

    async def list_publication_posts(
        self, publication_id: str, page: int = 0, limit: int = 10
    ) -> Dict[str, Any]:
        query = """
        query GetPublicationPosts($publicationId: ObjectId!, $page: Int!, $limit: Int!) {
          publication(id: $publicationId) {
            posts(page: $page, limit: $limit) {
              id
              title
              slug
              brief
              coverImage
              dateAdded
            }
          }
        }
        """
        return await self.client.query(
            query, {"publicationId": publication_id, "page": page, "limit": limit}
        )

    # ---------- Analytics ----------
    async def get_post_analytics(
        self, publication_id: str, post_id: str
    ) -> Dict[str, Any]:
        query = """
        query GetPostAnalytics($publicationId: ObjectId!, $postId: ObjectId!) {
          publication(id: $publicationId) {
            post(id: $postId) {
              analytics {
                views
                readTime
                reactions
                comments
                shares
              }
            }
          }
        }
        """
        return await self.client.query(query, {"publicationId": publication_id, "postId": post_id})

    # ---------- Lifecycle Actions ----------
    async def publish_draft(self, post_id: str) -> Dict[str, Any]:
        mutation = """
        mutation PublishStory($input: PublishStoryInput!) {
          publishStory(input: $input) {
            post { id slug }
          }
        }
        """
        return await self.client.query(mutation, {"input": {"id": post_id}})

    async def unpublish_post(self, post_id: str) -> Dict[str, Any]:
        mutation = """
        mutation UnpublishStory($input: UnpublishStoryInput!) {
          unpublishStory(input: $input) {
            post { id slug }
          }
        }
        """
        return await self.client.query(mutation, {"input": {"id": post_id}})

    async def delete_post(self, data: DeletePostInput) -> Dict[str, Any]:
        mutation = """
        mutation DeleteStory($input: DeleteStoryInput!) {
          deleteStory(input: $input) {
            success
          }
        }
        """
        return await self.client.query(mutation, {"input": {"id": data.post_id}})

    async def schedule_post(self, data: SchedulePostInput) -> Dict[str, Any]:
        mutation = """
        mutation ScheduleStory($input: ScheduleStoryInput!) {
          scheduleStory(input: $input) {
            post { id slug scheduledDate }
          }
        }
        """
        return await self.client.query(
            mutation, {"input": {"id": data.post_id, "scheduledAt": data.scheduled_at.isoformat()}}
        )

    # ---------- Tags ----------
    async def add_tags_to_post(self, data: AddTagsInput) -> Dict[str, Any]:
        mutation = """
        mutation UpdateStory($input: UpdateStoryInput!) {
          updateStory(input: $input) {
            post { id tags }
          }
        }
        """
        return await self.client.query(
            mutation, {"input": {"id": data.post_id, "tags": data.tags}}
        )

    # ---------- Series ----------
    async def create_series(self, data: CreateSeriesInput) -> Dict[str, Any]:
        mutation = """
        mutation CreateSeries($input: CreateSeriesInput!) {
          createSeries(input: $input) {
            series { slug name }
          }
        }
        """
        payload = {"name": data.name, "description": data.description}
        if data.cover_image_url:
            payload["coverImage"] = data.cover_image_url
        return await self.client.query(mutation, {"input": payload})

    async def add_post_to_series(self, data: AddPostToSeriesInput) -> Dict[str, Any]:
        mutation = """
        mutation AddToSeries($input: AddToSeriesInput!) {
          addToSeries(input: $input) {
            success
          }
        }
        """
        return await self.client.query(
            mutation, {"input": {"postId": data.post_id, "seriesSlug": data.series_slug}}
        )

    async def get_series_posts(self, series_slug: str) -> Dict[str, Any]:
        query = """
        query SeriesPosts($slug: String!) {
          series(slug: $slug) {
            posts {
              id
              title
              slug
            }
          }
        }
        """
        return await self.client.query(query, {"slug": series_slug})
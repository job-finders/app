
# services/hashnode_service.py
from typing import Optional
from pydantic import BaseModel

from src.services.hashnode.hashnode_service import HashnodeClient


# --- Input Models (for AI agents or validation) ---
class CreatePostInput(BaseModel):
    """
    CreatePostInput

    A structured input model for creating a new blog post on Hashnode.

    This model ensures consistent validation and schema compliance when initiating content creation.
    It is designed for use in API endpoints, service layers, and by AI agents issuing structured commands.

    ---
    Fields:
    - publication_id (str): The ID of the publication where the post will be published. Required.
    - title (str): The headline/title of the blog post. Required.
    - content_markdown (str): The full body of the post in Markdown format. Required.
    - slug (Optional[str]): A custom URL slug (e.g., 'my-awesome-post'). Optional.
    - is_draft (bool): Whether to save the post as a draft or publish it. Defaults to `True`.

    ---
    Example Usage:
        CreatePostInput(
            publication_id="pub_123",
            title="Understanding Event Loops",
            content_markdown="# Async in Python\nThis is how it works...",
            is_draft=False
        )

    ---
    Notes for AI Agents:
    - Ensure all required fields are filled.
    - Markdown syntax must be properly formatted.
    - Use `is_draft=True` to prevent accidental publication during test runs.
    """
    publication_id: str
    title: str
    content_markdown: str
    slug: Optional[str] = None
    is_draft: bool = True


class UpdatePostInput(BaseModel):
    """
    UpdatePostInput

    A schema-compliant input model for updating an existing blog post on Hashnode.

    This model allows modification of a post's title and content. It is intended for use by backend APIs and autonomous AI agents updating blog entries programmatically.

    ---
    Fields:
    - post_id (str): The unique identifier of the blog post to be updated. Required.
    - title (str): The new title for the blog post. Required.
    - content_markdown (str): The revised body content of the post in Markdown format. Required.

    ---
    Example Usage:
        UpdatePostInput(
            post_id="post_456",
            title="Updated: Async Event Loops in Python",
            content_markdown="## Revised Content\nHere are the new insights..."
        )

    ---
    Notes for AI Agents:
    - The `post_id` must match an existing post owned by the user.
    - Ensure that content markdown adheres to formatting standards to avoid rendering issues on publish.
    """
    post_id: str
    title: str
    content_markdown: str


# --- Service Logic ---
class HashnodeService:
    """
    HashnodeService

    A high-level service that provides structured access to the Hashnode blogging platform through its GraphQL API.

    This class wraps predefined operations like fetching user information, retrieving posts, creating content, and updating blog entries.
    It is designed for both backend services and AI agent systems, ensuring a safe, schema-consistent interface.

    ---
    Dependencies:
    - Requires a valid Hashnode API token to initialize.
    - Internally uses `HashnodeClient` to perform GraphQL operations.

    ---
    Usage:
        service = HashnodeService(token="your-api-token")
        await service.get_user_info()

    ---
    AI Agent Notes:
    - Methods here are designed to be used as callable command functions.
    - Input data should typically be validated externally before being passed into the service.
    """

    def __init__(self, token: str):
        """
        Initialize the HashnodeService with an authentication token.

        Args:
            token (str): A valid Hashnode API token with access to user and publication resources.
        """
        self.client = HashnodeClient(token)

    async def get_user_info(self):
        """
        Fetch authenticated user and associated publication info from Hashnode.

        Returns:
            dict: JSON response containing user details and their primary publication.

        Example Response:
        {
            "data": {
                "me": {
                    "id": "...",
                    "username": "...",
                    "name": "...",
                    "publication": {
                        "id": "...",
                        "title": "...",
                        "domain": "..."
                    }
                }
            }
        }
        """
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

    async def get_all_posts(self, publication_id: str, page: int = 0):
        """
        Retrieve all posts for a given publication.

        Args:
            publication_id (str): The ID of the publication (usually retrieved from get_user_info()).
            page (int, optional): Page index for paginated results. Defaults to 0.

        Returns:
            dict: A dictionary containing a list of post metadata, such as title, slug, and cover image.

        Example:
        {
            "data": {
                "publication": {
                    "posts": [
                        {
                            "title": "...",
                            "slug": "...",
                            "brief": "...",
                            "coverImage": "...",
                            "dateAdded": "..."
                        }
                    ]
                }
            }
        }
        """
        query = """
        query GetPublicationPosts($publicationId: ObjectId!, $page: Int!) {
          publication(id: $publicationId) {
            posts(page: $page) {
              title
              slug
              brief
              coverImage
              dateAdded
            }
          }
        }
        """
        variables = {"publicationId": publication_id, "page": page}
        return await self.client.query(query, variables)

    async def create_post(self, data: CreatePostInput):
        """
        Create a new post in the user's publication.

        Args:
            data (CreatePostInput): A structured data model containing the post's title, content in markdown, optional slug, publication ID, and draft status.

        Returns:
            dict: JSON response containing the newly created post's metadata (ID, title, slug, and date added).

        Required Fields in `data`:
        - title (str)
        - content_markdown (str)
        - publication_id (str)
        - is_draft (bool)
        - slug (str, optional)

        Example:
        CreatePostInput(
            title="My Blog Title",
            content_markdown="## Intro\nThis is a blog.",
            publication_id="pubId123",
            is_draft=True
        )
        """
        query = """
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
        input_data = {
            "title": data.title,
            "contentMarkdown": data.content_markdown,
            "isPartOfPublication": {"publicationId": data.publication_id},
            "isDraft": data.is_draft
        }
        if data.slug:
            input_data["slug"] = data.slug

        return await self.client.query(query, {"input": input_data})

    async def update_post(self, data: UpdatePostInput):
        """
        Update an existing blog post.

        Args:
            data (UpdatePostInput): A structured data model containing the post ID, updated title, and new markdown content.

        Returns:
            dict: JSON response with status code, success flag, and message string.

        Example:
        UpdatePostInput(
            post_id="abc123",
            title="Updated Blog Title",
            content_markdown="## Updated Content"
        )
        """
        query = """
        mutation UpdateStory($input: UpdateStoryInput!) {
          updateStory(input: $input) {
            code
            success
            message
          }
        }
        """
        variables = {"input": data.dict()}
        return await self.client.query(query, variables)



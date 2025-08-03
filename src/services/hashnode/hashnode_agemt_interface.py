# services/agent_commands/hashnode_agent.py
from datetime import datetime
from typing import Optional

from src.services.hashnode.hashnode_client import HashnodeService, CreatePostInput, UpdatePostInput

class HashnodeAgentCommandRegistry:
    """
    HashnodeAgentCommandRegistry

    A command registry designed for AI agents and dynamic systems to interface with the Hashnode blogging service.

    This registry acts as a command-to-function mapping layer that exposes validated, structured operations from the `HashnodeService`.
    It’s intended for use in autonomous systems, chat-based agents, or programmable interfaces that need to query or manipulate blog content on Hashnode.

    ---
    Features:Mobius5627084@

    - Centralized access to available blogging commands.
    - Introspectable for AI agents to dynamically discover callable functions and required input models.
    - Includes method descriptions and schemas for documentation or validation.

    ---
    Typical Usage:
        registry = HashnodeAgentCommandRegistry(service=HashnodeService(token))
        commands = registry.get_commands()
        command_fn = commands["create_post"]["fn"]
        await command_fn(CreatePostInput(...))

    ---
    Notes for AI Systems:
    - This registry is schema-aware. Each command defines its expected input model.
    - Designed to be plugged into a broader agent framework that routes natural language or JSON-based intent to specific service logic.
    """

    def __init__(self, service: HashnodeService):
        """
        Initialize the command registry with a HashnodeService instance.
        Args:
            service (HashnodeService): An instance of the HashnodeService, which handles the actual API interaction logic.
        """
        self.service = service


    async def run_service(self, command_name: str, **kwargs):
        """
        One-line helper that routes a command + kwargs to the correct service call.

        Args:
            command_name (str): Key from `get_commands()`.
            **kwargs: Named arguments matching the command's input_model.

        Returns:
            The raw service response (dict).

        Raises:
            KeyError if command_name is unknown.
            pydantic.ValidationError if kwargs do not match the input_model.
        """
        cmd = self.get_commands()[command_name]
        
        if cmd["input_model"] is None:
            return await cmd["fn"]()
        # Build or validate Pydantic model

        model_cls = cmd["input_model"]
        if isinstance(model_cls, dict):
            # quick dict schema (for list_publication_posts, etc.)
            return await cmd["fn"](**kwargs)
        return await cmd["fn"](model_cls(**kwargs))

    def get_commands(self):
        """
        Retrieve the dictionary of available commands that the Hashnode agent can perform.

        Each command entry maps a command name to a dictionary containing:
        - `fn`: The asynchronous callable function implementing the command.
        - `description`: A human-readable explanation of what the command does.
        - `input_model`: The expected input data model (typically a Pydantic model) defining required and optional parameters.
        ---
        Returns:
            dict[str, dict]: A mapping where keys are command names (str), and values are command metadata dictionaries.
        Example return value structure:
        {
            "get_user_info": {
                "fn": <async function>,
                "description": "Get the current Hashnode user and publication information",
                "input_model": None
            },
            "create_post": {
                "fn": <async function>,
                "description": "Create a new post on Hashnode",
                "input_model": CreatePostInput
            },
            ...
        }

        ---
        Usage:
            commands = registry.get_commands()
            create_post_cmd = commands["create_post"]
            result = await create_post_cmd["fn"](CreatePostInput(...))

        ---
        Notes for AI Agents:
        - Use this method to introspect what operations can be called dynamically.
        - Input models help validate and construct the necessary arguments before invocation.
        """

        return {
            "get_user_info": {
                "fn": self.service.get_user_info,
                "description": "Get the current Hashnode user and publication information",
                "input_model": None,
            },
            "get_all_posts": {
                "fn": self.service.get_all_posts,
                "description": "Fetch all blog posts for a given publication",
                "input_model": {"publication_id": str, "page": int},
            },
            "create_post": {
                "fn": self.service.create_post,
                "description": "Create a new post on Hashnode",
                "input_model": CreatePostInput,
            },
            "update_post": {
                "fn": self.service.update_post,
                "description": "Update an existing post on Hashnode",
                "input_model": UpdatePostInput,
            },
            "get_post": {
                "fn": self.service.get_post,
                "description": "Retrieve a specific post by its ID",
                "input_model": {"publication_id": str, "post_id": str},
            },
            "get_post_analytics": {
                "fn": self.service.get_post_analytics,
                "description": "Get analytics data for a specific post",
                "input_model": {"publication_id": str,"post_id": str},
            },

            "list_publication_posts": {
                "fn": self.service.list_publication_posts,
                "description": "List all posts in a specific publication",
                "input_model": {"publication_id": str, "page": int},
            },
            "delete_post": {
                "fn": self.service.delete_post,
                "description": "Permanently remove a post (irreversible)",
                "input_model": {"post_id": str},
            },
            "publish_draft": {
                "fn": self.service.publish_draft,
                "description": "Turn an existing draft into a live post",
                "input_model": {"post_id": str},
            },
            "unpublish_post": {
                "fn": self.service.unpublish_post,
                "description": "Move a live post back to draft status",
                "input_model": {"post_id": str},
            },
            "add_tags_to_post": {
                "fn": self.service.add_tags_to_post,
                "description": "Append or replace tags on an existing post",
                "input_model": {"post_id": str, "tags": list[str]},
            },
            "schedule_post": {
                "fn": self.service.schedule_post,
                "description": "Schedule a post to go live at a future UTC datetime",
                "input_model": {"post_id": str, "scheduled_at": datetime},
            },
            "create_series": {
                "fn": self.service.create_series,
                "description": "Create or update a Hashnode series (tag-based collection)",
                "input_model": {"name": str, "description": str, "cover_image_url": Optional[str]},
            },
            "add_post_to_series": {
                "fn": self.service.add_post_to_series,
                "description": "Associate an existing post with a series",
                "input_model": {"post_id": str, "series_slug": str},
            },
            "get_series_posts": {
                "fn": self.service.get_series_posts,
                "description": "List all posts inside a specific series",
                "input_model": {"series_slug": str},
            },            
        }


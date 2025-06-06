# services/agent_commands/hashnode_agent.py

from src.services.hashnode.hashnode_client import HashnodeService, CreatePostInput, UpdatePostInput

class HashnodeAgentCommandRegistry:
    """
    HashnodeAgentCommandRegistry

    A command registry designed for AI agents and dynamic systems to interface with the Hashnode blogging service.

    This registry acts as a command-to-function mapping layer that exposes validated, structured operations from the `HashnodeService`.
    It’s intended for use in autonomous systems, chat-based agents, or programmable interfaces that need to query or manipulate blog content on Hashnode.

    ---
    Features:
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

    def get_commands(self):
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
        }


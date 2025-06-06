
import httpx

class HashnodeClient:
    """
    HashnodeClient

    A low-level asynchronous client for communicating with the Hashnode GraphQL API.

    This client is designed to handle raw GraphQL queries and mutations against the Hashnode platform.
    It provides foundational API interaction logic used by higher-level services or AI agents.

    ---
    Usage Context:
    - Meant to be used internally by service layers like `HashnodeService`.
    - Can be directly used by agents for custom GraphQL requests if needed.

    ---
    Requirements:
    - An API token with proper authorization from Hashnode.
    - Internet access (the client sends HTTP requests to https://gql.hashnode.com/).
    - Async runtime (i.e., must be called inside an `async` context).

    ---
    Attributes:
    - token (str): The Hashnode API token used for authenticating all requests.
    - endpoint (str): The fixed URL for Hashnode’s GraphQL API endpoint.

    ---
    Methods:
    - async query(query: str, variables: dict = None) -> dict:
        Sends a GraphQL query or mutation to Hashnode.
        Returns the parsed JSON response.

    ---
    Example:
        client = HashnodeClient(token="your-token")
        response = await client.query(query="...", variables={"foo": "bar"})

    ---
    Notes for AI Agents:
    - You can safely use this class to send custom GraphQL operations to Hashnode.
    - Always validate or sanitize `query` and `variables` inputs to ensure compatibility with the Hashnode schema.
    - It is advised to use higher-level wrappers (e.g. `HashnodeService`) for predefined, schema-safe operations.
    """

    def __init__(self, token: str):
        self.token = token
        self.endpoint = "https://gql.hashnode.com/"

    async def query(self, query: str, variables: dict = None):
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": self.token,
                "Content-Type": "application/json"
            }
            response = await client.post(self.endpoint, headers=headers, json={"query": query, "variables": variables})
            response.raise_for_status()
            return response.json()

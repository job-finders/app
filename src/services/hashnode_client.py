# services/hashnode_client.py
import httpx

class HashnodeClient:
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

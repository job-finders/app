# agents/blog/reader_agent.py
from src.agents.base import BaseAgent
from services.hashnode.hashnode_client import HashnodeClient

class BlogPostReaderAgent(BaseAgent):
    async def run(self):
        query = """
        query {
          me {
            publication {
              posts(page: 0) {
                title
                brief
                slug
                dateAdded
              }
            }
          }
        }
        """
        client = HashnodeClient(token=self.hashnode_token)
        data = await client.query(query)
        return data["data"]["me"]["publication"]["posts"]

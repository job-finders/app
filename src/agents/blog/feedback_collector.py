# agents/blog/feedback_collector.py
from src.agents.base import BaseAgent
from src.services.hashnode_client import HashnodeClient

class FeedbackCollector(BaseAgent):
    async def run(self):
        query = """
        query {
          me {
            publication {
              posts(page: 0) {
                title
                views
                totalReactions
              }
            }
          }
        }
        """
        client = HashnodeClient(token="HASHNODE_API_TOKEN")
        data = await client.query(query)
        return data["data"]["me"]["publication"]["posts"]

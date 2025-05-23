# agents/blog/post_submitter_agent.py
from src.agents.base import BaseAgent
from src.services.hashnode_client import HashnodeClient
from pydantic import BaseModel

class BlogPostSubmitterAgent(BaseAgent):
    async def run(self, article):
        mutation = """
        mutation CreateStory($input: CreateStoryInput!) {
          createPublicationStory(input: $input) {
            post {
              slug
              title
            }
          }
        }
        """
        input_data = {
            "input": {
                "title": article.title,
                "contentMarkdown": article.content,
                "coverImageURL": article.cover_image_url or "",
                "publicationId": "YOUR_PUBLICATION_ID"
            }
        }
        client = HashnodeClient(token="HASHNODE_API_TOKEN")
        await client.query(mutation, variables=input_data)

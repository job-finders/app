"""
Thin re-export so agents never import from services directly.
"""
from src.config import config_instance
from src.services.hashnode import HashnodeAgentCommandRegistry, HashnodeService

config = config_instance()
_HASHNODE_PAT        = config.HASHNODE_BLOG.HASHNODE_TOKEN
_HASHNODE_PUB_ID     = config.HASHNODE_BLOG.BLOG_ID

service = HashnodeService(token=_HASHNODE_PAT, publication_id=_HASHNODE_PUB_ID)

# singleton ready for async use
hashnode = HashnodeAgentCommandRegistry(service=service)

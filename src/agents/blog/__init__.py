
# src/agents/__init__.py
from .blog.agent import (
    TopicDiscoveryAgent,
    ArticlePlannerAgent,
    PerformanceMonitorAgent,
    RefinerAgent,
)

__all__ = [
    "TopicDiscoveryAgent",
    "ArticlePlannerAgent",
    "PerformanceMonitorAgent",
    "RefinerAgent",
    # ... existing employer agents
]

import os
ENABLED = os.getenv("BLOG_AGENTS_V2", "false").lower() in {"true", "1"}

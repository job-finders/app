import argparse
import asyncio
from .agent import TopicDiscoveryAgent, ArticlePlannerAgent, PerformanceMonitorAgent, RefinerAgent

async def loop():
    """Demo loop: discover → plan → (fake) metrics → refine."""
    td = TopicDiscoveryAgent()
    ap = ArticlePlannerAgent()
    pm = PerformanceMonitorAgent()
    rf = RefinerAgent()

    # Stub site-map
    site_map = {"tech": ["python-jobs", "remote-dev"], "marketing": ["seo-roles"]}
    topics = await td.run(site_map)
    for topic in topics:
        outline = await ap.run(topic)
        metrics = await pm.run(outline.slug)
        await rf.run(metrics)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["loop"], required=True)
    args = parser.parse_args()
    asyncio.run(loop())

if __name__ == "__main__":
    main()
    
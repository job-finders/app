# agents/blog/strategy_refiner.py
from src.agents.base import BaseAgent

class StrategyRefiner(BaseAgent):
    async def run(self, feedback):
        # This is placeholder logic: filter for low-performing topics and adjust prompt generation
        underperforming = [f for f in feedback if f["views"] < 100]
        # Log, store, or retrain based on performance
        if underperforming:
            print(f"Underperforming: {[p['title'] for p in underperforming]}")
        return {"status": "refined"}

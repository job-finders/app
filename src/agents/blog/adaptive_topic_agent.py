# /agents/adaptive_topic_agent.py

from src.agents.blog.topic_suggestion_agent import generate_new_topics
from src.agents.blog.feedback_agent import analyze_feedback


def enhance_prompt_strategy():
    feedback = analyze_feedback()
    base_prompts = generate_new_topics()

    enhanced_prompts = feedback.new_prompt_ideas + base_prompts
    return list(set(enhanced_prompts))[:10]  # Top 10 de-duplicated prompts

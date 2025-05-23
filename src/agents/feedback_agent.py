# /agents/feedback_agent.py

from src.database.models.feedback_analysis import FeedbackAnalysisSummary, ArticleFeedbackEntry
from collections import defaultdict

def analyze_feedback() -> FeedbackAnalysisSummary:
    entries = db_session.query(BlogFeedbackORM).all()
    if not entries:
        return FeedbackAnalysisSummary(
            high_performing_topics=[], underperforming_topics=[],
            average_score=0.0, insights=[], new_prompt_ideas=[]
        )

    topic_scores = defaultdict(list)
    all_scores = []

    # Simulated topic mapping (normally via DB/article metadata)
    article_topic_map = {
        "article1": "Job Interview Tips",
        "article2": "Remote Work Trends",
        "article3": "CV Optimization",
        # etc.
    }

    for entry in entries:
        topic = article_topic_map.get(entry.article_id, "General")
        topic_scores[topic].append(entry.feedback_score)
        all_scores.append(entry.feedback_score)

    # Calculate insights
    avg_score = sum(all_scores) / len(all_scores)
    high_performing = []
    underperforming = []
    insights = []
    prompts = []

    for topic, scores in topic_scores.items():
        topic_avg = sum(scores) / len(scores)
        if topic_avg >= 8:
            high_performing.append(topic)
            prompts.append(f"Expand on {topic}")
        elif topic_avg <= 4:
            underperforming.append(topic)
            insights.append(f"Topic '{topic}' underperformed, consider avoiding or improving clarity.")

    return FeedbackAnalysisSummary(
        high_performing_topics=high_performing,
        underperforming_topics=underperforming,
        average_score=avg_score,
        insights=insights,
        new_prompt_ideas=prompts
    )

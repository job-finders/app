# routes/cron_routes.py

from flask import Blueprint, jsonify
from agents.blog.reader_agent import BlogPostReaderAgent
from agents.blog.gap_analyzer_agent import GapAnalyzerAgent
from agents.blog.article_creator_agent import ArticleCreatorAgent
from agents.blog.post_submitter_agent import BlogPostSubmitterAgent
from agents.blog.feedback_collector import FeedbackCollector
from agents.blog.strategy_refiner import StrategyRefiner

cron_bp = Blueprint("cron", __name__, url_prefix="/_cron/api/v1")

@cron_bp.route("/create-article", methods=["GET"])
async def create_article_pipeline():
    existing_posts = await BlogPostReaderAgent().run()
    content_gaps = await GapAnalyzerAgent().run(existing_posts)

    for topic in content_gaps.suggested_topics:
        for prompt in topic.prompts:
            article = await ArticleCreatorAgent().run(prompt=prompt, topic=topic.title)
            await BlogPostSubmitterAgent().run(article)

    feedback_data = await FeedbackCollector().run()
    await StrategyRefiner().run(feedback_data)

    return jsonify({"status": "Blog automation executed successfully"})

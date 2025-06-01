import requests
from flask import Blueprint, jsonify
from flask import url_for

from src.agents.blog.article_creator_agent import ArticleCreatorAgent
from src.agents.blog.feedback_collector import FeedbackCollector
from src.agents.blog.gap_analyzer_agent import GapAnalyzerAgent
from src.agents.blog.post_submitter_agent import BlogPostSubmitterAgent
from src.agents.blog.reader_agent import BlogPostReaderAgent
from src.agents.blog.strategy_refiner import StrategyRefiner
from src.logger import init_logger
from src.routes.seo_routes.seo import get_site_job_links

cron_route = Blueprint('cron', __name__, url_prefix='/_cron')
cron_logger = init_logger()


def ping_indexnow(url_list: list[str], key: str, key_location: str):
    payload = {
        "host": "jobfinders.site",
        "urlList": url_list,
        "key": key,
        "keyLocation": key_location
    }
    try:
        r = requests.post("https://api.indexnow.org/indexnow", json=payload, timeout=10)
        return {'indexnow': r.status_code}
    except Exception as e:
        return {'indexnow': str(e)}


@cron_route.get('/ping-index-now')
async def cron_ping_index_now():
    """
    https://jobfinders.site/_cron/ping-index-now

    :return:
    """
    key='3554e950877947b59633174a3c18e6b3'
    jobs_links = await get_site_job_links()
    cron_logger.info(jobs_links)
    result = ping_indexnow(url_list=jobs_links, key=key, key_location=url_for('seo.get_indexnow_key', _external=True))
    return result

@cron_route.get('/scrape-junction')
async def scrape_junction():
    """sumary_line
        Need to Actual scrape online for jobs     
        Keyword arguments:
        argument -- description
        Return: return_description
    """
    pass

@cron_route.route("/create-article", methods=["GET"])
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

# @cron_route.route("/_cron/adapt-blog-strategy", methods=["GET"])
# def adapt_blog_strategy():
#     prompts = enhance_prompt_strategy()
#     return {"next_prompts": prompts}

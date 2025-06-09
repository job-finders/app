from flask import Blueprint, render_template

from src.database.models.users import User
from src.authentication import user_details
from src.cache.cache_redis import cached
from src.routes import flask_error_handler
from src.database.models.seo import create_tags
from src.logger import init_logger

blog_route = Blueprint('blog', __name__)
blog_logger = init_logger()


@blog_route.get('/blog')
@flask_error_handler
@user_details
@cached(ttl=60*60*6)
async def blog_home(user: User):
    search_term, template_path = ("Jobfinders Blog Articles", "blog/blog.html")
    seo = await create_tags(search_term=search_term)
    context = dict(curremt_user=user, seo=seo, term=search_term)
    return render_template(template_path, **context)


@blog_route.get('/blog/<string:topic>')
@flask_error_handler
@user_details
@cached(ttl=60*60*6)
async def get_blog(user: User, topic: str):
    """
    will return blog for the specified topic
    :param user:
    :param topic: The topic of the blog
    :return: The rendered template for the specified topic
    """
    # Define a dictionary to map topics to search terms and template paths
    topic_mappings = {
        "index": ("Jobfinders Blog Articles", "blog/blog.html"),
        "resume-writing-tips": ("Resume Writing Tips", "blog/resume/index.html"),
        "job-search-strategies": ("Job Search Strategies", "blog/job_search/index.html"),
        "mastering-networking": ("Mastering Networking", "blog/job_search/mastering_networking.html"),
        "interview-strategies": ("Interview Strategies", "blog/interview/index.html"),
        "remote-work-freelancing": ("Remote Work and Freelancing", "blog/freelancing/index.html"),
        "job-application-tips": ("Job Application Tips", "blog/job_application/index.html"),
        "workplace-tips": ("Workplace Tips", "blog/workplace_tips/index.html"),
        "job-market-research": ("Job Market Research", "blog/job_market/index.html"),
        "career": ("Navigating Career Change", "blog/job_market/strategies_for_smooth_change.html"),
        "digital-branding": ("Personal Branding", "blog/job_market/building_personal_brand.html"),
        "education": ("Education and Training", "blog/education/index.html"),

    }

    if topic in topic_mappings:
        search_term, template_path = topic_mappings[topic]
        seo = await create_tags(search_term=search_term)
        context = dict(curremt_user=user,seo=seo, term=search_term)
        return render_template(template_path, **context)
    else:
        # Handle invalid topic here, e.g., return a 404 page
        error = dict(title="Error Page not Found", message="Error finding that blog page")
        return render_template("error.html")

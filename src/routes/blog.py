from flask import Blueprint, render_template, send_from_directory

from src.database.models.seo import create_tags
from src.database.models import Job, SEO
from src.logger import init_logger
from src.main import scrapper
from src.utils import static_folder, format_title

blog_route = Blueprint('blog', __name__)
blog_logger = init_logger()


@blog_route.get('/blog')
async def get_blog():
    """
        will return blog
    :return:
    """
    seo = create_tags(search_term="Blog")
    context = dict(seo=seo, term="blog")
    return render_template("blog/blog.html", **context)


@blog_route.get('/blog/resume-writing-tips')
async def resume_writing_tips():
    seo = create_tags(search_term="Resume Writing Tips")
    context = dict(seo=seo, term="Resume Writing Tips")
    return render_template("blog/resume/resume_writing_tips.html", **context)


@blog_route.get('/blog/job-search-strategies')
async def job_search_strategies():
    seo = create_tags(search_term="Job Search Strategies")
    context = dict(seo=seo, term="Job Search Strategies")
    return render_template("blog/job_search/index.html", **context)


@blog_route.get('/blog/interview-strategies')
async def interview_strategies():
    seo = create_tags(search_term="Interview Strategies")
    context = dict(seo=seo, term="Interview Strategies")
    return render_template("blog/interview/index.html", **context)


@blog_route.get('/blog/remote-work-freelancing')
async def freelancing():
    seo = create_tags(search_term="Remote Work and Freelancing")
    context = dict(seo=seo, term="Remote Work and Freelancing")
    return render_template("blog/freelancing/index.html", **context)

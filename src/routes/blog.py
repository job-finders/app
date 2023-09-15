from flask import Blueprint, render_template

from src.database.models.seo import create_tags
from src.logger import init_logger

blog_route = Blueprint('blog', __name__)
blog_logger = init_logger()


@blog_route.get('/blog')
async def blog_home():
    search_term, template_path = ("Jobfinders Blog Articles", "blog/blog.html")
    seo = await create_tags(search_term=search_term)
    context = dict(seo=seo, term=search_term)
    return render_template(template_path, **context)


@blog_route.get('/blog/<string:topic>')
async def get_blog(topic):
    """
    will return blog for the specified topic
    :param topic: The topic of the blog
    :return: The rendered template for the specified topic
    """
    # Define a dictionary to map topics to search terms and template paths
    topic_mappings = {
        "index": ("Jobfinders Blog Articles", "blog/blog.html"),
        "resume-writing-tips": ("Resume Writing Tips", "blog/resume/index.html"),
        "job-search-strategies": ("Job Search Strategies", "blog/job_search/index.html"),
        "interview-strategies": ("Interview Strategies", "blog/interview/index.html"),
        "remote-work-freelancing": ("Remote Work and Freelancing", "blog/freelancing/index.html"),
        "job-application-tips": ("Job Application Tips", "blog/job_application/index.html"),
        "workplace-tips": ("Workplace Tips", "blog/workplace_tips/index.html"),
        "job-market-research": ("Job Market Research", "blog/job_market/index.html"),
        "education": ("Education and Training", "blog/education/index.html"),
    }

    if topic in topic_mappings:
        search_term, template_path = topic_mappings[topic]
        seo = await create_tags(search_term=search_term)
        context = dict(seo=seo, term=search_term)
        return render_template(template_path, **context)

    # Handle invalid topic here, e.g., return a 404 page
    error = dict(title="Error Page not Found", message="Error finding that blog page")
    context = dict(error=error)
    return render_template("error.html", **context)


@blog_route.get("/blog/resume-templates/<string:template_name>")
async def get_resume_template(template_name: str):
    """
        resume templates here
    :param template_name:
    :return:
    """
    if template_name == "developer":
        return render_template("blog/resume/software_developer_resume.html")
    elif template_name == "marketing":
        return render_template("blog/resume/marketing_manager_resume.html")
    elif template_name == "classic":
        return render_template("blog/resume/classic_resume.html")
    elif template_name == "creative":
        return render_template("blog/resume/creative_resume.html")

    error = dict(title="Error Page not Found", message="Error Resume Template not found")
    context = dict(error=error)
    return render_template("error.html", **context)


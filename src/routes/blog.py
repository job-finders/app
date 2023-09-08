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


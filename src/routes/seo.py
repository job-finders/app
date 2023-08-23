from flask import Blueprint, render_template, send_from_directory

from src.database.models.jobs import Job
from src.main import junction_scrapper
from src.utils import static_folder

seo_route = Blueprint('seo', __name__)


@seo_route.get('/sitemap.xml')
async def sitemap():
    """

    :return:
    """
    return send_from_directory(static_folder(), 'sitemap.xml')


@seo_route.get('/robots.txt')
async def robots():
    return send_from_directory(static_folder(), 'robots.txt')

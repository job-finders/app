from flask import Blueprint, render_template, send_from_directory

from src.database.models import Job, SEO
from src.logger import init_logger
from src.main import scrapper
from src.utils import static_folder, format_title

jobs_route = Blueprint('jobs', __name__)
jobs_logger = init_logger("jobs_logger")


@jobs_route.get('/similar-jobs/<string:search_term>/<string:title>')
async def similar_jobs(search_term: str, title: str):
    """

    :param search_term:
    :param title:
    :return:
    """
    jobs_list: list[Job] = await scrapper.similar_jobs(search_term=search_term, title=title)
    return jobs_list

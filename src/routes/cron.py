from flask import Blueprint, render_template, send_from_directory

from src.database.models import Job, SEO
from src.logger import init_logger
from src.main import scrapper
from src.utils import static_folder, format_title

cron_route = Blueprint('cron', __name__)
cron_logger = init_logger()


@cron_route.get('/_cron/jobs/')
async def cron_jobs():
    """

    :return:
    """
    pass



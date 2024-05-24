from flask import Blueprint

from src.logger import init_logger

cron_route = Blueprint('cron', __name__)
cron_logger = init_logger()


@cron_route.get('/_cron/jobs/')
async def cron_jobs():
    """

    :return:
    """
    pass



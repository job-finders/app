import requests
from flask import Blueprint, url_for

from src.routes.seo import get_site_job_links
from src.logger import init_logger

cron_route = Blueprint('cron', __name__)
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


@cron_route.get('/_cron/ping-index-now')
async def cron_ping_index_now():
    """

    :return:
    """
    key='3QxfFYZbaazjresnuK8uY5YHRp561rVc95'
    jobs_links = await get_site_job_links()
    result = ping_indexnow(url_list=jobs_links, key=key, key_location=url_for('seo.get_indexnow_key', _external=True))
    return result



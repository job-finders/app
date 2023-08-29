from functools import lru_cache
from flask import Blueprint, render_template, send_from_directory, url_for
from src.main import junction_scrapper, scrapper
from src.utils import static_folder

seo_route = Blueprint('seo', __name__)


async def get_site_job_links() -> list[str]:
    """
    :return:
    """
    links = []
    for job in scrapper.jobs.values():
        links.append(url_for('home.job_detail', _external=True, reference=job.job_ref))
    return links


@seo_route.get('/sitemap.xml')
async def sitemap():
    """

    :return:
    """
    return send_from_directory(static_folder(), 'sitemap.xml')


@seo_route.get("/jobs/sitemap.xml")
async def get_jobs_sitemap():
    """

    :return:
    """
    sitemap_urls = await get_site_job_links()
    context = dict(sitemap_urls=sitemap_urls)
    return render_template("sitemap.xml", **context)


@seo_route.get('/robots.txt')
async def robots():
    return send_from_directory(static_folder(), 'robots.txt')

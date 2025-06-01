
from flask import Blueprint, render_template, send_from_directory, url_for, make_response

from src.main import junction_scrapper
from src.utils import static_folder

seo_route = Blueprint('seo', __name__)


async def get_site_job_links() -> list[str]:
    """
    :return:
    """
    links = []
    for job in junction_scrapper.jobs.values():
        links.append(url_for('jobs.job_slug', _external=True, slug=job.slug))
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
    # TODO ocnsider rending sitemaps for categories and others
    sitemap_urls = await get_site_job_links()
    context = dict(sitemap_urls=sitemap_urls)
    xml_content = render_template("sitemap.xml", **context)
    response = make_response(xml_content)
    response.headers["Content-Type"] = "application/xml"
    return response

@seo_route.get('/lims.txt')
async def lims():
    return send_from_directory(static_folder(), 'lims.txt')


@seo_route.get('/robots.txt')
async def robots():
    return send_from_directory(static_folder(), 'robots.txt')


@seo_route.get("/Ads.txt")
async def ads_txt():
    return send_from_directory(static_folder(), 'ads.txt')


@seo_route.get("/ads.txt")
async def adstxt():
    return send_from_directory(static_folder(), 'ads.txt')


@seo_route.get("/ai-crawlers-info")
async def get_ai_crawlers_info():
    """
    Serve the AI-Crawlers Info page from the static folder.
    """
    # current_app.static_folder points to your configured static directory
    return send_from_directory(static_folder(), 'crawlers.MD')

@seo_route.get('/3554e950877947b59633174a3c18e6b3.txt')
async def get_indexnow_key():
    """
        index now endpoint
    :return:
    """
    return send_from_directory(static_folder(), '3554e950877947b59633174a3c18e6b3.txt')

from flask import Blueprint, render_template, send_from_directory

from src.main import junction_scrapper
from src.scrappers import default_jobs

home_route = Blueprint('home', __name__)


@home_route.get('/')
async def get_home():
    job_list = await junction_scrapper.scrape("information-technology")
    search_terms = default_jobs
    context = dict(term="information-technology", job_list=job_list, search_terms=search_terms)
    return render_template('index.html', **context)


@home_route.get('/jobs/<string:search_term>')
async def job_search(search_term: str):
    job_list = await junction_scrapper.scrape(term=search_term)
    search_terms = default_jobs
    context = dict(term=search_term, job_list=job_list, search_terms=search_terms)
    return render_template('index.html', **context)


@home_route.get('/job/<string:reference>')
async def job_detail(reference: str):
    job = await junction_scrapper.job_search(job_reference=reference)
    context = dict(job=job)
    return render_template('job.html', **context)

from flask import Blueprint, render_template, send_from_directory

from src.database.models.jobs import Job
from src.main import junction_scrapper

home_route = Blueprint('home', __name__)


async def create_context(search_term):
    """
        will create common context for jobs
    :param search_term:
    :return:
    """
    job_list = await junction_scrapper.scrape(term=search_term)
    search_terms: list[str] = junction_scrapper.default_jobs

    current_index: int = search_terms.index(search_term)
    previous_term: str = search_terms[current_index - 1] if current_index > 0 else search_terms[len(search_terms) - 1]
    next_term: str = search_terms[current_index + 1] if current_index < len(search_terms) - 1 else search_terms[0]

    context = dict(term=search_term, previous_term=previous_term, next_term=next_term,
                   job_list=job_list, search_terms=search_terms)

    return render_template('index.html', **context)


@home_route.get('/')
async def get_home():
    """
        home directory will start with information tech jobs
    :return:
    """
    search_term = "information-technology"
    return await create_context(search_term)


@home_route.get('/jobs/<string:search_term>')
async def job_search(search_term: str):
    return await create_context(search_term)


@home_route.get('/job/<string:reference>')
async def job_detail(reference: str):
    job: Job = await junction_scrapper.job_search(job_reference=reference)
    term = job.title
    context = dict(term=term, job=job, search_terms=junction_scrapper.default_jobs)
    return render_template('job.html', **context)


@home_route.get('/sw-check-permissions-a0d20.js')
async def get_pro_push_code():
    """

    6244766
    will serve pro push code from static folder
    :return:
    """
    return send_from_directory('static', 'sw-check-permissions-a0d20.js')

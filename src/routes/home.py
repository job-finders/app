from flask import Blueprint, render_template, send_from_directory

from src.logger import init_logger
from src.database.models import Job, SEO
from src.main import junction_scrapper, scrapper
from src.utils import static_folder, format_title

home_route = Blueprint('home', __name__)
home_logger = init_logger()


async def create_tags(search_term: str) -> SEO:
    """

    :param search_term:
    :return:
    """
    title = f"{search_term} Jobs"
    description = f"jobfinders.site {search_term} Jobs"
    term_words = ",".join(format_title(search_term).split(" "))
    keywords = f"JobFinders, {term_words}"
    seo_dict = dict(title=title, description=description, keywords=keywords)
    return SEO(**seo_dict)


async def create_context(search_term: str):
    """
        will create common context for jobs
    :param search_term:
    :return:
    """
    if search_term not in scrapper.search_terms:
        # TODO - return an error here preferably with an error page
        return None

    job_list = [job for job in scrapper.jobs.values() if job.search_term.casefold() == search_term.casefold()]

    search_terms: list[str] = scrapper.search_terms

    seo = await create_tags(search_term=search_term)
    current_index: int = search_terms.index(search_term)
    previous_term: str = search_terms[current_index - 1] if current_index > 0 else search_terms[len(search_terms) - 1]
    next_term: str = search_terms[current_index + 1] if current_index < len(search_terms) - 1 else search_terms[0]

    context = dict(term=search_term, previous_term=previous_term, next_term=next_term,
                   job_list=job_list, search_terms=search_terms, seo=seo)

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
    job: Job = await scrapper.job_search(job_reference=reference)
    term = job.title
    seo = await create_tags(search_term=term)
    context = dict(term=term, job=job, search_terms=scrapper.search_terms, seo=seo)
    return render_template('job.html', **context)


@home_route.get('/sw-check-permissions-a0d20.js')
async def get_pro_push_code():
    """
        will serve pro push code from static folder
    :return:
    """
    return send_from_directory(static_folder(), 'js/sw-check-permissions-a0d20.js')


@home_route.get('/about')
async def about():
    """
    :return:
    """
    seo = await create_tags(search_term="about")
    context = dict(seo=seo, term="about")
    return render_template('about.html', **context)


@home_route.get('/contact')
async def contact():
    """
    :return:
    """
    seo = await create_tags(search_term="contact")
    context = dict(seo=seo, term="contact")
    return render_template('contact.html', **context)


@home_route.get('/terms')
async def terms():
    """
    :return:
    """
    seo = await create_tags(search_term="terms")
    context = dict(seo=seo, term="terms")
    return render_template('terms.html', **context)


@home_route.get('/sister-sites')
async def sister_sites():
    """
    :return:
    """
    seo = await create_tags(search_term="sister-sites")
    context = dict(seo=seo, term="sister-sites")
    return render_template('sisters.html', **context)


@home_route.get('/faq')
async def faq():
    """
    :return:
    """
    seo = await create_tags(search_term="FAQ")
    context = dict(seo=seo, term="FAQ")
    return render_template('faq.html', **context)

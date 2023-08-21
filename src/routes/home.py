from flask import Blueprint, render_template, send_from_directory
from src.main import junction_scrapper

home_route = Blueprint('home', __name__)


@home_route.get('/')
async def get_home():
    job_list = await junction_scrapper.scrape("information-technology")
    print(job_list)
    context = dict(term="information-technology", job_list=job_list)
    return render_template('index.html', **context)


@home_route.get('/jobs/<string:search_term>')
async def job_search(search_term: str):
    job_list = await junction_scrapper.scrape(term=search_term)
    print(f'search term: {search_term}')
    print(job_list)
    context = dict(term=search_term, job_list=job_list)
    return render_template('index.html', **context)

from flask import Blueprint, render_template, request, redirect, url_for

from src.routes import flask_error_handler
from src.database.models import Job
from src.main import scrapper
from src.routes.utils import (create_common_context, not_found, gone, TOWN_TO_PROVINCE, create_search_context,
                              sub_job_detail)

jobs_route = Blueprint('jobs', __name__)

# Route Definitions

@jobs_route.get('/jobs-in/<string:location>')
@flask_error_handler
async def jobs_by_location(location: str):
    """
    Handles jobs by province or town.
    If the location is a known town, replace it with its parent province for consistent filtering.
    """

    page = int(request.args.get('page', 1))
    location_lower = location.lower()

    # If user typed a town, convert to province
    if location_lower in TOWN_TO_PROVINCE:
        province = TOWN_TO_PROVINCE[location_lower]
    else:
        province = location  # Assume it's already a province or partial match

    jobs_filtered = [
        job for job in scrapper.jobs.values()
        if job.location and province.lower() in job.location.lower()
    ]

    if not jobs_filtered:
        return await not_found(location)

    # Slug for SEO
    search_term = f"jobs-in-{location_lower.replace(' ', '-')}"

    context = await create_common_context(
        search_term=search_term,
        job_list=jobs_filtered,
        page=page,
        per_page=10
    )

    return render_template('location.html', **context)


@jobs_route.get('/jobs/category/<string:category>')
@flask_error_handler
async def category_jobs(category: str):
    """Render job search results by search term."""
    page = int(request.args.get('page', 1))
    response = await create_search_context(search_term=category, page=page)
    if response is None:
        return await not_found(category)
    return response


@jobs_route.get('/jobs/<string:search_term>')
@flask_error_handler
async def job_search(search_term: str):
    """Render job search results by search term."""
    page = int(request.args.get('page', 1))
    response = await create_search_context(search_term=search_term, page=page)
    if response is None:
        return await not_found(search_term)
    return response


@jobs_route.get('/search')
@flask_error_handler
async def search_bar():
    """Render search results from a query submitted via search bar."""
    search_term = request.args.get('search_term')
    if not search_term:
        return redirect(url_for('home.get_home'), code=302)
    page = int(request.args.get('page', 1))
    response = await create_search_context(search_term=search_term, page=page)
    if response is None:
        return await not_found(search_term)
    return response


@jobs_route.get('/job/<string:reference>')
@flask_error_handler
async def job_detail(reference: str):
    """Display job details identified by job reference."""
    job: Job = await scrapper.job_search(job_reference=reference)
    if isinstance(job, Job) and job.title.strip():
        return await sub_job_detail(job)
    return await gone(search_term=reference)

@jobs_route.get('/search/job/<string:slug>')
@flask_error_handler
async def job_slug(slug: str):
    """Display job details identified by its slug."""
    job: Job = await scrapper.search_by_slug(slug=slug)
    if isinstance(job, Job) and job.title.strip():
        return await sub_job_detail(job)
    return await gone(search_term=slug)

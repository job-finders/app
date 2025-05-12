from flask import Blueprint, render_template, request, redirect, url_for

from src.authentication import user_details, admin_login
from src.database.models import Job, Role
from src.database.models.users import User
from src.main import scrapper, jobs_controller
from src.routes import flask_error_handler
from src.routes.utils import (create_common_context, not_found, gone, TOWN_TO_PROVINCE, create_search_context,
                              sub_job_detail)

jobs_route = Blueprint('jobs', __name__)

# Route Definitions

@jobs_route.get('/jobs-in/<string:location>')
@flask_error_handler
@user_details
async def jobs_by_location(user: User,location: str):
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
    context.update(current_user=user)

    return render_template('location.html', **context)


@jobs_route.get('/jobs/category/<string:category>')
@flask_error_handler
@user_details
async def category_jobs(user: User,category: str):
    """Render job search results by search term."""
    page = int(request.args.get('page', 1))
    response = await create_search_context(user=user, search_term=category, page=page)
    if response is None:
        return await not_found(category)
    return response


@jobs_route.get('/jobs/<string:search_term>')
@flask_error_handler
@user_details
async def job_search(user: User,search_term: str):
    """Render job search results by search term."""
    page = int(request.args.get('page', 1))
    response = await create_search_context(user=user, search_term=search_term, page=page)
    if response is None:
        return await not_found(search_term)
    return response


@jobs_route.get('/search')
@flask_error_handler
@user_details
async def search_bar(user: User):
    """Render search results from a query submitted via search bar."""
    search_term = request.args.get('search_term')
    if not search_term:
        return redirect(url_for('home.get_home'), code=302)
    page = int(request.args.get('page', 1))
    response = await create_search_context(user=user, search_term=search_term, page=page)
    if response is None:
        return await not_found(search_term)
    return response


@jobs_route.get('/job/<string:reference>')
@flask_error_handler
@user_details
async def job_detail(user: User, reference: str):
    """Display job details identified by job reference."""
    if user and user.role == Role.SEEKER:
        # Obtain Job Seeker Resume
        pass

    job: Job = await scrapper.job_search(job_reference=reference)

    if isinstance(job, Job) and job.title.strip():
        return await sub_job_detail(user=user, job=job)
    return await gone(user=user, search_term=reference)

@jobs_route.get('/search/job/<string:slug>')
@flask_error_handler
@user_details
async def job_slug(user: User,slug: str):
    """Display job details identified by its slug."""
    job: Job = await scrapper.search_by_slug(slug=slug)
    if isinstance(job, Job) and job.title.strip():
        return await sub_job_detail(user=user, job=job)
    return await gone(search_term=slug)


@jobs_route.get('/jobs/categories')
@flask_error_handler
@user_details
async def categories(user: User):
    pass


@jobs_route.get('/jobs/ai-based-search')
@flask_error_handler
@user_details
async def assisted_search(user: User):
    pass


@jobs_route.get('/jobs/approve-job/<string:approval_token>')
@flask_error_handler
@admin_login
async def approve_job(user: User, approval_token: str):
    """
    Approves a job posting using the provided approval token.

    :param user: The admin user performing the approval.
    :param approval_token: Unique token to identify the job awaiting approval.
    :return: A success or failure message.
    """
    # TODO - ensure there is a place to enter feedback for the approval or rejection

    result = await jobs_controller.approve_method(approval_token, approver=user)

    if result.success:
        return render_template("admin/job_approval_success.html", job=result.data)
    else:
        return render_template("admin/job_approval_error.html", message=result.message), 400


@jobs_route.get('/jobs/reject-job/<string:approval_token>')
@flask_error_handler
@admin_login
async def reject_job(user: User, approval_token: str):
    """
    Rejects a job posting using the provided approval token.

    :param user: The admin user performing the rejection.
    :param approval_token: Unique token to identify the job awaiting rejection.
    :return: A success or failure message.
    """
    result = await jobs_controller.reject_method(approval_token, rejector=user)

    if result.success:
        return render_template("admin/job_rejection_success.html", job=result.data)
    else:
        return render_template("admin/job_approval_error.html", message=result.message), 400


from flask import Blueprint, render_template, request, redirect, url_for

from src.routes.utils import gone
from src.authentication import user_details, login_required, admin_login
from src.routes import flask_error_handler
from src.main import jobs_controller
from src.database.models.users import User

# Blueprint definition
jobs_route = Blueprint('jobs', __name__, url_prefix='/jobs')

@jobs_route.get('/')
@flask_error_handler
@user_details
async def list_jobs(user: User):
    """
    Display a paginated list of all available jobs.

    This route fetches all published jobs from the database using the jobs controller,
    paginates the results based on the 'page' query parameter, and renders them
    using the `jobs/list.html` template.

    Args:
        user (User): The currently authenticated user.

    Returns:
        HTML template rendering the job listings.

    Example:
        GET /jobs?page=2
    """
    page = int(request.args.get('page', 1))
    jobs = await jobs_controller.get_all_jobs(page)
    context = {
        'jobs': jobs,
        'page': page,
        'per_page': 10,
        'total_jobs': await jobs_controller.get_total_jobs(),
    }
    return render_template('jobs/list.html', **context)


@jobs_route.get('/search')
@flask_error_handler
@user_details
async def search_jobs(user: User):
    """
    Search for jobs by keyword.

    This route retrieves job listings filtered by the given 'keyword' query parameter.
    It supports pagination and renders the results using the `jobs/search.html` template.

    Args:
        user (User): The currently authenticated user.

    Returns:
        HTML template with search results.

    Example:
        GET /jobs/search?keyword=engineer&page=1
    """
    keyword = request.args.get('keyword', '')
    page = int(request.args.get('page', 1))
    jobs = await jobs_controller.search_jobs(keyword, page)
    context = {
        'jobs': jobs,
        'page': page,
        'per_page': 10,
        'total_jobs': await jobs_controller.get_total_jobs(),
        'search_keyword': keyword,
    }
    return render_template('jobs/search.html', **context)


@jobs_route.get('/<string:job_id>')
@flask_error_handler
@user_details
async def job_details(user: User, job_id: str):
    """
    Display details for a specific job.

    Retrieves job details by `job_id` and displays them via the `jobs/detail.html` template.
    If the job is not found, renders a 'gone' page.

    Args:
        user (User): The authenticated user.
        job_id (str): The unique identifier of the job.

    Returns:
        HTML page with job details or a 'job not found' page.

    Example:
        GET /jobs/123e4567-e89b-12d3-a456-426614174000
    """
    job = await jobs_controller.get_job_by_id(job_id)
    if not job:
        return await gone(search_term=job_id)
    context = {'job': job}
    return render_template('jobs/detail.html', **context)


@jobs_route.post('/save/<string:job_id>')
@flask_error_handler
@user_details
async def save_job(user: User, job_id: str):
    """
    Save a job for the authenticated user.

    This route adds the specified job to the user's saved list.

    Args:
        user (User): The authenticated user.
        job_id (str): The ID of the job to save.

    Returns:
        Redirect to the job detail page.

    Example:
        POST /jobs/save/123e4567-e89b-12d3-a456-426614174000
    """
    await jobs_controller.save_job_for_user(user.user_id, job_id)
    return redirect(url_for('jobs.job_details', job_id=job_id))


@jobs_route.post('/apply/<string:job_id>')
@flask_error_handler
@user_details
async def apply_job(user: User, job_id: str):
    """
    Submit a job application.

    The currently logged-in user applies to the job identified by `job_id`.

    Args:
        user (User): The authenticated user.
        job_id (str): The job's unique ID.

    Returns:
        Redirect to job detail page after applying.

    Example:
        POST /jobs/apply/123e4567-e89b-12d3-a456-426614174000
    """
    await jobs_controller.apply_to_job(user.user_id, job_id)
    return redirect(url_for('jobs.job_details', job_id=job_id))


@jobs_route.post('/deactivate/<string:job_id>')
@flask_error_handler
@user_details
@login_required
async def deactivate_job(user: User, job_id: str):
    """
    Deactivate a job listing (admin only).

    Marks the job as inactive by setting its status and expiration date.

    Args:
        user (User): The admin user.
        job_id (str): The ID of the job to deactivate.

    Returns:
        Redirect to the job detail page.

    Example:
        POST /jobs/deactivate/123e4567-e89b-12d3-a456-426614174000
    """
    await jobs_controller.deactivate_job_listing(job_id)
    return redirect(url_for('jobs.job_details', job_id=job_id))

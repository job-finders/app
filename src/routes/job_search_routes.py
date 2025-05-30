
from flask import Blueprint, render_template, request, redirect, url_for

from src.routes.utils import gone
from src.authentication import user_details, login_required, admin_login
from src.routes import flask_error_handler
from src.main import jobs
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
    page: int = int(request.args.get('page', 1))
    search_result: dict[str, str| int|list[jobs]] = await job_search_controller.get_all_jobs(page=page)

    context = {
        'jobs': search_result.get('jobs',[]),
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size',25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0)
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
    search_result: dict[str, str| int|list[jobs]] = await jobs_controller.search_jobs(keyword=keyword, page=page)

    context = {
        'jobs': search_result.get('jobs',[]),
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size',25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0),
        'search_keyword': keyword
        }

    return render_template('jobs/search.html', **context)


@jobs_route.get('/category/<string:category>')
@flask_error_handler
@user_details
async def jobs_by_category(user: User, category: str):
    """
    Display a paginated list of jobs filtered by category.

    Args:
        user (User): The currently authenticated user.
        category (str): The category to filter jobs by.

    Returns:
        HTML template rendering the filtered job listings.

    Example:
        GET /jobs/category/engineering?page=1
    """
    page = int(request.args.get('page', 1))
    search_result: dict[str, str | int | list[jobs]] = await jobs_controller.search_jobs_by_category(
        category=category, page=page
    )

    context = {
        'jobs': search_result.get('jobs', []),
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0),
        'category': category.replace('-', ' ').title()
    }

    return render_template('jobs/category.html', **context)


@jobs_route.get('/<string:job_id>')
@flask_error_handler
@user_details
async def job_details(user: User, job_id: str):
    """
    Display details for a specific job with related jobs listed.

    Args:
        user (User): The authenticated user.
        job_id (str): The unique identifier of the job.

    Returns:
        HTML page with job details and related jobs.
    """
    job: Job | None = await jobs_controller.get_job_by_id(job_id)
    if not job or job.status != "active":
        return await gone(search_term=job_id)

    related_jobs: list[Job] = await jobs_controller.get_similar_jobs(job_id=job.job_id)

    context = {
        'job': job,
        'related_jobs': related_jobs,
        'meta_title': job.title,
        'meta_description': job.short_description,
    }

    return render_template('jobs/detail.html', **context)



@jobs_route.get('/location/<string:location>')
@flask_error_handler
@user_details
async def jobs_by_location(user: User, location: str):
    """Search jobs by location.
    """
    page = int(request.args.get('page', 1))
    # Stub: await jobs_controller.search_by_location(location, page)
    search_result = await jobs_controller.get_jobs_by_location(location=location, page=page)

    return render_template('jobs/location.html', {
        'jobs': search_result.get('jobs', []),
        'page': search_result.get('page', page),
        'total_jobs': search_result.get('total_jobs', 0),
        'page_size': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 1),
        'location': location.title()})


@jobs_route.get('/type/<string:job_type>')
@flask_error_handler
@user_details
async def jobs_by_type(user: User, job_type: str):
    """
    Display a paginated list of jobs filtered by job type (e.g., full-time, part-time).

    Args:
        user (User): The currently authenticated user.
        job_type (str): The job type to filter by (e.g., "full-time").

    Returns:
        HTML page rendering the filtered jobs.
    """
    page = int(request.args.get('page', 1))

    search_result: dict = await jobs_controller.search_by_type(job_type=job_type, page=page)

    context = {
        'jobs': search_result.get('jobs', []),
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0),
        'job_type': job_type.replace('-', ' ').title(),
    }

    return render_template('jobs/type.html', **context)


@jobs_route.get('/featured')
@flask_error_handler
@user_details
async def featured_jobs(user: User):
    """
    Display a paginated list of featured jobs.

    Args:
        user (User): The currently authenticated user.

    Returns:
        HTML page rendering featured job listings.
    """
    page = int(request.args.get('page', 1))

    search_result: dict = await jobs_controller.get_featured_jobs(page=page)

    context = {
        'jobs': search_result.get('jobs', []),
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0),
    }

    return render_template('jobs/featured.html', **context)


@jobs_route.get('/recent')
@flask_error_handler
@user_details
async def recent_jobs(user: User):
    """
    Display paginated list of recently posted jobs.

    Args:
        user (User): The authenticated user.

    Returns:
        HTML template with the most recent jobs.
    """
    page = int(request.args.get('page', 1))
    search_result = await jobs_controller.get_recent_jobs(page=page)

    context = {
        'jobs': search_result.get('jobs', []),
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0)
    }

    return render_template('jobs/recent.html', **context)


@jobs_route.get('/salary')
@flask_error_handler
@user_details
async def jobs_by_salary_range(user: User):
    """
    Display jobs filtered by salary range (monthly or yearly).

    Query Params:
        min (int): Minimum salary.
        max (int): Maximum salary.
        unit (str): 'monthly' or 'yearly'. Defaults to 'yearly'.
        page (int): Page number.

    Returns:
        Rendered HTML with filtered job listings.
    """
    page = int(request.args.get('page', 1))
    min_salary = request.args.get('min', type=int)
    max_salary = request.args.get('max', type=int)
    unit = request.args.get('unit', 'yearly').lower()

    if unit not in ['monthly', 'yearly']:
        unit = 'yearly'  # fallback to default if invalid

    search_result = await jobs_controller.search_by_salary_range(
        min_salary=min_salary,
        max_salary=max_salary,
        page=page,
        unit=unit
    )
    context = {
        'jobs': search_result.get('jobs', []),
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0),
        'min_salary': request.args.get('min'),
        'max_salary': request.args.get('max'),
        'salary_unit': unit}

    return render_template('jobs/salary.html', **context)


@jobs_route.get('/company/<string:company_slug>')
@flask_error_handler
@user_details
async def jobs_by_company(user: User, company_slug: str):
    """
    List active jobs for a given company.
    
    Args:
        company_slug (str): Slugified company name (e.g., 'microsoft-south-africa')

    Query Params:
        page (int): Page number

    Returns:
        Rendered company job listing template.
    """
    page = int(request.args.get('page', 1))
    search_result = await jobs_controller.search_by_company(company_slug=company_slug, page=page)
    
    return render_template('jobs/company.html', {
        'jobs': search_result.get('jobs', []),
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0),
        'company': search_result.get('company_name', company_slug.replace('-', ' ').title())
    })

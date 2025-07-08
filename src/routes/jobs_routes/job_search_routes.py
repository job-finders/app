import random
from datetime import datetime, timedelta
from typing import TypedDict, List

from flask import Blueprint, render_template, request

from src.database.models.jobs_model import JobCategory
from src.database.models.resume import JobSeekerCV
from src.database.models import Job

from src.authentication import user_details
from src.database.models.users import User
from src.routes import flask_error_handler
from src.routes.utils import gone
from src.utils.route_helpers import get_controller


def generate_mock_jobs(keyword: str, count: int = 5) -> list[dict]:
    """Generate mock job listings for demonstration purposes"""
    titles = [
        f"Senior {keyword} Developer",
        f"{keyword} Specialist",
        f"Junior {keyword} Engineer",
        f"{keyword} Team Lead",
        f"{keyword} Product Manager"
    ]

    companies = [
        "Tech Innovations Inc.",
        "Digital Solutions Ltd.",
        "Future Systems Corp.",
        "Global Tech Partners",
        "InnovateX Technologies"
    ]

    cities = ["Cape Town", "Johannesburg", "Durban", "Pretoria", "Port Elizabeth"]
    provinces = ["Western Cape", "Gauteng", "KwaZulu-Natal", "Eastern Cape"]
    job_types = ["FULL_TIME", "PART_TIME", "CONTRACT"]
    remote_policies = ["REMOTE", "HYBRID", "ONSITE"]
    experience_levels = ["ENTRY", "MID", "SENIOR"]

    mock_jobs = []
    for i in range(count):
        posted_at = datetime.utcnow() - timedelta(days=random.randint(0, 30))
        salary_min = random.randint(20000, 50000)
        salary_max = salary_min + random.randint(10000, 30000)

        job = {
            "job_id": f"mock_{i}",
            "title": random.choice(titles),
            "company": {
                "name": random.choice(companies),
                "logo_url": None
            },
            "position_type": random.choice(job_types),
            "remote_policy": random.choice(remote_policies),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": "ZAR",
            "city": random.choice(cities),
            "province": random.choice(provinces),
            "country": "South Africa",
            "posted_at": posted_at,
            "expires_at": posted_at + timedelta(days=60),
            "experience_level": random.choice(experience_levels),
            "description": f"We're looking for a talented {keyword} professional to join our team. "
                           f"You'll work on cutting-edge {keyword} solutions and collaborate with "
                           "a team of passionate engineers. Apply now!",
            "application_count": random.randint(0, 50),
            "view_count": random.randint(10, 200),
            "is_featured": i == 0,  # First job is featured
            "location": f"{random.choice(cities)}, {random.choice(provinces)}, South Africa",
            "salary": f"ZAR {salary_min} - {salary_max}",
            "is_active": True
        }
        mock_jobs.append(job)

    return mock_jobs



class JobSearchContext(TypedDict):
    current_user: User
    jobs: List[Job]
    page: int
    per_page: int
    total_pages: int
    total_jobs: int
    filters: dict


# Blueprint definition
jobs_search_route = Blueprint('jobs', __name__, url_prefix='/jobs')


# noinspection DuplicatedCode
@jobs_search_route.get('/browse-jobs')
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
        GET /browse-jobs?page=2
    """
    job_search_controller = get_controller('jobs_search')
    
    # obtaining page arguments
    page: int = int(request.args.get('page', 1))
    page_size: int = int(request.args.get('page_size', 25))
    
    search_result = await job_search_controller.get_all_jobs(page=page, page_size=page_size)
    jobs = search_result.get('jobs', [])

    if not jobs:
        jobs = generate_mock_jobs("Software Development")

    context: JobSearchContext = {
        'current_user': user,
        'jobs': jobs,
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size',25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0),
        'filters': {}
    }

    return render_template('jobs/list.html', **context)


@jobs_search_route.get('/search')
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

    job_search_controller = get_controller('jobs_search')

    keyword = request.args.get('keyword', '')
    
    page: int = int(request.args.get('page', 1))
    page_size: int = int(request.args.get('page_size', 25))

    
    search_result = await job_search_controller.search_jobs(keyword=keyword, page=page, page_size=page_size)

    jobs = search_result.get('jobs', [])
    total_jobs = search_result.get('total_jobs', 0)
    show_mock_jobs = not jobs  # Flag to indicate if we should show mock jobs

    if show_mock_jobs:
        # Generate mock jobs for demonstration purposes
        jobs = generate_mock_jobs(keyword)
        total_jobs = len(jobs)

    context: JobSearchContext = {
        'current_user': user,
        'jobs': jobs,
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 1),
        'total_jobs': total_jobs,
        'filters': {
            'search_keyword': keyword
        }}

    return render_template('jobs/search.html', **context)


@jobs_search_route.get('/categories')
@flask_error_handler
@user_details
async def job_categories(user: User):

    job_search_controller = get_controller('jobs_search')
    job_category_list: list[JobCategory] = await job_search_controller.list_job_categories()

    # Calculate aggregate statistics
    total_jobs = sum(category.total_jobs for category in job_category_list)
    active_jobs = sum(category.active_jobs for category in job_category_list)
    featured_jobs = sum(category.featured_jobs for category in job_category_list)

    # Find max salary for progress bars
    max_salary = 0
    for category in job_category_list:
        if category.avg_salary_max and category.avg_salary_max > max_salary:
            max_salary = category.avg_salary_max
        elif category.avg_salary_min and category.avg_salary_min > max_salary:
            max_salary = category.avg_salary_min

    context = {
        'current_user': user,
        'categories': job_category_list,
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'featured_jobs': featured_jobs,
        'max_salary': max_salary
    }
    return render_template('jobs/job_categories_list.html', **context)

@jobs_search_route.get('/category/<string:category>')
@flask_error_handler
@user_details
async def category_jobs(user: User, category: str):
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
    

    page: int = int(request.args.get('page', 1))
    page_size: int = int(request.args.get('page_size', 25))

    job_search_controller = get_controller('jobs_search')
    search_result = await job_search_controller.search_jobs_by_category(category=category, page=page, page_size=page_size)

    context: JobSearchContext = {
        'current_user': user,
        'jobs': search_result.get('jobs', []),
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0),
        'filters': {'category': category.replace('-', ' ').title()}
    }

    return render_template('jobs/category.html', **context)


@jobs_search_route.get('/full-job-detail/<string:job_id>')
@flask_error_handler
@user_details
async def full_job_details(user: User, job_id: str):
    """sumary_line
        Display full job details for a specific job ID.
    Keyword arguments:
    argument -- description
    Return: return_description
    """

    job_search_controller = get_controller('jobs_search')
    job = await job_search_controller.get_job_by_id(job_id)

    if not job or job.status != "active":
        return await gone(user=user, search_term=job_id)

    related_jobs: list[Job] = await job_search_controller.get_similar_jobs(job_id=job.job_id)
        
    context = {
        'current_user': user,
        'job': job,
        'related_jobs': related_jobs,
        'meta_title': job.title,
        'meta_description': job.short_description,
    }

    return render_template('jobs/full_job_detail.html', **context)


@jobs_search_route.get('/<string:job_id>')
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
    job_search_controller = get_controller('jobs_search')
    resume_controller = get_controller('resume')

    job = await job_search_controller.get_job_by_id(job_id)
    if not job or job.status != "active":
        return await gone(user=user, search_term=job_id)

    related_jobs: list[Job] = await job_search_controller.get_similar_jobs(job_id=job.job_id)
    
    
    list_resumes: list[JobSeekerCV] = await resume_controller.list_cvs_for_user(user_id=user.uid)

    context = {
        'current_user': user,
        'job': job,
        'list_resumes': list_resumes,
        'related_jobs': related_jobs,
        'meta_title': job.title,
        'meta_description': job.short_description,
    }


    return render_template('jobs/job_detail.html', **context)

@jobs_search_route.get('/location/<string:location>')
@flask_error_handler
@user_details
async def jobs_by_location(user: User, location: str):
    """Search jobs by location.
    """
    page: int = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 25))

    # Stub: await jobs_controller.search_by_location(location, page)
    job_search_controller = get_controller('jobs_search')
    search_result = await job_search_controller.get_jobs_by_location(location=location, page=page, page_size=page_size)
    
    context = {
        'current_user': user,
        'jobs': search_result.get('jobs', []),
        'page': search_result.get('page', page),
        'total_jobs': search_result.get('total_jobs', 0),
        'page_size': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 1),
        'location': location.title()
    }
    return render_template('jobs/location.html',**context)


@jobs_search_route.get('/type/<string:job_type>')
@flask_error_handler
@user_details
async def jobs_by_type(user: User, job_type: str):
    """
    Display a paginated list of jobs filtered by job event_type (e.g., full-time, part-time).

    Args:
        user (User): The currently authenticated user.
        job_type (str): The job event_type to filter by (e.g., "full-time").

    Returns:
        HTML page rendering the filtered jobs.
    """
    page = int(request.args.get('page', 1))
    job_search_controller = get_controller('jobs_search')
    search_result: dict = await job_search_controller.search_by_type(job_type=job_type, page=page)

    context : JobSearchContext = {
        'current_user': user,
        'jobs': search_result.get('jobs', []),
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0),
        'filters': {'job_type': job_type.replace('-', ' ').title(),}
        }

    return render_template('jobs/type.html', **context)


# noinspection DuplicatedCode
@jobs_search_route.get('/featured')
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
    job_search_controller = get_controller('jobs_search')
    search_result = await job_search_controller.get_featured_jobs(page=page)

    context: JobSearchContext = {
        'current_user': user,
        'jobs': search_result.get('jobs', []),
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0),
        'filters': {}
    }

    return render_template('jobs/featured.html', **context)


# noinspection DuplicatedCode
@jobs_search_route.get('/recent')
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
    job_search_controller = get_controller('jobs_search')
    search_result = await job_search_controller.get_recent_jobs(page=page)

    context: JobSearchContext = {
        'current_user': user,
        'jobs': search_result.get('jobs', []),
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0),
        'filters': {}
    }

    return render_template('jobs/recent.html', **context)


@jobs_search_route.get('/salary')
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
    job_search_controller = get_controller('jobs_search')
    search_result = await job_search_controller.search_by_salary_range(
        min_salary=min_salary,
        max_salary=max_salary,
        page=page,
        unit=unit
    )
    context: JobSearchContext = {
        'current_user': user,
        'jobs': search_result.get('jobs', []),
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0),
        'filters': {
        'min_salary': request.args.get('min'),
        'max_salary': request.args.get('max'),
        'salary_unit': unit}
    }

    return render_template('jobs/salary.html', **context)


@jobs_search_route.get('/company/<string:company_slug>')
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
        :param company_slug:
        :param user:
    """
    page = int(request.args.get('page', 1))
    job_search_controller = get_controller('jobs_search')
    search_result = await job_search_controller.search_by_company(company_slug=company_slug, page=page)
    context: JobSearchContext = {
        'current_user': user,
        'jobs': search_result.get('jobs', []),
        'page': search_result.get('page', page),
        'per_page': search_result.get('page_size', 25),
        'total_pages': search_result.get('total_pages', 0),
        'total_jobs': search_result.get('total_jobs', 0),
        'filters': {
        'company': search_result.get('company_name', company_slug.replace('-', ' ').title())
        }
    }
    return render_template('jobs/company.html', **context)

@jobs_search_route.get('/title')
@flask_error_handler
@user_details
async def jobs_by_title(user: User):
    """Search jobs by title.   
        return dict(
            jobs=[Job(**job.to_dict()) for job in jobs],
            total_jobs=total_jobs,
            page=page,
            page_size=page_size,
            total_pages=total_pages)    
    """
    page = int(request.args.get('page', 1))
    title = request.args.get('q', '')
    job_search_controller = get_controller('jobs_search')
    result = await job_search_controller.get_jobs_by_title(title=title,page=page)

    context: JobSearchContext = {
        'current_user': user,
        'jobs': result.get('jobs',[]),
        'total_jobs': result.get('total_jobs', 0),
        'page': result.get('page',page),
        'per_page': result.get('page_size', len(result.get('jobs',[]))),
        'total_pages': result.get('total_pages',1),
        'filters': {
        'title': result.get('title', title)}
    }

    return render_template('jobs/title.html', **context)


@jobs_search_route.get('/qualification')
@flask_error_handler
@user_details
async def jobs_by_qualification(user: User):
    """
    Search jobs by qualification.    
            return dict(
                jobs=[Job(**job.to_dict()) for job in jobs],
                total_jobs=total_jobs,
                page=page,
                page_size=page_size,
                total_pages=total_pages)
    """

    page = int(request.args.get('page', 1))
    qualification = request.args.get('q', '')
    types = request.args.getlist('event_type') or None
    job_search_controller = get_controller('jobs_search')
    result = await job_search_controller.get_jobs_by_qualification(qualification=qualification,
    qualification_types=types,page=page)

    context : JobSearchContext = {
        'current_user': user,
        'jobs': result.get('jobs', []),
        'total_jobs': result.get('total_jobs', 0),
        'page': result.get('page', page),
        'per_page': result.get('page_size', len(result.get('jobs', []))),
        'total_pages': result.get('total_pages', 1),
        'filters': {'qualification': qualification}
    }
    return render_template('jobs/qualification.html', **context)

@jobs_search_route.get('/reference/<string:reference>')
@flask_error_handler
@user_details
async def job_by_reference(user: User, reference: str):
    """Retrieve a job by its reference number."""
    job_search_controller = get_controller('jobs_search')
    job = await job_search_controller.get_job_by_reference(reference=reference)

    if not job:
        return render_template('jobs/error_404.html'), 404
    context = {'current_user': user,'job': job}
    return render_template('jobs/reference.html', **context)


##############################################################################################################
# @jobs_route.get('/jobs-in/<string:location>')
# @flask_error_handler
# @user_details
# async def jobs_by_location(user: User,location: str):
#     """
#     Handles jobs by province or town.
#     If the location is a known town, replace it with its parent province for consistent filtering.
#     """
#
#     page = int(request.args.get('page', 1))
#     location_lower = location.lower()
#
#     # If user typed a town, convert to province
#     if location_lower in TOWN_TO_PROVINCE:
#         province = TOWN_TO_PROVINCE[location_lower]
#     else:
#         province = location  # Assume it's already a province or partial match
#
#     jobs_filtered = [
#         job for job in scrapper.jobs.values()
#         if job.location and province.lower() in job.location.lower()
#     ]
#
#
#
#     if not jobs_filtered:
#         return await not_found(location)
#
#     # Slug for SEO
#     search_term = f"jobs-in-{location_lower.replace(' ', '-')}"
#
#     context = await create_common_context(
#         search_term=search_term,
#         job_list=jobs_filtered,
#         page=page,
#         per_page=10
#     )
#     context.update(current_user=user)
#
#     return render_template('location.html', **context)


# @jobs_route.get('/jobs/category/<string:category>')
# @flask_error_handler
# @user_details
# async def category_jobs(user: User,category: str):
#     """Render job search results by search term."""
#     page = int(request.args.get('page', 1))
#     response = await create_search_context(user=user, search_term=category, page=page)
#     if response is None:
#         return await not_found(category)
#     return response
#
#
# @jobs_route.get('/jobs/<string:search_term>')
# @flask_error_handler
# @user_details
# async def job_search(user: User,search_term: str):
#     """Render job search results by search term."""
#     page = int(request.args.get('page', 1))
#     response = await create_search_context(user=user, search_term=search_term, page=page)
#     if response is None:
#         return await not_found(search_term)
#     return response
#
#
# @jobs_route.get('/search')
# @flask_error_handler
# @user_details
# async def search_bar(user: User):
#     """Render search results from a query submitted via search bar."""
#     search_term = request.args.get('search_term')
#     if not search_term:
#         return redirect(url_for('home.get_home'), code=302)
#     page = int(request.args.get('page', 1))
#     response = await create_search_context(user=user, search_term=search_term, page=page)
#     if response is None:
#         return await not_found(search_term)
#     return response
#
#
# @jobs_route.get('/job/<string:reference>')
# @flask_error_handler
# @user_details
# async def job_detail(user: User, reference: str):
#     """Display job details identified by job reference."""
#     if user and user.role == Role.SEEKER:
#         # Obtain Job Seeker Resume
#         pass
#
#     job: Job = await scrapper.job_search(job_reference=reference)
#
#     if isinstance(job, Job) and job.title.strip():
#         return await sub_job_detail(user=user, job=job)
#     return await gone(user=user, search_term=reference)
#
# @jobs_route.get('/search/job/<string:slug>')
# @flask_error_handler
# @user_details
# async def job_slug(user: User,slug: str):
#     """Display job details identified by its slug."""
#     job: Job = await scrapper.search_by_slug(slug=slug)
#     if isinstance(job, Job) and job.title.strip():
#         return await sub_job_detail(user=user, job=job)
#     return await gone(search_term=slug)
#
#
# @jobs_route.get('/jobs/categories')
# @flask_error_handler
# @user_details
# async def categories(user: User):
#     pass
#
#
# @jobs_route.get('/jobs/ai-based-search')
# @flask_error_handler
# @user_details
# async def assisted_search(user: User):
#     pass
# Standard Library
from typing import TypedDict, List, Tuple
import time
# Flask Core
from flask import Blueprint, render_template, request, jsonify
import random

from src.controllers.jobs import JobsSearchController
# Authentication
from src.authentication import user_details
# Domain Models
from src.database.models import Job, JobCategory, JobSeekerCV, User, JobSeekerProfile
# Routes
from src.routes import flask_error_handler
from src.routes.utils import gone
# Utilities
from src.utils.route_helpers import get_controller, get_service
# Fake Data
from src.routes.fake_data import store
import random
from typing import Optional, List
# Cache
from src.cache.cache_redis import cached

# Blueprint definition
jobs_search_route = Blueprint('jobs', __name__, url_prefix='/jobs')


@jobs_search_route.route('/job-match-analysis/<string:job_id>', methods=['GET'])
@user_details
async def get_job_match_analysis(user: User, job_id: str):
    """
    API endpoint to get detailed job match analysis for a specific job.

    Args:
        user (User): The authenticated user
        job_id (str): The job ID to analyze

    Returns:
        JSON response with detailed match breakdown
    """
    from flask import jsonify
    from src.cache.cache_redis import cache
    from src.monitoring.match_scoring_metrics import track_performance, analytics

    logger = get_service('logger')()("API = Get Match Scores")
    # Track API usage
    start_time = time.time()
    logger.info(f"STARTED EXECUTION: {start_time}")
    logger.info(f"Received job_id: {job_id}")
    logger.info(f"User object: {user}")
    logger.info(f"User UID: {user.uid if user else 'No user'}")

    # Check if user is authenticated
    if not user or not user.uid:
        analytics.track_modal_interaction(
            user_id="anonymous",
            job_id=job_id,
            action="unauthorized_access"
        )
        return jsonify({
            'success': False,
            'message': 'Authentication required for match analysis'
        }), 401

    try:
        job_search_controller: JobsSearchController = get_controller('jobs_search')

        # Check if job exists
        job = await job_search_controller.get_complete_job_by_id(job_id=job_id)
        if not job:
            # Check fake data if enabled
            logger.info("Job Not Found")
            if store.is_fake_mode() and job_id in store.jobs:
                job = store.jobs[job_id]
            else:
                return jsonify({
                    'success': False,
                    'message': 'Job not found'
                }), 404
        logger.info(f"Job found: {job.title} (ID: {job.job_id})")
        # Check cache first (1-hour TTL)
        cache_key = f"detailed_match_{user.uid}_{job_id}"
        cached_analysis = cache.get(cache_key)

        if cached_analysis:
            logger.info(f"We found Cached Analyses: {cached_analysis}")
            analytics.track_modal_interaction(
                user_id=user.uid,
                job_id=job_id,
                action="opened",
                additional_data={"cached": True, "response_time": time.time() - start_time}
            )
            return jsonify({
                'success': True,
                'match_analysis': cached_analysis,
                'cached': True
            })
        logger.info(f"Trying to Obtain User Profile for User : {user.uid}")
        # Get user profile
        user_profile = await get_user_profile_for_matching(user_id=user.uid)
        if not user_profile:
            return jsonify({
                'success': False,
                'message': 'Please complete your profile to view match analysis'
            }), 400

        # Calculate detailed match analysis
        logger.info(f"Calculating Match Analysis  with : {user_profile.first_name}")
        match_analysis = await job_search_controller.calculate_job_match_score(job=job, user_id=user.uid)
        logger.info(f"Match Score we found : {match_analysis}")
        if not match_analysis:
            return jsonify({
                'success': False,
                'message': 'Unable to calculate match analysis at this time'
            }), 500

        # Format the response data
        formatted_analysis = {
            'total_score': match_analysis.get('total_score', 0),
            'job_title': job.title,
            'company_name': getattr(job, 'company_name', 'Unknown Company'),
            'skills_match': {
                'score': match_analysis.get('score_breakdown', {}).get('skills_match', 0),
                'matched_skills': match_analysis.get('matched_skills', []),
                'missing_skills': match_analysis.get('missing_skills', []),
                'explanation': match_analysis.get('skills_explanation', 'Skills analysis not available')
            },
            'experience_match': {
                'score': match_analysis.get('score_breakdown', {}).get('experience_match', 0),
                'details': {
                    'required_years': getattr(job, 'experience_required', 'Not specified'),
                    'user_years': getattr(user_profile, 'years_experience', 'Not specified'),
                    'industry_match': match_analysis.get('industry_match', 'Not specified')
                },
                'explanation': match_analysis.get('experience_explanation', 'Experience analysis not available')
            },
            'location_match': {
                'score': match_analysis.get('score_breakdown', {}).get('location_match', 0),
                'details': {
                    'job_location': getattr(job, 'location', 'Not specified'),
                    'user_location': getattr(user_profile, 'location', 'Not specified'),
                    'remote_option': getattr(job, 'remote_work', 'Not specified')
                },
                'explanation': match_analysis.get('location_explanation', 'Location analysis not available')
            },
            'salary_match': {
                'score': match_analysis.get('score_breakdown', {}).get('salary_match', 0),
                'details': {
                    'offered_range': f"R{getattr(job, 'salary_min', 0):,} - R{getattr(job, 'salary_max', 0):,}" if hasattr(
                        job, 'salary_min') else 'Not specified',
                    'expected_range': f"R{getattr(user_profile, 'expected_salary_min', 0):,} - R{getattr(user_profile, 'expected_salary_max', 0):,}" if hasattr(
                        user_profile, 'expected_salary_min') else 'Not specified',
                    'match_level': match_analysis.get('salary_match_level', 'Not specified')
                },
                'explanation': match_analysis.get('salary_explanation', 'Salary analysis not available')
            },
            'interpretation': match_analysis.get('interpretation', 'Match analysis completed successfully')
        }

        # Cache the result for 1 hour
        cache.set(cache_key, formatted_analysis, ttl=60 * 60)

        # Track successful modal interaction
        analytics.track_modal_interaction(
            user_id=user.uid,
            job_id=job_id,
            action="opened",
            additional_data={
                "cached": False,
                "response_time": time.time() - start_time,
                "total_score": formatted_analysis.get('total_score', 0)
            }
        )

        return jsonify({
            'success': True,
            'match_analysis': formatted_analysis,
            'cached': False
        })

    except Exception as e:
        print(f"Error in job match analysis API: {e}")

        # Track error
        analytics.track_modal_interaction(
            user_id=user.uid if user else "unknown",
            job_id=job_id,
            action="error",
            additional_data={"error": str(e), "response_time": time.time() - start_time}
        )

        return jsonify({
            'success': False,
            'message': 'An error occurred while analyzing job match'
        }), 500


@jobs_search_route.route('/api/jobs/<string:job_slug>/match-analysis', methods=['GET'])
@flask_error_handler
@user_details
async def get_job_match_analysis_by_slug(user: User, job_slug: str):
    """
    API endpoint to get detailed job match analysis using job slug.

    Args:
        user (User): The authenticated user
        job_slug (str): The job slug to analyze

    Returns:
        JSON response with detailed match breakdown
    """
    from flask import jsonify

    # Check if user is authenticated
    if not user or not user.uid:
        return jsonify({
            'success': False,
            'message': 'Authentication required for match analysis'
        }), 401

    try:
        job_search_controller: JobsSearchController = get_controller('jobs_search')

        # Get job by slug (assuming there's a method for this)
        # If not available, we'll need to implement it or use job_id
        job = await job_search_controller.get_job_by_slug(job_slug) if hasattr(job_search_controller,
                                                                               'get_job_by_slug') else None

        if not job:
            return jsonify({
                'success': False,
                'message': 'Job not found'
            }), 404

        # Redirect to the job_id endpoint
        return await get_job_match_analysis(user, job.job_id)

    except Exception as e:
        print(f"Error in job match analysis by slug API: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while analyzing job match'
        }), 500


class FakeDataHandler:
    @staticmethod
    def get_job(job_id: str) -> Optional[Job]:
        return store.jobs.get(job_id)

    @staticmethod
    def get_related_jobs(job_id: str, count: int = 4) -> List[Job]:
        return list(store.jobs.values())[:count]

    @staticmethod
    def get_user_resumes(user_id: str, count: int = 2) -> List[JobSeekerCV]:
        return list(store.resumes.values())[:count]

    @staticmethod
    def check_application_status(user_id: str, job_id: str) -> bool:
        return random.choice([True, False])


MIN_PAGE = 1
MAX_PAGE_SIZE = 100
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 25

async def parse_pagination_params(
    default_page: int = DEFAULT_PAGE,
    default_size: int = DEFAULT_PAGE_SIZE,
    max_size: int = MAX_PAGE_SIZE
) -> Tuple[int, int]:
    """Flexible version with customizable defaults"""
    try:
        page = request.args.get('page', default=default_page, type=int)
        
    except (TypeError, ValueError):
        page = default_page
    
    try:
        page_size = request.args.get('page_size', default=default_size, type=int)
        
    except (TypeError, ValueError):
        page_size = default_size

    page = max(page, MIN_PAGE)
    page_size = max(min(page_size, max_size), 1)
    
    return page, page_size


def get_fake_jobs(keyword: str = None) -> list[Job]:
    """Get jobs from fake data store, optionally filtered by keyword"""
    if not store.is_fake_mode():
        return []
        
    if keyword:
        keyword = keyword.lower()
        return [
            job for job in store.jobs.values()
            if keyword in job.title.lower() or
               (job.description and keyword in job.description.lower())
        ]
    return list(store.jobs.values())


# @cached(ttl=30 * 60)  # 30-minute cache TTL
async def get_user_profile_for_matching(user_id: str) -> Optional[JobSeekerProfile]:
    """Get user profile for match scoring with caching"""
    logger = get_service("logger")()("GET Profile for Job Matching")
    if not user_id:
        return None
    
    try:
        logger.info(f"Will Now try to obtain Profile for Job Matching")
        profile_controller = get_controller('job_seeker_profile')
        job_seeker_profile = await profile_controller.get_complete_profile_by_uid(user_uid=user_id)
        logger.info(f"We found the Seeker Profile : {job_seeker_profile.first_name}")
        return job_seeker_profile
    except Exception as e:
        print(f"Error fetching user profile for matching: {e}")
        return None


async def calculate_batch_match_scores(jobs: List[Job], user: User, job_search_controller: JobsSearchController) -> List[Job]:
    """
    Calculate quick match scores for a batch of jobs with optimized performance and caching.
    
    Args:
        jobs: List of jobs to score
        user: Current user
        job_search_controller: Controller instance for scoring
        
    Returns:
        List of jobs with match_score attribute added
    """
    from src.services.optimized_match_scoring import optimizer

    logger = get_service('logger')()("Batch Match Scores :")

    if not user or not user.uid or not jobs:
        # Return jobs without match scores if no user or no jobs
        for job in jobs:         
            job.match_score = None
        logger.info(f"We could not calculate scores Jobs : {len(jobs)},  User : {user}")
        return jobs
    
    try:
        # Get user profile with caching
        user_profile = await get_user_profile_for_matching(user_id=user.uid)
        logger.info(f"What we Found : {user_profile}")
        if not user_profile:
            # User has no profile - return jobs without match scores
            for job in jobs:
                job.match_score = None
            logger.info("We could not calculate scores because we failed to locate user profiles")
            return jobs
        
        # Use optimized batch scoring service

        logger.info("We are now loading Optimized Job Match Scores")
        return await optimizer.optimize_job_listing_scores(user.uid, jobs, user_profile)
                
    except Exception as e:
        logger.error(f"Error in batch match scoring: {e}")
        # Fallback: set all match scores to None
        for job in jobs:
            job.match_score = None
    
    return jobs

class JobSearchContext(TypedDict):
    current_user: User
    jobs: List[Job]
    page: int
    per_page: int
    total_pages: int
    total_jobs: int
    filters: dict



# noinspection DuplicatedCode
@jobs_search_route.get('/browse-jobs')
@flask_error_handler
@user_details
async def list_jobs(user: User):
    """
    Display a paginated list of all available jobs with match scores.

    This route fetches all published jobs from the database using the jobs controller,
    paginates the results based on the 'page' query parameter, calculates quick match
    scores for each job, and renders them using the `jobs/list.html` template.

    Args:
        user (User): The currently authenticated user.

    Returns:
        HTML template rendering the job listings with match scores.

    Example:
        GET /browse-jobs?page=2
    """
    job_search_controller: JobsSearchController = get_controller('jobs_search')
    
    # Advanced parsing with type conversion and validation
    page, page_size = await parse_pagination_params()
   
    search_result = await job_search_controller.get_all_jobs(page=page, page_size=page_size)
    jobs = search_result.get('jobs', [])

    if not jobs and store.is_fake_mode():
        jobs = get_fake_jobs()

    # Calculate match scores for jobs if user is logged in and has profile
    jobs_with_scores = await calculate_batch_match_scores(jobs, user, job_search_controller)

    context: JobSearchContext = {
        'current_user': user,
        'jobs': jobs_with_scores,
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
    Search for jobs by keyword with match scores.

    This route retrieves job listings filtered by the given 'keyword' query parameter,
    calculates quick match scores for each job, and supports pagination. Results are
    rendered using the `jobs/search.html` template.

    Args:
        user (User): The currently authenticated user.

    Returns:
        HTML template with search results and match scores.

    Example:
        GET /jobs/search?keyword=engineer&page=1
    """

    job_search_controller = get_controller('jobs_search')

    keyword = request.args.get('keyword', '')
    
    page, page_size = await parse_pagination_params()

    
    search_result = await job_search_controller.search_jobs(keyword=keyword, page=page, page_size=page_size)

    jobs = search_result.get('jobs', [])
    total_jobs = search_result.get('total_jobs', 0)
    show_mock_jobs = not jobs  # Flag to indicate if we should show mock jobs

    if show_mock_jobs and store.is_fake_mode():
        jobs = get_fake_jobs(keyword)
        total_jobs = len(jobs) if jobs else 0

    # Calculate match scores for jobs
    jobs_with_scores = await calculate_batch_match_scores(jobs, user, job_search_controller)

    context: JobSearchContext = {
        'current_user': user,
        'jobs': jobs_with_scores,
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
    Display a paginated list of jobs filtered by category with match scores.

    Args:
        user (User): The currently authenticated user.
        category (str): The category to filter jobs by.

    Returns:
        HTML template rendering the filtered job listings with match scores.

    Example:
        GET /jobs/category/engineering?page=1
    """
    

    page, page_size = await parse_pagination_params()

    job_search_controller = get_controller('jobs_search')
    search_result = await job_search_controller.search_jobs_by_category(category=category, page=page, page_size=page_size)

    jobs = search_result.get('jobs', [])
    
    # Calculate match scores for jobs
    jobs_with_scores = await calculate_batch_match_scores(jobs, user, job_search_controller)

    context: JobSearchContext = {
        'current_user': user,
        'jobs': jobs_with_scores,
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
    """Display full job details for a specific job ID."""

    job_search_controller = get_controller('jobs_search')
    job = await job_search_controller.get_job_by_id(job_id)

    if not job or job.status != "active":
        # Check for mock job
        if store.is_fake_mode():
            fake_job = store.get_fake_job(job_id)
            if fake_job:
                job = fake_job
            else:
                return await gone(user=user, search_term=job_id)
        else:
            return await gone(user=user, search_term=job_id)

    related_jobs: list[Job] = await job_search_controller.get_similar_jobs(job_id=job.job_id)

    context = {
        'current_user': user,
        'job': job,
        'related_jobs': related_jobs,
        'meta_title': job.title,
        'meta_description': job.seo_description,
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

    # Get job with statistics for enhanced detail page
    job, job_statistics = await job_search_controller.get_job_with_statistics(job_id)
    
    if not job or job.status != "active":
        # Check for fake data if enabled
        if store.is_fake_mode():
            fake_job = store.jobs.get(job_id)
            if fake_job:
                job = fake_job
                job_statistics = None  # No statistics for fake jobs
            else:
                return await gone(user=user, search_term=job_id)
        else:
            return await gone(user=user, search_term=job_id)

    # Get related jobs - use fake data if original job was fake
    if job.job_id in store.jobs:
        related_jobs = list(store.jobs.values())[:4]  # Get first few fake jobs as "related"
    else:
        related_jobs = await job_search_controller.get_similar_jobs(job_id=job.job_id)
    
    # Get resumes - use fake ones if job was fake
    if job.job_id in store.jobs:
        list_resumes = list(store.resumes.values())[:2]  # Get first couple fake resumes
    else:
        list_resumes = await resume_controller.list_cvs_for_user(user_id=user.uid)

    # Check if user has already applied for this job
    user_has_applied = False
    if user and user.uid:
        if job.job_id in store.jobs:
            # For fake jobs, randomly decide if "applied"
            user_has_applied = random.choice([True, False])
        else:
            try:
                user_applications, _ = await job_search_controller.get_applied_jobs_for_user(user_id=user.uid)
                user_has_applied = any(app.job_id == job_id for app in user_applications)
            except Exception:
                # If there's an error checking application status, default to False
                user_has_applied = False

    context = {
        'current_user': user,
        'job': job,
        'job_statistics': job_statistics,
        'list_resumes': list_resumes,
        'related_jobs': related_jobs,
        'user_has_applied': user_has_applied,
        'meta_title': job.title,
        'meta_description': job.seo_description,
    }

    return render_template('jobs/job_detail.html', **context)

@jobs_search_route.get('/location/<string:location>')
@flask_error_handler
@user_details
async def jobs_by_location(user: User, location: str):
    """Search jobs by location with match scores.
    """

    page, page_size = await parse_pagination_params()

    # Stub: await jobs_controller.search_by_location(location, page)
    job_search_controller = get_controller('jobs_search')
    search_result = await job_search_controller.get_jobs_by_location(location=location, page=page, page_size=page_size)

    jobs = search_result.get('jobs', [])
    
    # Calculate match scores for jobs
    jobs_with_scores = await calculate_batch_match_scores(jobs, user, job_search_controller)

    context = {
        'current_user': user,
        'jobs': jobs_with_scores,
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
    Display a paginated list of jobs filtered by job event_type (e.g., full-time, part-time) with match scores.

    Args:
        user (User): The currently authenticated user.
        job_type (str): The job event_type to filter by (e.g., "full-time").

    Returns:
        HTML page rendering the filtered jobs with match scores.
    """
    
    page, page_size = await parse_pagination_params()

    job_search_controller = get_controller('jobs_search')
    search_result: dict = await job_search_controller.search_by_type(job_type=job_type, page=page, page_size=page_size)

    jobs = search_result.get('jobs', [])
    
    # Calculate match scores for jobs
    jobs_with_scores = await calculate_batch_match_scores(jobs, user, job_search_controller)

    context : JobSearchContext = {
        'current_user': user,
        'jobs': jobs_with_scores,
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
    Display a paginated list of featured jobs with match scores.

    Args:
        user (User): The currently authenticated user.

    Returns:
        HTML page rendering featured job listings with match scores.
    """

    page, page_size = await parse_pagination_params()

    job_search_controller = get_controller('jobs_search')
    search_result = await job_search_controller.get_featured_jobs(page=page, page_size=page_size)

    jobs = search_result.get('jobs', [])
    
    # Calculate match scores for jobs
    jobs_with_scores = await calculate_batch_match_scores(jobs, user, job_search_controller)

    context: JobSearchContext = {
        'current_user': user,
        'jobs': jobs_with_scores,
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
    Display paginated list of recently posted jobs with match scores.

    Args:
        user (User): The authenticated user.

    Returns:
        HTML template with the most recent jobs and match scores.
    """
    page, page_size = await parse_pagination_params()

    job_search_controller = get_controller('jobs_search')
    search_result = await job_search_controller.get_recent_jobs(page=page, page_size=page_size)

    jobs = search_result.get('jobs', [])
    
    # Calculate match scores for jobs
    jobs_with_scores = await calculate_batch_match_scores(jobs, user, job_search_controller)

    context: JobSearchContext = {
        'current_user': user,
        'jobs': jobs_with_scores,
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
    
    page, page_size = await parse_pagination_params()

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
        page_size=page_size,
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
    
    page, page_size = await parse_pagination_params()

    job_search_controller = get_controller('jobs_search')
    search_result = await job_search_controller.search_by_company(company_slug=company_slug, page=page, page_size=page_size)

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
    
    page, page_size = await parse_pagination_params()

    title = request.args.get('q', '')
    job_search_controller = get_controller('jobs_search')
    result = await job_search_controller.get_jobs_by_title(title=title,page=page, page_size=page_size)


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

    page, page_size = await parse_pagination_params()

    qualification = request.args.get('q', '')
    types = request.args.getlist('event_type') or None
    job_search_controller = get_controller('jobs_search')
    result = await job_search_controller.get_jobs_by_qualification(qualification=qualification,
    qualification_types=types,page=page, page_size=page_size)

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
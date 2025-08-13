# Flask Core
from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
# Authentication
from src.authentication import jobseeker_login
# Domain Models
from src.database.models import JobSeekerCV, User
# Routes
from src.routes import flask_error_handler
# Utilities
from src.utils.route_helpers import get_controller, get_service

jobseeker_route = Blueprint('jobseekers', __name__,  url_prefix="/jobseeker")


async def get_user_cv(uid):
    pass


@jobseeker_route.route("/ai/cv/optimize", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def optimize_cv(user: User):
    # TODO - please Note this is just an API
    resume_controller = get_controller('resume')
    employee_agents_controller = get_controller('employee_agents')
    primary_resume: JobSeekerCV = await resume_controller.get_primary_resume(user_uid=user.uid)
    optimized_resume: JobSeekerCV = await employee_agents_controller.optimize_primary_cv(primary_resume=primary_resume)
    return jsonify(optimized_resume.model_dump())



@jobseeker_route.route('/dashboard', methods=['GET'])
@flask_error_handler
@jobseeker_login
# Fix 2: User Profile - Add null check before accessing attributes
async def dashboard(user: User):
    """Dashboard route with dynamic statistics from database"""
    logger = get_service("logger")()("JOB SEEKER ROUTER LOGGER")
    try:
        # Validate user object
        if not user or not hasattr(user, 'uid'):
            logger.error("Invalid user object")
            return redirect(url_for('auth.login'))

        # Get controllers
        resume_controller = get_controller('resume')
        jobs_search_controller = get_controller('jobs_search')

        # Get user CVs
        user_cvs = await resume_controller.list_cvs_for_user(user_uid=user.uid)

        # Get dashboard statistics with error handling
        try:
            dashboard_stats = await jobs_search_controller.get_user_dashboard_statistics(user.uid)
        except Exception as e:
            logger.error(f"Error fetching dashboard stats: {str(e)}")
            dashboard_stats = {}

        # Get saved jobs with error handling
        try:
            saved_jobs = await jobs_search_controller.get_saved_jobs_for_user(user.uid)
            recent_saved_jobs = saved_jobs[:5] if saved_jobs else []
        except Exception as e:
            logger.error(f"Error fetching saved jobs: {str(e)}")
            recent_saved_jobs = []

        # Safe access to user attributes
        seeker_stats = {
            'count': len(user_cvs) if user_cvs else 0,
            'cv_uploaded': dashboard_stats.get('cv_uploaded', False) if dashboard_stats else False,
            'cv_count': dashboard_stats.get('cv_count', 0) if dashboard_stats else 0,
            'applications_count': dashboard_stats.get('applications_count', 0) if dashboard_stats else 0,
            'saved_jobs_count': dashboard_stats.get('saved_jobs_count', 0) if dashboard_stats else 0,
            'recent_applications_count': dashboard_stats.get('recent_applications_count', 0) if dashboard_stats else 0,
            'saved_jobs': recent_saved_jobs
        }

        context = dict(current_user=user, seeker_stats=seeker_stats)
        return render_template("jobseekers/dashboard.html", **context)

    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return redirect(url_for('auth.login'))


@jobseeker_route.route('/apply', methods=['GET'])
@flask_error_handler
@jobseeker_login
async def apply(user: User):
    """Job Seekers retrieves their job application form here - this form will obtain the relevant job data
    from the request"""
    context = dict(current_user=user)
    return render_template("jobseekers/apply.html", **context)


@jobseeker_route.route('/saved-jobs', methods=['GET'])
@flask_error_handler
@jobseeker_login
async def saved_jobs(user: User):
    """Retrieves paginated list of jobs saved by the job seeker"""
    # Get pagination parameters
    logger = get_service("logger")()("GET SAVED JOBS")
    limit = min(int(request.args.get('limit', 20)), 100)  # Max 100 items
    offset = max(int(request.args.get('offset', 0)), 0)

    # Get job actions controller
    job_actions_controller = get_controller('job_actions')

    # Get saved jobs
    result = await job_actions_controller.get_user_saved_jobs(
        user_id=user.uid,
        limit=limit,
        offset=offset
    )

    if not result.success:
        flash("Error retrieving saved jobs", "danger")
        return redirect(url_for('jobseekers.dashboard'))

    # Prepare context with pagination info
    context = {
        'current_user': user,
        'jobs': result.jobs,
        'pagination': {
            'total': result.total_count,
            'limit': result.limit,
            'offset': result.offset
        }
    }
    
    return render_template("jobseekers/saved_jobs.html", **context)




@jobseeker_route.route('/notifications', methods=['GET'])
@flask_error_handler
@jobseeker_login
async def notifications(user: User):
    """Job Seekers Specific Notifitions"""
    context = dict(current_user=user)
    return render_template("jobseekers/notifications.html", **context)

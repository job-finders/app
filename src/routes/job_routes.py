
from flask import Blueprint, render_template, request, redirect, url_for

from authentication import login_required, admin_login
from routes.utils import gone
from src.authentication import user_details
from src.routes import flask_error_handler
from src.main import jobs_controller
from src.database.models.users import User


# Blueprint definition
jobs_route = Blueprint('jobs', __name__, url_prefix='/jobs')

# Route for displaying all jobs
@jobs_route.get('/')
@flask_error_handler
@user_details
async def list_jobs(user: User):
    """Display paginated list of all available jobs."""
    page = int(request.args.get('page', 1))
    jobs = await jobs_controller.get_all_jobs(page)
    context = {
        'jobs': jobs,
        'page': page,
        'per_page': 10,
        'total_jobs': await jobs_controller.get_total_jobs(),
    }
    return render_template('jobs/list.html', **context)


# Route for searching jobs
@jobs_route.get('/search')
@flask_error_handler
@user_details
async def search_jobs(user: User):
    """Search for jobs based on a keyword."""
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

# Route for displaying a single job's details
@jobs_route.get('/<string:job_id>')
@flask_error_handler
@user_details
async def job_details(user: User, job_id: str):
    """Display detailed information about a job."""
    job = await jobs_controller.get_job_by_id(job_id)
    if not job:
        return await gone(search_term=job_id)
    context = {'job': job}
    return render_template('jobs/detail.html', **context)



# Route for saving a job
@jobs_route.post('/save/<string:job_id>')
@flask_error_handler
@user_details
async def save_job(user: User, job_id: str):
    """Save a job for the user."""
    await jobs_controller.save_job_for_user(user.user_id, job_id)
    return redirect(url_for('jobs.job_details', job_id=job_id))


# Route for applying to a job
@jobs_route.post('/apply/<string:job_id>')
@flask_error_handler
@user_details
async def apply_job(user: User, job_id: str):
    """Apply to a job listing."""
    await jobs_controller.apply_to_job(user.user_id, job_id)
    return redirect(url_for('jobs.job_details', job_id=job_id))


# Route for deactivating a job listing
@jobs_route.post('/deactivate/<string:job_id>')
@flask_error_handler
@user_details
@login_required  # This could be a custom decorator for admin users
async def deactivate_job(user: User, job_id: str):
    """Deactivate a job listing (admin only)."""
    await jobs_controller.deactivate_job_listing(job_id)
    return redirect(url_for('jobs.job_details', job_id=job_id))


# Route for deleting a job listing (admin only)
@jobs_route.post('/delete/<string:job_id>')
@flask_error_handler
@user_details
@login_required
async def delete_job(user: User, job_id: str):
    """Delete a job listing (admin only)."""
    await jobs_controller.delete_job(job_id)
    return redirect(url_for('jobs.list_jobs'))



# Route for displaying saved jobs
@jobs_route.get('/saved')
@flask_error_handler
@user_details
async def saved_jobs(user: User):
    """Display list of jobs that the user has saved."""
    saved_jobs = await jobs_controller.get_saved_jobs_for_user(user.user_id)
    context = {'saved_jobs': saved_jobs}
    return render_template('jobs/saved_jobs.html', **context)


# Route for displaying applied jobs
@jobs_route.get('/applied')
@flask_error_handler
@user_details
async def applied_jobs(user: User):
    """Display list of jobs that the user has applied to."""
    applied_jobs = await jobs_controller.get_applied_jobs_for_user(user.user_id)
    context = {'applied_jobs': applied_jobs}
    return render_template('jobs/applied_jobs.html', **context)


# Route for displaying a "Job Not Found" page
@jobs_route.get('/gone')
@flask_error_handler
async def gone(search_term: str = ''):
    """Display a page when a job is not found."""
    return render_template('jobs/gone.html', search_term=search_term)

@jobs_route.get('/view/<string:job_id>')
@flask_error_handler
async def view(job_id: str):
    pass


@jobs_route.get('/jobs/review/<string:approval_token>')
@flask_error_handler
@admin_login
async def review_job(user: User, approval_token: str):
    """
    Display job details and prompt admin for approval or rejection with feedback.
    """
    job_data = await jobs_controller.get_job_by_token(approval_token)

    if not job_data.success:
        return render_template("admin/jobs/job_approval_error.html", message=job_data.message), 400

    return render_template("admin/jobs/job_approval_error.html", job=job_data.data, token=approval_token)


@jobs_route.post('/jobs/submit-review/<string:approval_token>')
@flask_error_handler
@admin_login
async def submit_job_review(user: User, approval_token: str):
    """
    Process admin's decision (approve or reject) and feedback.
    """
    form = request.form
    decision = form.get("decision")  # "approve" or "reject"
    feedback = form.get("feedback", "").strip()

    if decision == "approve":
        result = await jobs_controller.approve_method(approval_token, approver=user, feedback=feedback)
        template = "admin/jobs/job_approval_success.html"
    elif decision == "reject":
        result = await jobs_controller.reject_method(approval_token, rejector=user, feedback=feedback)
        template = "admin/job_rejection_success.html"
    else:
        return render_template("admin/jobs/job_approval_error.html", message="Invalid decision"), 400

    if result.success:
        return render_template(template, job=result.data)
    else:
        return render_template("admin/jobs/job_approval_error.html", message=result.message), 400


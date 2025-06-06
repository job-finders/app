# src/routes/jobs_workflow.py

from flask import Blueprint, render_template, request, redirect, url_for, flash


from src.authentication import login_required, employer_login, system_admin_login, jobseeker_login
from src.database.models.jobs_model import Job, JobApplication
from src.database.models.users import User
from src.firewall.rate_limiting import rate_limit
from src.routes import flask_error_handler
from src.utils.route_helpers import get_controller

jobs_workflow_route = Blueprint("jobs_workflow", __name__, url_prefix="/dashboard/jobs")

@jobs_workflow_route.get("/create")
@rate_limit("20 per minute")
@flask_error_handler
@employer_login
async def show_create_form(user: User):
    """
    This route is used to render the form for creating a new job post.
    This shows to the employer or admin. a minimal form to create a job post.
    will call agents to create a full job definition.
    Upon form submission, the job will be created in the database.
    through the create_job method.

        Render form to create a new job.
    
    """
    return render_template("jobs_workflow/create.html", current_user=user)

@jobs_workflow_route.post("/create")
@rate_limit("20 per minute")
@flask_error_handler
@employer_login
async def create_job(user: User):
    """
        The Job Submission Workflow started at the Agent Routes - where a partial Job Definition was created.
        Then Passed to the Agent Controller to create a Full Job Detail Model.
        in this route, we handle the final submission of the job posting. 
        then create a job summary and seo description with another agent.

    This Method will Handle submission of new job posting to the Database.

            ensure jobs could be posted under this company -
            check verification status of employer profile
            check verification status of company_profile
        :param user_uid:
        :param job_data:
        :return:               
    """
    data = request.form.to_dict()
    try:
        #    Will Ensure company can post jobs - will check if employer profile is verified, 
        #    and if company profile is verified.
        company_controller = get_controller('company')

        job_data = await company_controller.post_job(user_uid=user.user_id, job_data=data)

        employer_agents_controller = get_controller('employer_agents')
        # async def create_job_summary(self, user_id: str, job_id: str) -> JobSummaryOutput:
        job: Job = await employer_agents_controller.create_job_summary(user_id=user.user_id, job_id=job_data.job_id)

    except ValueError as e:
        flash(str(e), "danger")
        return render_template("jobs_workflow/create.html", current_user=user, form_data=data)
    flash("Job created successfully!", "success")
    return redirect(url_for("jobs.job_details", job_id=job.job_id))


@jobs_workflow_route.get("/<string:job_id>/edit")
@rate_limit("10 per minute")
@flask_error_handler
@employer_login
async def show_edit_form(user: User, job_id: str):
    """
    This route is used to render the form for editing an existing none live job post.
        Render form to edit an existing job.
    """
    jobs_workflow_controller = get_controller('jobs_workflow')
    job = await jobs_workflow_controller.get_job_for_edit(job_id)
    if not job:
        flash("Job not found.", "warning")
        return redirect(url_for("jobs.list_jobs"))
    return render_template("jobs_workflow/edit.html", current_user=user, job=job)

@jobs_workflow_route.post("/<string:job_id>/edit")
@rate_limit("10 per minute")
@flask_error_handler
@employer_login
async def edit_job(user: User, job_id: str):
    """
    Once the Job is submitted to the Database, through the create_job method,
    but before it is approved, the job can be edited by the employer or admin.
    through this endpoint, 
        Handle submission of job updates.
    
    """
    data = request.form.to_dict()
    jobs_workflow_controller = get_controller('jobs_workflow')
    updated = await jobs_workflow_controller.update_job(job_id, data, editor=user)
    if not updated:
        flash("Failed to update job.", "danger")
        return redirect(url_for("jobs_workflow.show_edit_form", job_id=job_id))
    flash("Job updated successfully.", "success")
    return redirect(url_for("jobs.job_details", job_id=job_id))


@jobs_workflow_route.get("/<string:job_id>/archive")
@rate_limit("10 per minute")
@flask_error_handler
@employer_login
async def archive_job(user: User, job_id: str):
    """
        This route is used to archive a job post, making it no longer active.
    
    It is typically called by an administrator or workflow AI to remove a job listing from active status.
        
        The owner of the Job Post can also archive the job post.

        Another Archival process happens in the background when the Job Application is closed.
        when the job application is closed, the job post is archived. and this can be deduced from the job application status.
    Archive a job posting.
    
    """
    jobs_workflow_controller = get_controller('jobs_workflow')
    job = await jobs_workflow_controller.archive_job_listing(job_id)
    if not job:
        flash("Job not found or could not be archived.", "danger")
    else:
        flash("Job archived.", "success")
    return redirect(url_for("jobs.list_jobs"))


@jobs_workflow_route.get("/<string:job_id>/feature")
@rate_limit("30 per minute")
@flask_error_handler
@employer_login
async def feature_job(user: User, job_id: str):
    """
    This route is used to feature a job post, making it more visible on the platform.
        It is typically called by an administrator or workflow AI to promote a job listing.
    
    Must become a paid feature in the future.
    Mark a job as featured.
    """
    jobs_workflow_controller = get_controller('jobs_workflow')
    job = await jobs_workflow_controller.feature_job_listing(job_id)
    if not job:
        flash("Job not found or could not be featured.", "danger")
    else:
        flash("Job is now featured.", "success")
    return redirect(url_for("jobs.list_jobs"))


@jobs_workflow_route.get("/approve/<string:approval_token>")
@rate_limit("60 per minute")
@flask_error_handler
@system_admin_login
async def approve_job(user: User, approval_token: str):
    """
    This will be called by the system administrator or workflow AI in order to approve a job post.
    Approve a pending job post."""
    jobs_workflow_controller = get_controller('jobs_workflow')
    result = await jobs_workflow_controller.approve_job(approval_token, approver=user)
    if result.success:
        flash("Job approved!", "success")
        return render_template("jobs_workflow/approval_success.html", job=result.data)
    else:
        flash(result.message, "danger")
        return render_template("jobs_workflow/approval_error.html", message=result.message), 400


@jobs_workflow_route.get("/reject/<string:approval_token>")
@rate_limit("60 per minute")
@flask_error_handler
@system_admin_login
async def reject_job(user: User, approval_token: str):
    """
        This will be called by the system administrator or workflow AI in order to reject a job post.
        Reject a pending job post.
    
    """
    jobs_workflow_controller = get_controller('jobs_workflow')
    result = await jobs_workflow_controller.reject_job(approval_token, rejector=user)
    if result.success:
        flash("Job rejected.", "warning")
        return render_template("jobs_workflow/rejection_success.html", job=result.data)
    else:
        flash(result.message, "danger")
        return render_template("jobs_workflow/approval_error.html", message=result.message), 400


@jobs_workflow_route.post("/<string:job_id>/apply")
@rate_limit("120 per minute")
@flask_error_handler
@jobseeker_login
async def submit_application(user: User, job_id: str):
    """
    The workflow for submitting a job application. started at the agents routes, where a candidate 
    drafted the initial cover letter and check their compatibility to the job post.

    This route is designed to be used by candidates and is typically
        called from the job details page when a candidate applies submit an initial job application
    .
    Handle candidate applying to a job."""
    form = request.form.to_dict()
    try:
        jobs_workflow_controller = get_controller('jobs_workflow')
        application: JobApplication = await jobs_workflow_controller.submit_application(
            job_id=job_id, applicant=user, data=form
        )
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("jobs.job_details", job_id=job_id))
    flash("Application submitted! Good luck.", "success")
    return redirect(url_for("jobs.job_details", job_id=job_id))

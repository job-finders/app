# src/routes/jobs_workflow.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.routes import flask_error_handler
from src.authentication import admin_login, user_details
from src.database.models.users import User
from src.main import jobs_workflow_controller  # your workflow controller instance
from src.database.models.jobs_model import Job, JobApplication

jobs_workflow_bp = Blueprint("jobs_workflow", __name__, url_prefix="/jobs")

@jobs_workflow_bp.get("/create")
@flask_error_handler
@admin_login
async def show_create_form(user: User):
    """Render form to create a new job."""
    return render_template("jobs_workflow/create.html", current_user=user)

@jobs_workflow_bp.post("/create")
@flask_error_handler
@admin_login
async def create_job(user: User):
    """Handle submission of new job posting."""
    data = request.form.to_dict()
    try:
        job: Job = await jobs_workflow_controller.create_job(data, creator=user)
    except ValueError as e:
        flash(str(e), "danger")
        return render_template("jobs_workflow/create.html", current_user=user, form_data=data)
    flash("Job created successfully!", "success")
    return redirect(url_for("jobs.job_details", job_id=job.job_id))


@jobs_workflow_bp.get("/<string:job_id>/edit")
@flask_error_handler
@admin_login
async def show_edit_form(user: User, job_id: str):
    """Render form to edit an existing job."""
    job = await jobs_workflow_controller.get_job_for_edit(job_id)
    if not job:
        flash("Job not found.", "warning")
        return redirect(url_for("jobs.list_jobs"))
    return render_template("jobs_workflow/edit.html", current_user=user, job=job)

@jobs_workflow_bp.post("/<string:job_id>/edit")
@flask_error_handler
@admin_login
async def edit_job(user: User, job_id: str):
    """Handle submission of job updates."""
    data = request.form.to_dict()
    updated = await jobs_workflow_controller.update_job(job_id, data, editor=user)
    if not updated:
        flash("Failed to update job.", "danger")
        return redirect(url_for("jobs_workflow.show_edit_form", job_id=job_id))
    flash("Job updated successfully.", "success")
    return redirect(url_for("jobs.job_details", job_id=job_id))


@jobs_workflow_bp.get("/<string:job_id>/archive")
@flask_error_handler
@admin_login
async def archive_job(user: User, job_id: str):
    """Archive a job posting."""
    job = await jobs_workflow_controller.archive_job_listing(job_id)
    if not job:
        flash("Job not found or could not be archived.", "danger")
    else:
        flash("Job archived.", "success")
    return redirect(url_for("jobs.list_jobs"))


@jobs_workflow_bp.get("/<string:job_id>/feature")
@flask_error_handler
@admin_login
async def feature_job(user: User, job_id: str):
    """Mark a job as featured."""
    job = await jobs_workflow_controller.feature_job_listing(job_id)
    if not job:
        flash("Job not found or could not be featured.", "danger")
    else:
        flash("Job is now featured.", "success")
    return redirect(url_for("jobs.list_jobs"))


@jobs_workflow_bp.get("/approve/<string:approval_token>")
@flask_error_handler
@admin_login
async def approve_job(user: User, approval_token: str):
    """Approve a pending job post."""
    result = await jobs_workflow_controller.approve_job(approval_token, approver=user)
    if result.success:
        flash("Job approved!", "success")
        return render_template("jobs_workflow/approval_success.html", job=result.data)
    else:
        flash(result.message, "danger")
        return render_template("jobs_workflow/approval_error.html", message=result.message), 400


@jobs_workflow_bp.get("/reject/<string:approval_token>")
@flask_error_handler
@admin_login
async def reject_job(user: User, approval_token: str):
    """Reject a pending job post."""
    result = await jobs_workflow_controller.reject_job(approval_token, rejector=user)
    if result.success:
        flash("Job rejected.", "warning")
        return render_template("jobs_workflow/rejection_success.html", job=result.data)
    else:
        flash(result.message, "danger")
        return render_template("jobs_workflow/approval_error.html", message=result.message), 400


@jobs_workflow_bp.post("/<string:job_id>/apply")
@flask_error_handler
@user_details
async def submit_application(user: User, job_id: str):
    """Handle candidate applying to a job."""
    form = request.form.to_dict()
    try:
        application: JobApplication = await jobs_workflow_controller.submit_application(
            job_id=job_id, applicant=user, data=form
        )
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("jobs.job_details", job_id=job_id))
    flash("Application submitted! Good luck.", "success")
    return redirect(url_for("jobs.job_details", job_id=job_id))

from flask import Blueprint, render_template, request, redirect, url_for, flash
from pydantic import ValidationError

from src.database.models.jobs import JobApplication
from src.routes import flask_error_handler
from src.authentication import login_required
from src.database.models.users import User

from src.main import jobs_controller  # Controller for handling applications

jobseeker_applications_bp = Blueprint("jobseeker_applications", __name__, url_prefix="/jobseeker/applications")

@jobseeker_applications_bp.route("/submit/<job_id>", methods=["POST"])
@flask_error_handler
@login_required
async def submit_application(job_id: str, user: User):
    try:
        application_data = {
            "user_uid": user.uid,
            "job_id": job_id,
            "cover_letter": request.form.get("cover_letter", "").strip(),
            "resume_url": request.form.get("resume_url", "").strip()
        }

        job_application = JobApplication(**application_data)

        applied_job = await jobs_controller.apply_to_job(job_application=job_application)
        if applied_job:
            flash("Application submitted successfully.", "success")
            return redirect(url_for("jobseeker_applications.list_applications"))

        flash("There was a problem applying for this job please check if you have not already applied.", "success")
        return redirect(url_for("jobseeker_applications.list_applications"))

    except ValidationError as e:
        flash("There was a validation error while submitting your application.", "danger")
        return redirect(url_for("jobs.view_job", job_id=job_id))  # Or show a more specific error page

@jobseeker_applications_bp.route("/", methods=["GET"])
@flask_error_handler
@login_required
async def list_applications(user: User):
    applications = await jobs_controller.get_applied_jobs_for_user(user.uid)
    return render_template("jobseekers/applications/list.html", current_user=user, applications=applications)

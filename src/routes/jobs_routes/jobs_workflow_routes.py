# Standard Library
import json
import uuid

# Flask & Third-Party
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from pydantic import ValidationError
# Authentication
from src.authentication import (
    employer_login,
    system_admin_login,
    jobseeker_login,
    employer_job_access_required,
    require_billing_role,
)

# Controllers
from src.controllers.agents import EmployerAgentsController
from src.controllers.company import CompanyController
from src.controllers.jobs import JobsWorkflowController

# Domain Models
from src.database.models import (
    Job,
    JobApplication,
    JobEditableFields,
    ApplicationFunnelStats,
    JobStatusEnum,
    AIATSReport,
    User,
)

# Constants
from src.database.constants import utc_time
# Logger
from src.logger import init_logger
# Routes
from src.routes import flask_error_handler
# Services
from src.services.billing.billing_service import BillingTiersEnum
# Utilities
from src.utils.route_helpers import get_controller

# Firewall (commented for now)
# from src.firewall.rate_limiting import rate_limit

jobs_workflow_route = Blueprint("jobs_workflow", __name__, url_prefix="/dashboard/jobs")
workflow_logger = init_logger("workflow-route")



@jobs_workflow_route.get("/create")
@flask_error_handler
@employer_login
@require_billing_role()
async def show_create_form(user: User):
    """
    This route is used to render the form for creating a new job post.
    This shows to the employer or admin. a minimal form to create a job post.
    will call agents to create a full job definition.
    Upon form submission, the job will be created in the database.
    through the create_job method.
        Render form to create a new job.
    """
    context = dict(current_user=user, form_data={})
    return render_template("jobs_workflow/create.html", **context)


@jobs_workflow_route.post("/save-job-draft")
@flask_error_handler
@employer_login
@require_billing_role()
async def save_job_draft(user: User):
    """
        this will save a job draft based on user input
    :param user:
    :return:
    """
    try:
        job_draft_data = JobEditableFields(**request.form)
    except ValidationError as e:
        workflow_logger.error(str(e))
        return redirect("company.manage_jobs")

    job_workflow_controller: JobsWorkflowController = get_controller('jobs_workflow')
    company_controller: CompanyController = get_controller('company')
    employer_agents_controller: EmployerAgentsController = get_controller("employer_agents")

    employer = await company_controller.get_employer_by_uid(user_id=user.uid)
    if not employer:
        workflow_logger.info(f"Employer : {employer}")

    draft_job = Job(**job_draft_data.model_dump())
    draft_job.company_id = employer.company_id
    draft_job.employer_id = employer.employer_id

    draft_job = await job_workflow_controller.post_job_employer(employer=employer, job_data=draft_job)

    flash(message="created job draft to finish creating your job please click on the draft and then proceed",
          category="success")
    return redirect(url_for("company.manage_jobs"))

@jobs_workflow_route.post("/create")
@flask_error_handler
@employer_login
@require_billing_role()
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
        :param user:
        :return:
    """

    data = request.form.to_dict()
    try:
        # This Method works correctly.
        #    Will Ensure company can post jobs - will check if employer profile is verified, 
        #    and if company profile is verified.
        company_controller = get_controller('company')
        job_workflow_controller: JobsWorkflowController = get_controller('jobs_workflow')
        employer_agents_controller: EmployerAgentsController = get_controller("employer_agents")

        job_data = await company_controller.post_job(user_uid=user.user_id, job_data=data)
        # async def create_job_summary(self, user_id: str, job_id: str) -> JobSummaryOutput:
        # NOTE: Job Summary is saved automatically by this method.
        job_summary = await employer_agents_controller.create_job_summary(user_id=user.user_id, job_id=job_data.job_id)

    except ValueError as e:
        flash(str(e), "danger")
        return render_template("jobs_workflow/create.html", current_user=user, form_data=data)
    flash("Job created successfully!", "success")
    return redirect(url_for("jobs.job_details", job_id=job_data.job_id))


@jobs_workflow_route.get("/<string:job_id>/edit")
@flask_error_handler
@employer_login
@employer_job_access_required()
@require_billing_role()
async def show_edit_form(user: User, job_id: str):
    """
    This route is used to render the form for editing an existing none live job post.
        Render form to edit an existing job.
    """

    job_workflow_controller: JobsWorkflowController = get_controller('jobs_workflow')
    job: Job = await job_workflow_controller.get_job_details(job_id=job_id)

    if not job:
        flash("Job not found.", "warning")
        return redirect(url_for("jobs.list_jobs"))

    company_ats_controller = get_controller('employer_ats_optimization')
    job_details: Job = await job_workflow_controller.get_job_details(job_id=job_id)
    ats_report: AIATSReport = await company_ats_controller.compile_ats_report(job=job_details)
    # workflow_logger.info(f"Job details for editing: {job}")
    if ats_report:
        workflow_logger.info(f"ATS Report: {ats_report}")

    context = dict(current_user=user, job=job, report=ats_report)
    return render_template("jobs_workflow/job_editor/edit.html", **context)


@jobs_workflow_route.post("/<string:job_id>/edit")
@flask_error_handler
@employer_login
@employer_job_access_required()
@require_billing_role()
async def edit_job(user: User, job_id: str):
    form = request.form.to_dict()

    # 1) convert JSON strings to Python objects
    form["required_skills"] = json.loads(form.get("required_skills") or "[]")
    form["preferred_skills"] = json.loads(form.get("preferred_skills") or "[]")
    form["education_requirements"] = json.loads(form.get("education_requirements") or "{}")
    workflow_logger.info(f"FORM DATA : {form}")
    # 2) let Pydantic validate the rest
    job_details = JobEditableFields(**form)

    jobs_workflow_controller = get_controller("jobs_workflow")
    updated_job = await jobs_workflow_controller.update_job(job_id=job_id,
                                                            updated_job=job_details)

    flash("Job updated successfully." if updated_job else "Failed to update job",
          "success" if updated_job else "warning")
    return redirect(url_for("jobs_workflow.show_edit_form", job_id=job_id))


@jobs_workflow_route.post("/<string:job_id>/calculate-ats")
@flask_error_handler
@employer_login
@employer_job_access_required()
async def calculate_ats(user: User, job_id: str):
    """
        This route is used to calculate ATS metrics for a job post.
        the ATS is based on industry standards and job requirements.
        Receives form fields, returns rendered ATS sidebar (HTML fragment).
    """
    workflow_logger.info(f"inside calculate ats : {job_id}")
    jobs_workflow_controller = get_controller("jobs_workflow")
    company_ats_controller = get_controller('employer_ats_optimization')
    job_details: Job = await jobs_workflow_controller.get_job_details(job_id=job_id)
    ats_report: AIATSReport = await company_ats_controller.compile_ats_report(job=job_details)
    if ats_report is None:
        return {}, 404

    return ats_report.model_dump(), 200


@jobs_workflow_route.get("/<string:job_id>/archive")
@flask_error_handler
@employer_login
@employer_job_access_required()
@require_billing_role()
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

    job = await jobs_workflow_controller.archive_job_listing(job_id=job_id)

    if not job:
        flash("Job not found or could not be archived.", "danger")
    else:
        flash("Job archived.", "success")
    return redirect(url_for("jobs.list_jobs"))


@jobs_workflow_route.get("/<string:job_id>/feature")
@flask_error_handler
@employer_login
@employer_job_access_required()
@require_billing_role(minimum=BillingTiersEnum.Growth.value)
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
@flask_error_handler
@system_admin_login
async def approve_job(user: User, approval_token: str):
    """
    This will be called by the system administrator or workflow AI in order to approve a job post.
    Approve a pending job post."""
    jobs_workflow_controller = get_controller('jobs_workflow')
    result = await jobs_workflow_controller.approve_jobs(approval_token, )
    if result.success:
        flash("Job approved!", "success")
        return render_template("jobs_workflow/approval_success.html", job=result.data)
    else:
        flash(result.message, "danger")
        return render_template("jobs_workflow/approval_error.html", message=result.message), 400


@jobs_workflow_route.get("/reject/<string:approval_token>")
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


@jobs_workflow_route.get("/<string:job_id>/insights")
@employer_login
@require_billing_role()
@employer_job_access_required()
@flask_error_handler
async def job_insights(user: User, job_id: str):
    """
        will retrieve job complete details so job insights and stats can be viewed
    :param job_id:
    :param user:
    :return:
    """
    jobs_workflow_controller: JobsWorkflowController = get_controller('jobs_workflow')
    job_details: Job = await jobs_workflow_controller.get_job_details(job_id=job_id)
    application_funnel_stats: ApplicationFunnelStats = await jobs_workflow_controller.get_application_funnel_stats(
        job_id=job_id)
    context = dict(current_user=user, job=job_details, application_funnel_stats=application_funnel_stats)

    return render_template('jobs_workflow/job_metrics.html', **context)


@jobs_workflow_route.get("/<string:job_id>/view-applications")
@employer_login
@require_billing_role()
@employer_job_access_required()
@flask_error_handler
async def view_job_applications(user: User, job_id: str):
    jobs_workflow_controller: JobsWorkflowController = get_controller('jobs_workflow')

    job_applications_details = await jobs_workflow_controller.get_application_funnel_stats(job_id=job_id)
    if job_applications_details is None:
        job_applications_details = ApplicationFunnelStats(
            views=0, started=0, completed=0, qualified=0,
            interviewed=0, hired=0, rejected=0, conversion_rate=0.0
        )

    job, job_applications_list = await jobs_workflow_controller.get_job_applications(job_id=job_id) or []

    if not job_applications_list:
        # 🧪 Generate 3 fake applications for testing
        from src.routes.fake_data import generate_fake_job_application
        job_applications_list = [
            generate_fake_job_application(job_id=job_id),
            generate_fake_job_application(job_id=job_id),
            generate_fake_job_application(job_id=job_id),
            generate_fake_job_application(job_id=job_id),
            generate_fake_job_application(job_id=job_id),
            generate_fake_job_application(job_id=job_id),
            generate_fake_job_application(job_id=job_id),
            generate_fake_job_application(job_id=job_id),
            generate_fake_job_application(job_id=job_id),

        ]
    job_application = job_applications_list[-1]
    workflow_logger.info(job_application)
    context = dict(
        job=job,
        job_id=job_id,
        stats=job_applications_details,
        job_applications=job_applications_list,
        current_user=user
    )
    return render_template("jobs_workflow/job_applications.html", **context)

@jobs_workflow_route.route("/<string:job_id>/update-status", methods=["POST"])
@employer_login
@require_billing_role()
@employer_job_access_required()
@flask_error_handler
async def update_status(user: User, job_id: str):
    """
    Change the status of an existing job.

    Payload   : {"status": "active" | "closed" | "draft" | "pending"}
    Response  : 204 No Content on success
    """
    workflow_logger.info(f"Received request to update job {job_id} status")

    data = request.get_json(silent=True)
    workflow_logger.info(f"Updating job {job_id} status with data: {data}")

    if not data or "status" not in data:
        workflow_logger.error("Missing 'status' field in request data")
        return jsonify(error="Missing JSON field 'status'"), 400

    new_status = data["status"]
    if new_status.casefold() not in JobStatusEnum.members_list():
        workflow_logger.error(f"Invalid status value: {new_status}")
        return jsonify(error="Invalid status value"), 400

    jobs_workflow_controller: JobsWorkflowController = get_controller('jobs_workflow')
    if new_status.casefold() == JobStatusEnum.PENDING_APPROVAL.value:
        # Employer Requesting to activate job
        status_update_result = await jobs_workflow_controller.create_approval_request(job_id=job_id)
        workflow_logger.info(f"Approval request created: {status_update_result}")

    elif new_status.casefold() == JobStatusEnum.CLOSED.value:
        # The User Intends to close this job
        status_update_result = await jobs_workflow_controller.employer_close_job(job_id=job_id)
        workflow_logger.info(f"Job activated: {status_update_result}")
    return "", 204


@jobs_workflow_route.get("/<string:job_id>/toggle-featured")
@employer_login
@require_billing_role()
@employer_job_access_required()
@flask_error_handler
async def toggle_featured(user: User):
    """

    :param user:
    :return:
    """
    pass

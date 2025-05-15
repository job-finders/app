import asyncio

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from pydantic import ValidationError

from src.database.models.jobs import ATSReport
from src.database.models.resume import JobSeekerCV
from src.logger import init_logger
from src.database.models.jobs import JobApplication, Job
from src.routes import flask_error_handler
from src.main import resume_controller, ats_controller, jobs_controller
from src.database.models.users import User
from src.authentication import login_required

jobseeker_applications_route = Blueprint("jobseeker_applications", __name__, url_prefix="/jobseeker/applications")
applications_logger = init_logger("Job-Applications")

async def get_location_options(user_id: str, cv_ids: list[str]) -> list[str]:
    """
    Aggregates location options from various jobseeker data sources.

    This combines locations from the jobseeker's profile, their CVs,
    and available job locations to assist in tailoring applications.

    :param user_id: Unique ID of the current jobseeker.
    :param cv_ids: List of CV IDs associated with the jobseeker.
    :return: A deduplicated list of all relevant location strings.
    """

    profile_locations = await resume_controller.get_preferred_locations_from_profile(user_id)
    cv_locations = await resume_controller.get_locations_from_cvs(cv_ids)
    job_locations = await jobs_controller.get_job_location()
    combined = list(set(profile_locations + cv_locations))
    return combined


@jobseeker_applications_route.route('/api/ats-check', methods=['POST'])
@login_required
async def api_ats_check(user: User):
    """
    Perform an ATS (Applicant Tracking System) compatibility check.

    This endpoint is used to evaluate how well a specific CV and optional
    cover letter match a job description. Returns structured ATS analysis.

    Required POST Parameters:
    - cv_id: ID of the CV to evaluate.
    - cover_letter: (optional) Cover letter text to include in evaluation.

    Query Params:
    - job_id: The job the user is applying for.

    :param user: Authenticated user via @login_required.
    :return: JSON ATS score report or error message.
    """

    try:
        data = request.form
        job_id = request.args.get("job_id")
        cv_id = data.get("cv_id")
        cover_letter = data.get("cover_letter", "")

        if not job_id or not cv_id:
            return jsonify({"error": "Missing required parameters"}), 400

        job: Job = await jobs_controller.get_job_by_id(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        ats_report: ATSReport = await ats_controller.evaluate_application(job=job,cv_id=cv_id,cover_letter=cover_letter)

        return jsonify(ats_report.model_dump())

    except Exception as e:
        applications_logger.error(f"ATS Check Error: {str(e)}")
        return jsonify({"error": "Failed to process ATS check"}), 500


@jobseeker_applications_route.route('/api/cover-draft', methods=['POST'])
@login_required
async def api_cover_draft(user: User):
    """
    Generate a cover letter draft using AI tools based on CV and job data.

    This endpoint fetches job and CV information to automatically create
    a tailored draft cover letter for the jobseeker.

    Required POST Parameters:
    - cv_id: ID of the selected CV.

    Query Params:
    - job_id: The job to tailor the cover letter for.

    :param user: Authenticated jobseeker.
    :return: JSON response with AI-generated cover letter draft or error.
    """

    try:
        data = request.form
        job_id = request.args.get("job_id")
        cv_id = data.get("cv_id")

        job: Job = await jobs_controller.get_job_by_id(job_id)
        cv: JobSeekerCV = await resume_controller.get_cv_by_id(cv_id)

        draft: str = await ats_controller.generate_cover_letter(job, cv)
        return jsonify({"draft": draft})

    except Exception as e:
        applications_logger.error(f"Cover Draft Error: {str(e)}")
        return jsonify({"error": "Failed to generate cover draft"}), 500

@jobseeker_applications_route.route('/jobs/aaply/<string:job_id>', methods=['GET'])
@login_required
async def apply_for_job(user: User, job_id: str):
    """
    Job application landing page (GET).

    This is triggered when a jobseeker clicks "Apply" on a job post.
    It gathers and displays all data needed for a successful application:
      - Suggested CV
      - ATS scores
      - AI-generated cover letter
      - Salary recommendation
      - Location preferences

    This process uses ATS tools and AI to maximize chances of success.

    :param user: Authenticated jobseeker.
    :param job_id: The job ID for the application.
    :return: Rendered application page template.
    """

    job_details: Job = await jobs_controller.get_job_by_id(job_id)
    if not job_details:
        flash("Job not found", "danger")
        # Should Preferably redirect back to job lists.
        return redirect(url_for("home.get_home"))

    cvs: list[JobSeekerCV] = await resume_controller.list_cvs_for_user(user_uid=user.uid)
    if not cvs:
        flash("You need to upload a CV before applying", "warning")
        return redirect(url_for("jobseeker_cv.list_cvs"))

    # Generate ATS analysis
    best_ats_report: ATSReport = await ats_controller.generate_cvs_job_description_ats_report(
        job_id=job_id,
        job_description=job_details.description,
        cvs=cvs
    )
    # Get salary recommendation - if JobSeeker is Professional set the AI Prompt to True
    salary_recommendation = await ats_controller.recommend_salary(job=job_details, use_ai=False)

    # Generate initial cover letter draft
    primary_cv = next((cv for cv in cvs if cv.cv_id == best_ats_report.cv_id), cvs[0])
    cover_draft = await ats_controller.generate_cover_letter(job_details, primary_cv)

    # Add ats_score to each CV before rendering template
    async def enrich_cv_with_score(cv):
        ats_report: ATSReport = await ats_controller.evaluate_application(
            job=job_details,
            cv_id=cv.cv.id,
            cover_letter=cover_draft if cv.cv_id == primary_cv.cv_id else ""
        )
        cv.ats_score = ats_report.score
        return cv

    cvs = await asyncio.gather(*(enrich_cv_with_score(cv) for cv in cvs))

    # Step 1: Load locations from the user profile + existing CVs
    cv_ids = [cv.cv_id for cv in cvs]
    user_locations = await get_location_options(user_id=user.uid, cv_ids=cv_ids)

    # Step 2: Get job location if available and not already included
    job_location = job_details.location  # or job_details.get("locations", [])
    if job_location and job_location not in user_locations:
        user_locations.append(job_location)

    locations = user_locations

    context = {
        'job': job_details,
        'cvs': cvs,
        'best_ats_report': best_ats_report,
        "selected_cv_id": best_ats_report.cv_id,
        'ats_score': best_ats_report.score,
        'matched_keywords': best_ats_report.matched_keywords,
        'missing_keywords': best_ats_report.missing_keywords,
        'cover_letter_feedback': best_ats_report.feedback,

        'salary_recommendation': salary_recommendation,
        'locations': locations,
        'current_user': user,
        'cover_letter': cover_draft,
    }

    return render_template('jobseekers/apply.html', **context)


@jobseeker_applications_route.route("/submit/<job_id>", methods=["POST"])
@flask_error_handler
@login_required
async def submit_application(job_id: str, user: User):
    """
    Finalizes and submits a job application.

    Accepts form data including selected CV, cover letter, salary expectations,
    and other metadata, and persists the application record.

    Form Parameters:
    - cv_id: Selected CV ID
    - cover_letter: Cover letter text
    - notes: Optional jobseeker notes
    - expected_salary: Desired salary
    - preferred_start_date: Availability to start
    - preferred_location: Preferred work location
    - ats_score: ATS score of this application
    - ats_report_id: Related ATS report ID

    :param job_id: Job being applied to.
    :param user: Authenticated jobseeker.
    :return: Redirect to application list or error page.
    """

    try:
        application_data = {
            "user_uid": user.uid,
            "job_id": job_id,
            "cover_letter": request.form.get("cover_letter", "").strip(),
            "cv_id": request.form.get("cv_id", ""),
            "notes" : request.form.get('notes'),
            "expected_salary": request.form.get("expected_salary"),
            "preferred_start_date": request.form.get("preferred_start_date"),
            "preferred_location": request.form.get("preferred_location"),
            "ats_score": request.form.get("ats_score"),
            "ats_report_id": request.form.get("ats_report_id")
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


@jobseeker_applications_route.route("/withdraw-application/<string:application_id>", methods=["GET"])
@flask_error_handler
@login_required
async def withdraw_application(user: User, application_id: str):
    """
    Withdraw a submitted job application.

    Ensures the user is authorized to withdraw their application and handles
    application status updates accordingly.

    :param user: Authenticated user from decorator.
    :param application_id: UUID of the job application to withdraw.
    :return: Redirect to application list with appropriate flash message.
    """

    """
    Handle job application withdrawal with proper authorization and state management
    :param user: Authenticated user from decorator
    :param application_id: UUID of the application to withdraw
    """
    # Get application with basic validation
    application = await jobs_controller.get_job_application_by_id(application_id)

    if not application:
        flash("Application not found", "danger")
        return redirect(url_for("jobseeker_applications.list_applications"))

    # Authorization check
    if application.user_uid != user.uid:
        flash("You are not authorized to withdraw this application", "danger")
        return redirect(url_for("jobseeker_applications.list_applications"))

    # State validation
    if application.status == "withdrawn":
        flash("This application was already withdrawn", "warning")
        return redirect(url_for("jobseeker_applications.list_applications"))

    # Process withdrawal
    success = await jobs_controller.withdraw_job_application(application_id)

    if success:
        flash("Application successfully withdrawn", "success")
        # Consider adding audit log here
    else:
        flash("Failed to process withdrawal - please try again", "danger")

    return redirect(url_for("jobseeker_applications.list_applications"))


@jobseeker_applications_route.route("/", methods=["GET"])
@flask_error_handler
@login_required
async def list_applications(user: User):
    """
    Display a list of all jobs the user has applied to.

    This view shows application history, statuses, and allows further
    interactions like withdrawal or review.

    :param user: Authenticated jobseeker.
    :return: Rendered application history template.
    """

    applications = await jobs_controller.get_applied_jobs_for_user(user.uid)
    context = dict(current_user=user, applications=applications)
    return render_template("jobseekers/applications/list.html", **context)

@jobseeker_applications_route.route("/<string:application_id>", methods=["GET"])
@flask_error_handler
@login_required
async def view_application(application_id: str, user: User):
    """
    View a specific job application by its ID. Shows job details, submitted CV, cover letter,
    ATS feedback, and current status.

    :param application_id: UUID of the job application
    :param user: Logged-in jobseeker
    """
    # Fetch application
    application: JobApplication = await jobs_controller.get_job_application_by_id(application_id)

    if not application:
        flash("Application not found", "danger")
        return redirect(url_for("jobseeker_applications.list_applications"))

    # Authorization check
    if application.user_uid != user.uid:
        flash("You are not authorized to view this application", "danger")
        return redirect(url_for("jobseeker_applications.list_applications"))

    # Fetch related data
    job: Job = await jobs_controller.get_job_by_id(application.job_id)
    ats_report: ATSReport | None = await ats_controller.get_ats_report_by_id(application.ats_report_id)
    submitted_cv: JobSeekerCV | None = await resume_controller.get_cv_by_id(application.cv_id)

    context = {
        "application": application,
        "job": job,
        "ats_report": ats_report,
        "cv": submitted_cv,
        "current_user": user,
    }

    return render_template("jobseekers/applications/view.html", **context)


@jobseeker_applications_route.route("/<string:application_id>/edit", methods=["GET"])
@flask_error_handler
@login_required
async def edit_application(application_id: str, user: User):
    application = await jobs_controller.get_job_application_by_id(application_id)

    if not application or application.user_uid != user.uid:
        flash("Application not found or not authorized", "danger")
        return redirect(url_for("jobseeker_applications.list_applications"))

    if application.status != "draft":
        flash("Only draft applications can be edited", "warning")
        return redirect(url_for("jobseeker_applications.view_application", application_id=application.application_id))

    job = await jobs_controller.get_job_by_id(application.job_id)
    cvs = await resume_controller.get_user_cvs(user.uid)

    context = {
        "application": application,
        "job": job,
        "cv_options": cvs,
        "selected_cv_id": application.cv_id,
        "cover_letter": application.cover_letter or "",
    }
    return render_template("jobseekers/applications/edit.html", **context)


@jobseeker_applications_route.route("/<string:application_id>/edit", methods=["POST"])
@flask_error_handler
@login_required
async def submit_edited_application(application_id: str, user: User):
    form = await request.form
    selected_cv_id = form.get("cv_id")
    cover_letter = form.get("cover_letter")

    application = await jobs_controller.get_job_application_by_id(application_id)

    if not application or application.user_uid != user.uid or application.status != "draft":
        flash("Unauthorized or invalid application", "danger")
        return redirect(url_for("jobseeker_applications.list_applications"))

    await jobs_controller.update_draft_application(
        application_id=application.application_id,
        updated_data={
            "cv_id": selected_cv_id,
            "cover_letter": cover_letter,
        }
    )

    flash("Application updated successfully", "success")
    return redirect(url_for("jobseeker_applications.view_application", application_id=application.application_id))


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
    profile_locations = await resume_controller.get_preferred_locations_from_profile(user_id)
    cv_locations = await resume_controller.get_locations_from_cvs(cv_ids)
    job_locations = await jobs_controller.get_job_location()
    combined = list(set(profile_locations + cv_locations))
    return combined


@jobseeker_applications_route.route('/api/ats-check', methods=['POST'])
@login_required
async def api_ats_check(user: User):
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
        landing page for job applications when a jobseeker click on APPLY Button on our portal they come here
        this is where we use our tools to assist on the job application process.
        1. Create Cover Letter
        2. Help Select the Best CV For the Application
        3. Suggest Improvements on CV if the CV Falls short
        4. all the while USE AI Based Tools and ATS Tools to improve the likelihood of a successful application
    :param user:
    :param job_id:
    :return:
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
    applications = await jobs_controller.get_applied_jobs_for_user(user.uid)
    context = dict(current_user=user, applications=applications)
    return render_template("jobseekers/applications/list.html", **context)

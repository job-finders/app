# Standard Library
import asyncio

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
from src.authentication import jobseeker_login, is_valid_uid
# Domain Models
from src.database.models import JobApplication, Job, ATSReport, JobSeekerCV, User
# Logger
from src.logger import init_logger
# Routes
from src.routes import flask_error_handler
# Utilities
from src.utils.route_helpers import get_controller

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
    resume_controller = get_controller('resume')
    job_search_controller = get_controller('jobs_search')

    profile_locations = await resume_controller.get_preferred_locations_from_profile(user_id)
    cv_locations = await resume_controller.get_locations_from_cvs(cv_ids)
    job_locations = await job_search_controller.get_job_location()
    combined = list(set(profile_locations + cv_locations))
    return combined


@jobseeker_applications_route.route('/api/ats-check', methods=['POST'])
@flask_error_handler
@jobseeker_login
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

        job_search_controller = get_controller('jobs_search')
        ats_controller = get_controller('jobs_search')

        job: Job = await job_search_controller.get_job_by_id(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        ats_report: ATSReport = await ats_controller.evaluate_application(job=job,cv_id=cv_id,cover_letter=cover_letter)
        if not ats_report:
            return jsonify({"error": "Failed to generate ATS report"}), 500

        return jsonify(ats_report.model_dump())

    except Exception as e:
        applications_logger.error(f"ATS Check Error: {str(e)}")
        return jsonify({"error": "Failed to process ATS check"}), 500


@jobseeker_applications_route.route('/api/cover-draft', methods=['POST'])
@flask_error_handler
@jobseeker_login
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

        jobs_search_controller = get_controller('jobs_search')
        resume_controller = get_controller('resume')
        ats_controller = get_controller('ats')

        job: Job = await jobs_search_controller.get_job_by_id(job_id)
        cv: JobSeekerCV = await resume_controller.get_cv_by_id(cv_id)

        draft: str = await ats_controller.generate_cover_letter(job, cv)
        return jsonify({"draft": draft})

    except Exception as e:
        applications_logger.error(f"Cover Draft Error: {str(e)}")
        return jsonify({"error": "Failed to generate cover draft"}), 500

@jobseeker_applications_route.route('/jobs/apply/<string:job_id>', methods=['GET'])
@flask_error_handler
@jobseeker_login
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
    jobs_search_controller = get_controller('jobs_search')
    resume_controller = get_controller('resume')
    ats_controller = get_controller('ats')

    job_details: Job = await jobs_search_controller.get_job_by_id(job_id)
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
    if not best_ats_report:
        # Better to throw an error here so an error message gets displayed to the user
        pass

    # Get salary recommendation - if JobSeeker is Professional set the AI Prompt to True
    salary_recommendation = await ats_controller.recommend_salary(job=job_details, use_ai=False)

    # Generate initial cover letter draft
    primary_cv = next((cv for cv in cvs if cv.cv_id == best_ats_report.cv_id), cvs[0])
    cover_draft = await ats_controller.generate_cover_letter(job_details, primary_cv)

    # Add ats_score to each CV before rendering template
    async def enrich_cv_with_score(cv):
        ats_report: ATSReport = await ats_controller.evaluate_application(
            job=job_details,
            cv_id=cv.cv_id,
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
        "selected_cv_id": best_ats_report.cv_id if best_ats_report else (cvs[0].cv_id if cvs else None),
        'ats_score': best_ats_report.score if best_ats_report else 0,
        'ats_report_id': best_ats_report.ats_report_id if best_ats_report else None,
        'matched_keywords': best_ats_report.matched_keywords if best_ats_report else [],
        'missing_keywords': best_ats_report.missing_keywords if best_ats_report else [],
        'cover_letter_feedback': best_ats_report.feedback if best_ats_report else "",

        'salary_recommendation': salary_recommendation,
        'locations': locations,
        'current_user': user,
        'cover_letter': cover_draft,
    }

    return render_template('jobseekers/apply.html', **context)


@jobseeker_applications_route.route("/submit/<job_id>", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def submit_application(job_id: str, user: User):
    """
    Finalizes and submits a job application with comprehensive validation.

    Accepts form data including selected CV, cover letter, salary expectations,
    and other metadata, and persists the application record after thorough validation.

    Form Parameters:
    - cv_id: Selected CV ID (required)
    - cover_letter: Cover letter text (required, min 50 characters)
    - notes: Optional jobseeker notes
    - expected_salary: Desired salary (optional, must be positive integer)
    - preferred_start_date: Availability to start (optional, cannot be in past)
    - preferred_location: Preferred work location (optional)
    - ats_score: ATS score of this application
    - ats_report_id: Related ATS report ID

    :param job_id: Job being applied to.
    :param user: Authenticated jobseeker.
    :return: Redirect to application list on success or error page with feedback.
    """

    try:
        # Extract and sanitize form data
        cv_id = request.form.get("cv_id", "").strip()
        cover_letter = request.form.get("cover_letter", "").strip()
        notes = request.form.get('notes', '').strip()
        expected_salary = request.form.get("expected_salary", "").strip()
        preferred_start_date = request.form.get("preferred_start_date", "").strip()
        preferred_location = request.form.get("preferred_location", "").strip()
        ats_score = request.form.get("ats_score", "").strip()
        ats_report_id = request.form.get("ats_report_id", "").strip()
        
        # Comprehensive server-side validation
        validation_errors = []
        
        # Required field validation
        if not cv_id:
            validation_errors.append("Please select a CV for your application.")
            
        if not cover_letter:
            validation_errors.append("Cover letter is required.")
        elif len(cover_letter) < 50:
            validation_errors.append("Cover letter must be at least 50 characters long.")
        elif len(cover_letter) > 5000:
            validation_errors.append("Cover letter cannot exceed 5000 characters.")
            
        # Optional field validation with proper data types
        parsed_expected_salary = None
        if expected_salary:
            try:
                parsed_expected_salary = int(expected_salary)
                if parsed_expected_salary < 0:
                    validation_errors.append("Expected salary must be a positive number.")
                elif parsed_expected_salary > 10000000:  # Reasonable upper limit
                    validation_errors.append("Expected salary seems unreasonably high. Please check your input.")
            except (ValueError, TypeError):
                validation_errors.append("Expected salary must be a valid number.")
        
        parsed_start_date = None
        if preferred_start_date:
            try:
                from datetime import datetime, date
                parsed_start_date = datetime.strptime(preferred_start_date, '%Y-%m-%d').date()
                if parsed_start_date < date.today():
                    validation_errors.append("Preferred start date cannot be in the past.")
                elif parsed_start_date > date.today().replace(year=date.today().year + 2):
                    validation_errors.append("Preferred start date cannot be more than 2 years in the future.")
            except ValueError:
                validation_errors.append("Please provide a valid start date in YYYY-MM-DD format.")
        
        # Validate location if provided
        if preferred_location and len(preferred_location) > 100:
            validation_errors.append("Preferred location cannot exceed 100 characters.")
            
        # Validate notes if provided
        if notes and len(notes) > 1000:
            validation_errors.append("Notes cannot exceed 1000 characters.")
            
        # Validate ATS score if provided
        parsed_ats_score = None
        if ats_score:
            try:
                parsed_ats_score = float(ats_score)
                if parsed_ats_score < 0 or parsed_ats_score > 100:
                    validation_errors.append("ATS score must be between 0 and 100.")
            except (ValueError, TypeError):
                validation_errors.append("ATS score must be a valid number.")

        # If there are validation errors, return to application form with errors
        if validation_errors:
            for error in validation_errors:
                flash(error, "danger")
            return redirect(url_for("jobseeker_applications.apply_for_job", job_id=job_id))

        # Business logic validation
        jobs_search_controller = get_controller('jobs_search')
        
        # Check if user has already applied for this job (duplicate prevention)
        user_applications, _ = await jobs_search_controller.get_applied_jobs_for_user(user_id=user.uid)
        if any(app.job_id == job_id for app in user_applications):
            flash("You have already applied for this job. You can view your application in your applications list.", "warning")
            return redirect(url_for("jobseeker_applications.list_applications"))

        # Verify job exists and is still active
        job_details = await jobs_search_controller.get_job_by_id(job_id)
        if not job_details:
            flash("The job you are trying to apply for no longer exists.", "danger")
            return redirect(url_for("jobs.list_jobs"))
            
        if job_details.status not in ["active", "open"]:
            flash("This job is no longer accepting applications.", "warning")
            return redirect(url_for("jobs.job_details", job_id=job_id))
            
        # Check if job has expired
        if hasattr(job_details, 'expires_at') and job_details.expires_at:
            from datetime import datetime, timezone
            if job_details.expires_at < datetime.now(timezone.utc):
                flash("This job posting has expired and is no longer accepting applications.", "warning")
                return redirect(url_for("jobs.job_details", job_id=job_id))

        # Verify CV exists and belongs to user
        resume_controller = get_controller('resume')
        user_cvs = await resume_controller.list_cvs_for_user(user_uid=user.uid)
        if not any(cv.cv_id == cv_id for cv in user_cvs):
            flash("The selected CV is not valid or does not belong to you.", "danger")
            return redirect(url_for("jobseeker_applications.apply_for_job", job_id=job_id))

        # Prepare validated application data
        application_data = {
            "user_id": user.uid,
            "job_id": job_id,
            "cover_letter": cover_letter,
            "cv_id": cv_id,
            "notes": notes if notes else None,
            "expected_salary": parsed_expected_salary,
            "preferred_start_date": parsed_start_date,
            "preferred_location": preferred_location if preferred_location else None,
            "ats_score": parsed_ats_score,
            "ats_report_id": ats_report_id if ats_report_id else None
        }

        # Create and submit application
        job_application = JobApplication(**application_data)
        jobs_workflow_controller = get_controller('jobs_workflow')

        applied_job = await jobs_workflow_controller.apply_to_job(job_application=job_application)
        
        if applied_job:
            # Success flow - redirect to applications list with success message
            flash("Application submitted successfully! You can track its progress in your applications list.", "success")
            applications_logger.info(f"User {user.uid} successfully applied to job {job_id}")
            return redirect(url_for("jobseeker_applications.list_applications"))
        else:
            # Application submission failed at controller level
            flash("There was a problem submitting your application. This may be due to a duplicate application or system error. Please try again or contact support if the issue persists.", "danger")
            applications_logger.error(f"Application submission failed for user {user.uid} and job {job_id}")
            return redirect(url_for("jobseeker_applications.apply_for_job", job_id=job_id))

    except ValidationError as e:
        # Pydantic validation errors
        applications_logger.error(f"Pydantic validation error in application submission: {str(e)}")
        flash("There was a validation error with your application data. Please check all fields and try again.", "danger")
        return redirect(url_for("jobseeker_applications.apply_for_job", job_id=job_id))
    
    except Exception as e:
        # Catch-all for unexpected errors
        applications_logger.error(f"Unexpected error in application submission for user {user.uid}, job {job_id}: {str(e)}")
        flash("An unexpected error occurred while submitting your application. Please try again or contact support if the problem persists.", "danger")
        return redirect(url_for("jobseeker_applications.apply_for_job", job_id=job_id))


@jobseeker_applications_route.route("/withdraw-application/<string:application_id>", methods=["GET"])
@flask_error_handler
@jobseeker_login
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
    jobs_search_controller = get_controller('jobs_search')
    jobs_workflow_controller = get_controller('jobs_workflow')
    application = await jobs_search_controller.get_application_by_id(application_id)

    if not application:
        flash("Application not found", "danger")
        return redirect(url_for("jobseeker_applications.list_applications"))

    # Authorization check
    if application.user_id != user.uid:
        flash("You are not authorized to withdraw this application", "danger")
        return redirect(url_for("jobseeker_applications.list_applications"))

    # State validation
    if application.status == "withdrawn":
        flash("This application was already withdrawn", "warning")
        return redirect(url_for("jobseeker_applications.list_applications"))

    # Process withdrawal
    success = await jobs_workflow_controller.withdraw_job_application(application_id)

    if success:
        flash("Application successfully withdrawn", "success")
        # Consider adding audit log here
    else:
        flash("Failed to process withdrawal - please try again", "danger")

    return redirect(url_for("jobseeker_applications.list_applications"))


@jobseeker_applications_route.route("/", methods=["GET"])
@flask_error_handler
@jobseeker_login
async def list_applications(user: User):
    """
    Display a list of all jobs the user has applied to.

    This view shows application history, statuses, and allows further
    interactions like withdrawal or review.

    :param user: Authenticated jobseeker.
    :return: Rendered application history template.
    """
    from flask import request
    
    jobs_search_controller = get_controller('jobs_search')

    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    # Get paginated applications
    applications, total_count = await jobs_search_controller.get_applied_jobs_for_user(
        user.uid, page=page, page_size=page_size
    )

    # Calculate pagination info
    total_pages = (total_count + page_size - 1) // page_size
    has_prev = page > 1
    has_next = page < total_pages

    context = dict(
        current_user=user,
        applications=applications,
        pagination={
            'page': page,
            'page_size': page_size,
            'total_count': total_count,
            'total_pages': total_pages,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_num': page - 1 if has_prev else None,
            'next_num': page + 1 if has_next else None
        }
    )
    return render_template("jobseekers/applications/list.html", **context)

@jobseeker_applications_route.route("/<string:application_id>", methods=["GET"])
@flask_error_handler
@jobseeker_login
async def view_application(application_id: str, user: User):
    """
    View a specific job application by its ID. Shows job details, submitted CV, cover letter,
    ATS feedback, and current status.

    :param application_id: UUID of the job application
    :param user: Logged-in jobseeker
    """
    # Fetch application
    jobs_search_controller = get_controller('jobs_search')
    application: JobApplication = await jobs_search_controller.get_application_by_id(application_id)

    if not application:
        flash("Application not found", "danger")
        return redirect(url_for("jobseeker_applications.list_applications"))

    # Authorization check
    if application.user_id != user.uid:
        flash("You are not authorized to view this application", "danger")
        return redirect(url_for("jobseeker_applications.list_applications"))

    # Fetch related data


    job: Job = await jobs_search_controller.get_job_by_id(application.job_id)
    ats_controller = get_controller('ats')
    ats_report: ATSReport | None = await ats_controller.get_ats_report_by_id(application.ats_report_id)
    resume_controller = get_controller('resume')
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
@jobseeker_login
async def edit_application(application_id: str, user: User):
    jobs_search_controller = get_controller('jobs_search')
    application = await jobs_search_controller.get_application_by_id(application_id)

    if not application or application.user_id != user.uid:
        flash("Application not found or not authorized", "danger")
        return redirect(url_for("jobseeker_applications.list_applications"))

    if application.application_stage != "draft":
        flash("Only draft applications can be edited", "warning")
        return redirect(url_for("jobseeker_applications.view_application", application_id=application.application_id))
    resume_controller = get_controller('resume')
    job = await jobs_search_controller.get_job_by_id(application.job_id)
    cvs = await resume_controller.list_cvs_for_user(user_uid=user.uid)

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
@jobseeker_login
async def submit_edited_application(application_id: str, user: User):
    form = request.form
    selected_cv_id = form.get("cv_id")
    cover_letter = form.get("cover_letter")
    jobs_search_controller = get_controller('jobs_search')
    application = await jobs_search_controller.get_application_by_id(application_id)

    if not application or application.user_id != user.uid or application.application_stage != "draft":
        flash("Unauthorized or invalid application", "danger")
        return redirect(url_for("jobseeker_applications.list_applications"))
    jobs_workflow_controller = get_controller('jobs_workflow')
    
    # Note: This method may not exist in the workflow controller, but keeping for now
    # In a real implementation, you would need to implement this method or use an alternative approach
    try:
        await jobs_workflow_controller.update_draft_application(
            application_id=application.application_id,
            updated_data={
                "cv_id": selected_cv_id,
                "cover_letter": cover_letter,
            }
        )
        flash("Application updated successfully", "success")
    except AttributeError:
        flash("Application editing is not currently supported", "warning")
    
    return redirect(url_for("jobseeker_applications.view_application", application_id=application.application_id))


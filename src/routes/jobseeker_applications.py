from flask import Blueprint, render_template, request, redirect, url_for, flash
from pydantic import ValidationError

from src.database.models.jobs import JobApplication
from src.routes import flask_error_handler
from src.main import resume_controller, ats_controller, jobs_controller
from src.database.models.users import User
from src.authentication import login_required

jobseeker_applications_bp = Blueprint("jobseeker_applications", __name__, url_prefix="/jobseeker/applications")

async def get_location_options(user_id: str, cv_ids: list[str]) -> list[str]:
    profile_locations = await resume_controller.get_preferred_locations_from_profile(user_id)
    cv_locations = await resume_controller.get_locations_from_cvs(cv_ids)
    combined = list(set(profile_locations + cv_locations))
    return combined

@jobseeker_applications_bp.route('/api/ats-check', methods=['POST'])
@login_required
async def api_ats_check(user: User):
    data = await request.form
    cv_id = data.get("cv_id")
    cover_letter = data.get("cover_letter", "")

    # You’ll need to pass job_id or job description too
    job_id = request.args.get("job_id")
    job = await jobs_controller.get_job_by_id(job_id)

    ats_score, matched_keywords, missing_keywords = await ats_controller.evaluate_application(
        job_description=job.description,
        cv_id=cv_id,
        cover_letter=cover_letter
    )
    return {
        "score": ats_score,
        "matched": matched_keywords,
        "missing": missing_keywords
    }

@jobseeker_applications_bp.route('/api/cover-draft', methods=['POST'])
@login_required
async def api_cover_draft(user: User):
    data = await request.form
    job_id = request.args.get("job_id")
    cv_id = data.get("cv_id")

    job = await jobs_controller.get_job_by_id(job_id)
    cv = await resume_controller.get_cv_by_id(cv_id)

    draft = await ats_controller.generate_cover_letter(job, cv)
    return {"draft": draft}

@jobseeker_applications_bp.route('/jobs/<string:job_id>/apply', methods=['GET'])
@login_required
async def apply_for_job(user: User, job_id: str):
    job_details = await jobs_controller.get_job_by_id(job_id)
    cvs = await resume_controller.list_cvs_for_user(user_uid=user.uid)

    # Set the keywords found in the job description and the industry the job falls in
    ats_controller.set_industry_keywords()
    ats_score, matched_keywords, missing_keywords = await ats_controller.generate_ats_report()

    # The Cover letter feedback will be done once the cover letter is written
    cover_letter_feedback = None

    # Use job descriptions and recommendations from an API
    salary_recommendation = await ats_controller.recommend_salary(job_details)

    # Find locations from job description and jobseekers’ preferred locations (from CV and Profile)
    cv_ids = [cv.cv_id for cv in cvs]
    locations = await get_location_options(user_id=user.uid,job_id=job_details.job_id, cv_ids=cv_ids)

    context = dict(
        job=job_details,
        cvs=cvs,
        ats_score=ats_score,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        cover_letter_feedback=cover_letter_feedback,
        salary_recommendation=salary_recommendation,
        locations=locations,
        current_user=user,
        cover_letter="",  # Can preload if previously saved
    )

    # Display the intuitive Job Application Form with all the tools necessary for the job application process
    return render_template('jobseekers/apply.html', **context)


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


@jobseeker_applications_bp.route("/withdraw-application/<string:application_id>", methods=["GET"])
@flask_error_handler
@login_required
async def withdraw_application(user: User, application_id: str):
    """

    :param user:
    :return:
    """
    pass

@jobseeker_applications_bp.route("/", methods=["GET"])
@flask_error_handler
@login_required
async def list_applications(user: User):
    applications = await jobs_controller.get_applied_job_applications_for_user(user.uid)
    context = dict(current_user=user, applications=applications)
    return render_template("jobseekers/applications/list.html", **context)

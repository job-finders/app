import uuid
from datetime import datetime

from flask import Blueprint, request, render_template, redirect, url_for, flash
from pydantic import ValidationError

from database.models.resume import JobSeekerCV, SavedCV
from src.authentication import login_required
from src.database.models.employer_models import Employer
from src.database.models.jobs_model import Company, JobApplicationDashboard, Job
from src.database.models.users import User
from src.main import users_controller, jobs_controller
from src.main import company_controller
from src.logger import init_logger

company_bp = Blueprint('company', __name__, url_prefix='/company')

logger = init_logger("company_routes")


@company_bp.route("/create-company", methods=["GET", "POST"])
@login_required
async def create_company_profile(user: User):
    """Company profile creation endpoint"""
    _employer_profile: Employer = await company_controller.get_employer_by_uid(uid=user.uid)

    if request.method == "GET":
        if not _employer_profile:
            flash(message="You do not already have an employer profile please create your employer profile first",
                  category="success")
            return redirect(url_for('company.employer_profile'))
        # with user data & employer profile we can now create a company profile
        context = dict(current_user=user, employer_profile=_employer_profile)
        return render_template("company/create_company.html", **context)

    try:
        # Validate incoming data using Pydantic model
        company_data = Company(**request.form)
    except ValidationError as e:
        logger.error(f"Company validation error: {str(e)}")
        flash("Invalid company data. Please check all fields.", "danger")
        return render_template("company/create_company.html",
                            error=e.errors(),
                            current_user=user)

    try:
        # Attempt company creation through controller
        created_company: Company = await company_controller.create_company(company_data=company_data)
    except ValueError as e:
        logger.error(f"Company creation conflict: {str(e)}")
        flash(str(e), "danger")
        return render_template("company/create_company.html",
                            error=str(e),
                            current_user=user,
                            form_data=request.form)
    if not created_company:
        logger.error(f'Error creating company using company data : {company_data}')
        flash(message="there was an problem creating your company please try again", category="danger")

        return redirect(url_for("company.view_company"))

    # Update user role if needed (assuming employers need company association)
    if user.role != "employer":
        await users_controller.update_user_role(user.uid, "employer")

    _add_company_employer_profile = await company_controller.update_employer_profile(
        employer_id=_employer_profile.employer_id, company_data=company_data)

    flash("Company profile created successfully!", "success")
    return redirect(url_for("company.view_company"))


@company_bp.route("/profile", methods=["GET"])
@login_required
async def view_company(user: User):
    """Company profile viewing endpoint"""
    if user.role != "employer":
        logger.error(f"Company lookup error: User is not an Employer at any company")
        return redirect(url_for("company.employer_profile"))

    _employer_profile: Employer = await company_controller.get_employer_by_uid(user_id=user.uid)
    if not _employer_profile:
        err = f"Employer lookup error: Please try again or inform admin"
        logger.error(err)
        flash(err, "danger")
        return redirect(url_for("company.employer_profile"))
    company_data: Company = await company_controller.get_company_by_id(company_id=_employer_profile.company_id)
    if not company_data:
        logger.error(f"Error looking up Company with Company ID: {_employer_profile.company_id}")
        flash(message="looks like you have not yet created a company associated with your employer profile, please create it", category='danger')
        return redirect(url_for('company.create_company_profile'))

    context = {
        "current_user": user,
        "employer_profile": _employer_profile,
        "company_data": company_data}

    return render_template("company/view_profile.html", **context)


@company_bp.route("/employer/profile", methods=["GET", "POST"])
@login_required
async def employer_profile(user: User):
    """Employer profile management (web interface)"""
    if request.method == "GET":
        _employer_profile: Employer = await company_controller.get_employer_by_uid(user_id=user.uid)
        if _employer_profile and _employer_profile.company_id:
            company_data = await company_controller.get_company_by_id(company_id=_employer_profile.company_id)
        else:
            company_data = {}
        context = dict(current_user=user, employer_profile=_employer_profile, company_data=company_data)
        return render_template("company/employer_profile.html", **context)

    # creating new employer profile method is POST
    try:
        employer_data = Employer(**request.form)
    except ValidationError as e:
        logger.error(str(e))
        return redirect(url_for("company.employer_profile"))

    employer: Employer = await company_controller.register_employer(employer_data=employer_data)
    if not employer:
        err = "Employer profile already exists"
        logger.error(f"Profile creation failed: {err}")
        flash("Profile creation failed: {err}", "danger")
        return redirect(url_for("company.employer_profile"))

    flash("Profile updated successfully", "success")
    return redirect(url_for("company.employer_profile"))


@company_bp.route("/jobs", methods=["GET", "POST"])
@login_required
async def manage_jobs(user: User):
    """Job post management (mirrors ATS tool pattern)"""

    if not user.role == "employer":
        flash(message="You are not associated with any company please create a company in order to continue",
              category="danger")
        return redirect(url_for('company.employer_profile'))

    _employer_profile: Employer = await company_controller.get_employer_by_uid(user_id=user.uid)
    if not _employer_profile:
        flash("Please create your employer profile before posting or viewing jobs", "danger")
        return redirect(url_for('company.employer_profile'))

    if not (_employer_profile.is_valid and _employer_profile.is_verified):
        flash("Please verify your employer profile before posting or viewing jobs", "danger")
        return redirect(url_for('company.employer_profile'))

    if request.method == "GET":
        # get methods allows employer to view jobs
        company_id=_employer_profile.company_id
        jobs:list[Job] = await company_controller.get_company_jobs(company_id=company_id)
        company_data = await company_controller.get_company_by_id(company_id=company_id)
        context = dict(current_user=user,employer_profile=_employer_profile, company=company_data,jobs=jobs)

        return render_template("company/jobs.html", **context)

    # POST - Create new jobs for employers
    try:
        job_data = Job(**request.form)
    except ValidationError as e:
        logger.error(str(e))
        flash(message='please complete fully the job post form')
        return redirect(url_for('company.manage_jobs'))

    job:Job = await company_controller.post_job(user_uid=user.uid, job_data=job_data)
    flash("Job created successfully", "success")
    return redirect(url_for("company.manage_jobs"))

@company_bp.route("/candidates", methods=["GET", "POST"])
@login_required
async def candidate_management(user: User):
    """Candidate shortlisting (extends ATS functionality)"""

    if not user.role == "employer":
        flash(message="You are not associated with any company please create a company in order to continue",
              category="danger")
        return redirect(url_for('company.create_company_profile'))

    if request.method == "GET":
        candidates: list[JobSeekerCV] = await company_controller.get_saved_candidates(user_uid=user.uid)
        context = dict(current_user=user, candidates=candidates)
        return render_template("company/candidates.html", **context)
    
    # POST - Save candidate - when user clicks save show a dialog and gather notes
    cv_id = request.form.get('cv_id')
    notes = request.form.get('notes')

    employer_details: Employer = await company_controller.get_employer_by_uid(user_id=user.uid)

    save_cv_model= SavedCV(notes=notes, employer_id=employer_details.employer_id, cv_id=cv_id)
    candidate_saved = await company_controller.save_candidate(user_uid=user.uid, save_cv_model=save_cv_model)

    if not candidate_saved:
        flash("Unable to save candidate please try again later", "danger")
        return redirect(url_for("company.candidate_management"))

    flash("Candidate saved to shortlist", "success")
    return redirect(url_for("company.candidate_management"))
    

@company_bp.route("/analytics/applications", methods=["GET"])
@login_required
async def application_analytics(user: User):
    """Hiring analytics dashboard (integrates with ATS reports)"""

    if not user.role == "employer":
        flash(message="You are not associated with any company please create a company in order to continue", category="danger")
        return redirect(url_for('company.create_company_profile'))

    _employer_profile: Employer = await company_controller.get_employer_by_uid(user_uid=user.uid)
    if not (_employer_profile.is_valid and _employer_profile.is_verified):
        flash(message="Your Employer Profile is either not complete or not verified", category="danger")
        return redirect(url_for('company.employer_profile'))

    analytics: JobApplicationDashboard = await company_controller.get_application_analytics(company_id=_employer_profile.company_id)
    context = dict(current_user=user, analytics=analytics)
    return render_template("company/analytics.html", **context)

@company_bp.route("/verify-employer-profile", methods=["POST"])
@login_required
async def initiate_employer_verification(user: User):
    """Start company verification process"""
    employer_orm = await company_controller.get_employer_by_uid(user_uid=user.uid)
    if not employer_orm:
        flash(message="please create the employer profile first", category='danger')
        return redirect(url_for("company.employer_profile"))

    employer = Employer(**employer_orm.to_dict())

    if not employer.is_valid:
        flash(message="please ensure your employer profile is complete before attemmpting verification", category="danger")
        return redirect(url_for("company.employer_profile"))

    response = await company_controller.initiate_employer_profile_verification(employer_id=employer.employer_id)
    # Send verification email (pseudo-code)
    # await send_verification_email(request.user_email, token)
    flash("Verification initiated - check your email", "success")

    return redirect(url_for("company.employer_profile"))

@company_bp.route("/do-verify-employer-profile/<string:token>/<string:employer_id>", methods=["GET"])
async def verify_employer_profile(token: str, employer_id: str):
    """
    The employer lands here after clicking the verification link in the email.
    """
    employer = await company_controller.get_employer_by_employer_id(employer_id=employer_id)
    context = {'current_year': datetime.now().year}

    if not employer:
        flash("Invalid employer ID or the profile does not exist.", "danger")
        return render_template("employers/employer_verification_failed.html", **context)

    if not employer.is_token_valid(token):
        flash("The verification link is invalid or has expired.", "danger")
        return render_template("employers/employer_verification_failed.html", **context)

    # Mark as verified and remove token
    _ = await company_controller.mark_employer_as_verified(employer_id=employer_id)

    flash("Your profile has been successfully verified!", "success")


    return render_template("employers/employer_verification_success.html", **context)





import uuid

from flask import Blueprint, request, render_template, redirect, url_for, flash
from pydantic import ValidationError

from authentication import login_required
from database.models.employer_models import Employer
from database.models.jobs_model import Company
from database.models.users import User
from main import users_controller, jobs_controller
from src.main import company_controller
from src.logger import init_logger

company_bp = Blueprint('company', __name__, url_prefix='/company')

logger = init_logger("company_routes")


@company_bp.route("/create-company", methods=["GET", "POST"])
@login_required
async def create_company_profile(user: User):
    """Company profile creation endpoint"""
    if request.method == "GET":
        context = dict(current_user=user)
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
        created_company = await company_controller.create_company(company_data)
    except ValueError as e:
        logger.error(f"Company creation conflict: {str(e)}")
        flash(str(e), "danger")
        return render_template("company/create_company.html",
                            error=str(e),
                            current_user=user,
                            form_data=request.form)

    # Update user role if needed (assuming employers need company association)
    if user.role != "employer":
        await users_controller.update_user_role(user.uid, "employer")

    flash("Company profile created successfully!", "success")
    return redirect(url_for("company.view_company"))


@company_bp.route("/profile", methods=["GET"])
@login_required
async def view_company(user: User):
    """Company profile viewing endpoint"""
    employer_details = await company_controller.get_employer_by_uid(user_id=user.uid)

    if not employer_details:
        logger.error(f"Company lookup error: User is not an Employer at any company")
        return redirect(url_for("company.create_company_profile"))

    company_id = employer_details.company_id
    company: Company = await company_controller.get_company_by_id(company_id)
    if not company:
        err = f"Company lookup error: Please try again or inform admin"
        logger.error(err)
        flash(err, "danger")
        return redirect(url_for("company.employer_profile"))

    context = {
        "current_user": user,
        "company": company}

    return render_template("company/view_profile.html", **context)


@company_bp.route("/employer/profile", methods=["GET", "POST"])
@login_required
async def employer_profile(user: User):
    """Employer profile management (web interface)"""
    if request.method == "GET":
        context = dict(current_user=user)
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
    if request.method == "GET":
        company_data: Company = await company_controller.get_employer_by_uid(user_id=user.uid)

        if not company_data:
            flash("There could be an error accessing the database or your account is not associated with a company", "danger")
            return redirect(url_for('company.create_company'))
        company_id=company_data.company_id
        if not company_data.jobs:
            jobs = await company_controller.get_company_jobs(company_id=company_id)
        else:
            jobs = company_data.jobs

        context = dict(current_user=user, company=company_data,jobs=jobs)

        return render_template("company/jobs.html", **context)
    
    # POST - Create new job
    job_data = {
        "title": request.form.get("title"),
        "description": request.form.get("description"),
        "location": request.form.get("location"),
        "salary": request.form.get("salary"),
        "status": "DRAFT"
    }
    
    try:
        job = await company_controller.post_job(
            user_uid=request.user_uid,
            job_data=job_data
        )
        flash("Job created successfully", "success")
        return redirect(url_for("company.manage_jobs"))
    
    except Exception as e:
        logger.error(f"Job creation failed: {str(e)}")
        return render_template("company/jobs.html", error=str(e))

@company_bp.route("/candidates", methods=["GET", "POST"])
async def candidate_management():
    """Candidate shortlisting (extends ATS functionality)"""
    if request.method == "GET":
        candidates = await company_controller.get_saved_candidates(
            user_uid=request.user_uid
        )
        return render_template("company/candidates.html", candidates=candidates)
    
    # POST - Save candidate
    try:
        candidate = await company_controller.save_candidate(
            user_uid=request.user_uid,
            cv_id=request.form.get("cv_id"),
            notes=request.form.get("notes")
        )
        flash("Candidate saved to shortlist", "success")
        return redirect(url_for("company.candidate_management"))
    
    except Exception as e:
        logger.error(f"Candidate save failed: {str(e)}")
        return render_template("company/candidates.html", error=str(e))

@company_bp.route("/analytics/applications", methods=["GET"])
async def application_analytics():
    """Hiring analytics dashboard (integrates with ATS reports)"""
    try:
        metrics = await company_controller.get_application_analytics(
            user_uid=request.user_uid
        )
        return render_template("company/analytics.html", metrics=metrics)
    
    except Exception as e:
        logger.error(f"Analytics load failed: {str(e)}")
        flash("Failed to load analytics", "danger")
        return redirect(url_for("company.employer_profile"))

@company_bp.route("/verify", methods=["POST"])
async def initiate_verification():
    """Start company verification process"""
    try:
        token = await company_controller.initiate_verification(
            user_uid=request.user_uid
        )
        # Send verification email (pseudo-code)
        # await send_verification_email(request.user_email, token)
        flash("Verification initiated - check your email", "success")
    
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        flash("Verification initiation failed", "danger")
    
    return redirect(url_for("company.employer_profile"))
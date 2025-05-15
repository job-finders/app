from flask import Blueprint, request, render_template, redirect, url_for, flash
from src.controllers import CompanyController
from src.database.models.employer import Employer
from src.logger import init_logger

company_bp = Blueprint('company', __name__)
company_controller = CompanyController()
logger = init_logger("company_routes")

@company_bp.route("/company/profile", methods=["GET", "PUT"])
async def employer_profile():
    """Employer profile management (web interface)"""
    if request.method == "GET":
        return render_template("company/profile.html")
    
    # PUT - Update profile
    updates = {
        "company_name": request.form.get("company_name"),
        "industry": request.form.get("industry"),
        "website": request.form.get("website"),
        "location": request.form.get("location")
    }
    
    try:
        employer = await company_controller.update_employer_profile(
            user_uid=request.user_uid,  # Assume auth middleware adds this
            updates=updates
        )
        flash("Profile updated successfully", "success")
        return redirect(url_for("company.employer_profile"))
    
    except Exception as e:
        logger.error(f"Profile update failed: {str(e)}")
        flash("Failed to update profile", "danger")
        return render_template("company/profile.html", error=str(e))

@company_bp.route("/company/jobs", methods=["GET", "POST"])
async def manage_jobs():
    """Job post management (mirrors ATS tool pattern)"""
    if request.method == "GET":
        jobs = await company_controller.get_company_jobs(
            user_uid=request.user_uid
        )
        return render_template("company/jobs.html", jobs=jobs)
    
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

@company_bp.route("/company/candidates", methods=["GET", "POST"])
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

@company_bp.route("/company/analytics/applications", methods=["GET"])
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

@company_bp.route("/company/verify", methods=["POST"])
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
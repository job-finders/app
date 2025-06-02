import uuid
from datetime import datetime

from flask import Blueprint, request, render_template, redirect, url_for, flash
from pydantic import ValidationError

from database.models.company_models import CompanyVerificationStatus
from database.models.resume import JobSeekerCV, SavedCV
from src.authentication import login_required
from src.database.models.employer_models import Employer
from src.database.models.jobs_model import Company, JobApplicationDashboard, Job
from src.database.models.users import User
from src.main import users_controller, company_controller
from src.main import company_controller
from src.logger import init_logger

company_search_routes = Blueprint('company_search', __name__, url_prefix='/company')




@company_search_routes.get('/view/<str:company_id>')
@login_required
async def view_company_by_company_id(user: User, company_id: str):
    """
        Search for companies based on the user's input.
    """
    if not company_id:
        flash("Company ID is required.", "error")
        return redirect(url_for('home.get_home'))

    company_data = await company_controller.get_company_by_id(company_id=company_id)
    if not company_data:
        flash("Company not found.", "error")
        return redirect(url_for('home.get_home'))

    if company_data.verification_status != CompanyVerificationStatus.VERIFIED:
        flash("Company is not verified.", "error")
        return redirect(url_for('home.get_home'))
    
    # Fetch the jobs associated with the company
    jobs = await company_controller.get_jobs_by_company_id(company_id=company_id)
    if not jobs:
        flash("No jobs found for this company.", "info")

    # Fetch the employer associated with the company
    employer = await company_controller.get_employer_by_company_id(company_id=company_id)

    if not employer:
        flash("Employer not found for this company.", "error")
        return redirect(url_for('home.get_home'))

    # Fetch the job applications for the user
    job_applications = await company_controller.get_job_applications_by_user_id_and_company_id(
        user_id=user.id, company_id=company_id
    )    
    if not job_applications:
        flash("No job applications found for this company.", "info")

    
    # Fetch the saved CVs for the user
    saved_cvs = await company_controller.get_saved_cvs_by_user_id_and_company_id(
        user_id=user.id, company_id=company_id
    )
    if not saved_cvs:
        flash("No saved CVs found for this company.", "info")

    return render_template(
    'company/view_company.html',
        current_user=user,
        company=company_data,
        jobs=jobs,
        employer=employer,
        job_applications=job_applications,
        saved_cvs=saved_cvs     
    )



    


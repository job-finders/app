from flask import Blueprint, render_template, redirect, url_for, flash

from src.authentication import employer_login, user_details
from src.database.models.company_models import CompanyVerificationStatus, Company
from src.database.models.employer_models import Employer
from src.database.models.users import User
from src.logger import init_logger
from src.routes import flask_error_handler
from src.utils.route_helpers import get_controller

company_search_routes = Blueprint('company_search', __name__, url_prefix='/company')




@company_search_routes.get('/view/<string:company_id>')
@flask_error_handler
@employer_login
async def view_company_by_company_id(user: User, company_id: str):
    """
        Search for companies based on the user's input.
    """
    if not company_id:
        flash("Company ID is required.", "error")
        return redirect(url_for('home.get_home'))
    company_controller = get_controller('company')
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
    
@company_search_routes.get('/browse')
@flask_error_handler
@user_details
async def list_companies(user: User):
    """
        This is a Public Route to view Public Details About All Available Companies and their jobs
    :param user:
    :return:
    """
    company_controller = get_controller('company')
    company_list: list[Company] = await company_controller.get_all_companies()
    context = {
        'current_user': user,
        'company_list': company_list
    }
    return render_template('company/public/company_list.html', **context)



@company_search_routes.get('/employees')
@flask_error_handler
@employer_login
async def get_employer_details(user: User):
    """
    Fetches the employer details for a given company ID.
    """
    try:
        company_controller = get_controller('company')
        _employee_profile = await company_controller.get_employer_by_uid(uid=user.uid)
        if not _employee_profile:
            flash(message="Unable to list Employees", category="danger")
            return redirect('home.get_home')
        company_id = _employee_profile.company_id
        employee_list: list[Employer] = await company_controller.get_employees_by_company_id(company_id=company_id)
        #TODO - need to finalize this route
        context = dict(current_user=user, employee_list=employee_list)
        return render_template('company/company_employees.html', **context)

    except Exception as e:
        init_logger().error(f"Error fetching employer details: {e}")
        return None
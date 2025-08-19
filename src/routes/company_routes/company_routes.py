# Standard Library
import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

# Flask & Third-Party
from flask import Blueprint, request, render_template, redirect, url_for, flash
from pydantic import ValidationError, HttpUrl
from werkzeug.utils import secure_filename

from src.controllers.billing.billing_controller import BillingController
from src.controllers.company import CompanyController
# Authentication
from src.authentication import login_required, employer_login, require_billing_role

# Controllers
from src.controllers.agents import EmployerAgentsController
from src.controllers.jobs import JobsWorkflowController

# Domain Models
from src.database.models import (
    Company,
    CompanyUpdate,
    CompanyVerificationStatus,
    CompanyVerificationDocument,
    CompanySettings,
    AllowableCompanyVerificationDocumentsEnum,
    CompanyCIPC,
    DirectorDetails,
    Employer,
    Job,
    JobApplicationDashboard,
    JobSeekerCV,
    SavedCV,
    User,
)
# Logger
from src.logger import init_logger
# Routes
from src.routes import flask_error_handler
# Services
from src.services.billing.billing_service import BillingTiersEnum
# Utilities
from src.utils.file_uploads import save_company_logo, save_verification_file
from src.utils.route_helpers import get_controller

company_bp = Blueprint('company', __name__, url_prefix='/dashboard/company')
logger = init_logger("company_routes")

# Configure these in your settings
ALLOWED_EXTENSIONS = {'pdf'}
UPLOAD_FOLDER = 'company_documents'

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@company_bp.route("/create-company", methods=["GET", "POST"])
@login_required
async def create_company_profile(user: User):
    """Company profile creation endpoint"""
    company_controller = get_controller('company')
    countries = await company_controller.get_countries()
    industries = await company_controller.get_industries()
    tech_options = await company_controller.get_tech_options()
    logger.info(f"Inside Company Profile Creator")

    if request.method == "GET":
        company_data = await company_controller.get_employer_created_company(uid=user.uid)
        if company_data:
            logger.info(f"Company is found : {company_data} lets go to view it")
            flash(message="You already created a company. View or edit your company profile below.", category="info")
            return redirect(url_for('company.view_company'))

        context = dict(current_user=user, countries=countries, industries=industries, tech_options=tech_options)
        logger.info("Will display a form to create a company")
        return render_template("company/details/create.html", **context)

    # POST
    form_data = request.form.to_dict()
    form_data['tech_stack'] = request.form.getlist("tech_stack")
    logger.info(f"Obtained Form Data for creating Company Profile and Employer Initial Profile : {form_data}")
    try:
        company_data = Company(**form_data)
        logger.info(f"Company Data casted into Pydantic for creating Company Data : {company_data}")
    except ValidationError as e:
        logger.error(f"Company validation error: {str(e)}")
        errors = e.errors()
        for error in errors:
            field = error['loc'][0]
            msg = error['msg']
            flash(f"{field.title()} error: {msg}", "danger")
        context = dict(current_user=user, countries=countries, industries=industries, tech_options=tech_options, form_data=form_data, errors=errors)
        return render_template("company/details/create.html", **context), 400
    try:
        created_company: Company = await company_controller.create_company(company_data=company_data)
        if not created_company:
            flash(message="Unable to create Company - Maybe a Duplicate Company", category="danger")
            context = dict(current_user=user, countries=countries, industries=industries, tech_options=tech_options, form_data=form_data)
            return render_template("company/details/create.html", **context), 400
        logger.info(f"Company Created : {created_company}")
        initial_employer_profile = Employer(
            user_uid=user.uid,
            company_id=created_company.company_id)
        logger.info(f"Trying to Register an Employer by calling register employer with initial employer profile : {initial_employer_profile}")
        create_employer_profile: Employer = await company_controller.register_employer(
            employer_data=initial_employer_profile)
        if not create_employer_profile:
            flash(message="Unable to create Employer Profile - Maybe a Duplicate Company", category="danger")
            context = dict(current_user=user, countries=countries, industries=industries, tech_options=tech_options, form_data=form_data)
            return render_template("company/details/create.html", **context), 400
        logger.info(f"Successfully created Company & Employer Profiles")
    except ValueError as e:
        logger.error(f"Company creation conflict: {str(e)}")
        flash(str(e), "danger")
        context = dict(current_user=user, countries=countries, industries=industries, tech_options=tech_options, form_data=form_data, error=str(e))
        return render_template("company/details/create.html", **context), 400

    if not (created_company and create_employer_profile):
        logger.error(f'Error creating company using company data : {company_data}')
        flash(message="There was a problem creating your company. Please try again.", category="danger")
        context = dict(current_user=user, countries=countries, industries=industries, tech_options=tech_options, form_data=form_data)
        return render_template("company/details/create.html", **context), 400

    # Update user role if needed (assuming employers need company association)
    if user.role != "employer":
        users_controller = get_controller('users')
        await users_controller.update_user_role(user.uid, "employer")

    flash("Company profile created successfully! Please create your employer profile next.", "success")
    return redirect(url_for("company.view_company"))


@company_bp.route('/profile/edit', methods=['GET'])
@employer_login
async def edit_company_profile(user: User):
    """Render company profile edit form"""
    company_controller = get_controller('company')
    _employer_profile: Employer = await company_controller.get_employer_by_uid(user_id=user.uid)
    if not _employer_profile:
        flash("Employer profile not found. Please create your employer profile first.", "danger")
        return redirect(url_for("company.create_company_profile"))
    if not _employer_profile.company_id:
        flash("No company associated with your employer profile. Please create a company profile.", "danger")
        return redirect(url_for("company.create_company_profile"))
    company = await company_controller.get_company_by_id(_employer_profile.company_id)
    if not company:
        flash("Company not found. Please create your company profile.", "danger")
        return redirect(url_for("company.create_company_profile"))
    context = dict(
        current_user=user,
        company=company,
        current_year=datetime.now().year
    )
    return render_template('company/details/editor.html', **context)


@company_bp.route('/profile/update', methods=['POST'])
@employer_login
async def update_company_profile(user: User):
    """Process company profile updates"""
    company_controller = get_controller('company')
    _employer_profile = await company_controller.get_employer_by_uid(user_id=user.uid)
    company_id = _employer_profile.company_id
    if not _employer_profile:
        logger.info(f"Employer Profile not Found")
        return redirect(url_for("company.create"))

    try:
        # Process form data
        form_data = request.form.to_dict()
        # Handle file upload
        logo_file = request.files.get('logo')
        if logo_file and allowed_file(logo_file.filename):
            filename = secure_filename(logo_file.filename)
            logo_url = save_company_logo(logo_file, company_id)
            form_data['logo_url'] = logo_url

        # Convert tech stack string to list
        if 'tech_stack' in form_data:
            # noinspection PyTypeChecker
            form_data['tech_stack'] = [tech.strip() for tech in form_data['tech_stack'].split(',') if tech.strip()]

        # Convert employee count to int if possible
        if form_data.get('employee_count'):
            try:
                form_data['employee_count'] = int(form_data['employee_count'])
            except ValueError:
                # Keep as string if it's a range (e.g., "51-200")
                pass

        # Convert checkbox to boolean
        # form_data['is_public'] = 'make_profile_public' in form_data

        # Validate and update
        update_data = CompanyUpdate(**form_data)
        updated_company = company_controller.update_company(company_id, update_data)

        flash('Company profile updated successfully!', 'success')
        return redirect(url_for('company.view_company_profile'))

    except ValidationError as e:
        errors = e.errors()
        for error in errors:
            field = error['loc'][0]
            msg = error['msg']
            flash(f'{field.title()} error: {msg}', 'danger')

        # Re-fetch company to repopulate form
        company: Company = company_controller.get_company_by_id(company_id=company_id)
        context = dict(
            company=company,
            form_data=request.form,
            current_year=datetime.now().year
        )
        return render_template('company/details/editor.html', **context), 400

    except Exception as e:
        logger.error(f"Error updating company profile: {str(e)}")
        flash('An error occurred while updating your profile. Please try again.', 'danger')
        return redirect(url_for('company.edit_company_profile'))


@company_bp.route("/update-employer", methods=["GET", "POST"])
@employer_login
async def update_employer_profile(user: User):
    if user.role != "employer":
        flash("Access denied: Only employers can update this profile.", "danger")
        return redirect(url_for("company.view_employer_profile"))
    company_controller = get_controller('company')
    employer_profile: Employer = await company_controller.get_employer_by_uid(user_id=user.uid)
    if not employer_profile:
        flash("Please create your employer profile before updating.", "danger")
        return redirect(url_for("company.view_employer_profile"))

    company_data: Company = await company_controller.get_company_by_id(employer_profile.company_id)
    if not company_data:
        flash("Please create a company profile before updating employer details.", "danger")
        return redirect(url_for("company.create_company_profile"))

    if request.method == "POST":
        form = request.form
        # Update fields if present in the form
        employer_profile.full_name = form.get("full_name") or employer_profile.full_name
        employer_profile.job_title = form.get("job_title") or employer_profile.job_title
        employer_profile.department = form.get("department") or employer_profile.department
        employer_profile.bio = form.get("bio") or employer_profile.bio
        employer_profile.company_email = form.get("company_email") or employer_profile.company_email
        employer_profile.personal_email = form.get("personal_email") or employer_profile.personal_email
        employer_profile.phone_number = form.get("phone_number") or employer_profile.phone_number
        employer_profile.alternate_phone = form.get("alternate_phone") or employer_profile.alternate_phone
        employer_profile.linkedin_url = form.get("linkedin_url") or employer_profile.linkedin_url
        employer_profile.twitter_handle = form.get("twitter_handle") or employer_profile.twitter_handle
        employer_profile.signature = form.get("signature") or employer_profile.signature

        # Date field
        hire_date = form.get("hire_date")
        if hire_date:
            try:
                # noinspection PyTypeChecker
                employer_profile.hire_date = datetime.strptime(hire_date, "%Y-%m-%d")
            except ValueError:
                flash("Invalid hire date format.", "warning")

        # Checkbox for hiring authority
        employer_profile.hiring_authority = "hiring_authority" in form

        try:
            employer_profile.update_timestamp()
            await company_controller.update_employer_profile(employer_profile)
            flash("Employer profile updated successfully.", "success")
            return redirect(url_for("company.update_employer_profile"))
        except Exception as e:
            flash(f"An error occurred while updating your profile: {str(e)}", "danger")
            context = {
                "current_user": user,
                "employer_profile": employer_profile,
                "company_data": company_data,
                "form_data": form
            }
            return render_template("company/details/company_profile.html", **context), 400

    context = {
        "current_user": user,
        "employer_profile": employer_profile,
        "company_data": company_data
    }
    return render_template("company/details/company_profile.html", **context)


@company_bp.route("/profile", methods=["GET"])
@flask_error_handler
@employer_login
async def view_company(user: User):
    """Company profile viewing endpoint"""
    if not hasattr(user, "role") or user.role != "employer":
        logger.error("Company lookup error: User is not an Employer at any company or role missing")
        flash("You must be an employer to view this page.", "danger")
        return redirect(url_for("company.view_employer_profile"))

    company_controller = get_controller('company')
    _employer_profile: Employer = await company_controller.get_employer_by_uid(user_id=getattr(user, "uid", None))
    if not _employer_profile or not hasattr(_employer_profile, "company_id") or not _employer_profile.company_id:
        logger.info("Unable to Retrieve Employer Profile from Database or company_id missing")
        flash("Please create your Employer Profile", "danger")
        return redirect(url_for("company.view_employer_profile"))

    logger.info(f"view_company : Retrieved Employer Profile : {_employer_profile}")
    company_data: Company = await company_controller.get_company_by_id(company_id=_employer_profile.company_id)
    if not company_data:
        logger.info(f"Error looking up Company with Company ID: {getattr(_employer_profile, 'company_id', None)}")
        flash("Looks like you have not yet created a company associated with your employer profile, please create it", "danger")
        return redirect(url_for('company.create_company_profile'))

    context = {
        "current_user": user,
        "employer_profile": _employer_profile,
        "company": company_data
    }

    return render_template("company/details/company_profile.html", **context)

@company_bp.route("/employer/profile", methods=["GET"])
@flask_error_handler
@employer_login
async def view_employer_profile(user: User):
    """
        this route allows the employer to view their own profile
        employer profile
    :param user:
    :return:
    """
    logger.info(f"Inside View Employer Profile")
    company_controller = get_controller('company')
    employer_profile = await company_controller.get_employer_by_uid(user_id=user.uid)
    if not employer_profile:
        logger.info(f"No employer profile found for user {user.uid}")
        flash(message="Please create your employer profile before you can continue.", category="warning")
        return redirect(url_for('company.create_company_profile'))
    if not employer_profile.company_id:
        logger.info(f"Employer profile exists but no company_id for user {user.uid}")
        flash(message="Please create your company profile before you can continue.", category="warning")
        return redirect(url_for('company.create_company_profile'))
    company_data = await company_controller.get_company_by_id(company_id=employer_profile.company_id)
    if not company_data:
        logger.info(f"No company data found for employer {employer_profile.employer_id}")
        flash(message="Please create your company profile before you can continue.", category="warning")
        return redirect(url_for('company.create_company_profile'))
    context = {
        "current_user": user,
        "employer": employer_profile,
        "company_data": company_data,
        "current_year": datetime.now().year
    }
    return render_template("company/employers/verify_profile.html", **context)


@company_bp.route("/jobs", methods=["GET", "POST"])
@flask_error_handler
@employer_login
@require_billing_role()
async def manage_jobs(user: User):
    """Job post management (mirrors ATS tool pattern)"""

    if not user.role == "employer":
        flash(message="You are not associated with any company please create a company in order to continue",
        category="danger")
        return redirect(url_for('company.view_employer_profile'))

    company_controller = get_controller('company')
    job_workflow_controller: JobsWorkflowController = get_controller('jobs_workflow')
    employer_agent_controller: EmployerAgentsController = get_controller("employer_agents")

    _employer_profile: Employer = await company_controller.get_employer_by_uid(user_id=user.uid)
    if not _employer_profile:
        flash("Please create your employer profile before posting or viewing jobs", "danger")
        return redirect(url_for('company.view_employer_profile'))

    # if not (_employer_profile.is_valid and _employer_profile.is_verified):
    #     flash("Please verify your employer profile before posting or viewing jobs", "danger")
    #     return redirect(url_for('company.view_employer_profile'))
    if request.method == "GET":
        # get methods allows employer to view jobs
        company_id=_employer_profile.company_id
        logger.info(f"MANAGE JOBS : COMPANY ID : {company_id}")
        jobs:list[Job] = await company_controller.get_company_jobs(company_id=company_id)
        company_data = await company_controller.get_company_by_id(company_id=company_id)
        today = datetime.now(timezone.utc).date().isoformat()
        context = dict(current_user=user, employer_profile=_employer_profile, company=company_data, jobs=jobs, today=today)

        return render_template("company/manage_jobs.html", **context)

    return redirect(url_for("jobs_workflow.show_create_form"))


@company_bp.route("/candidates", methods=["GET", "POST"])
@flask_error_handler
@employer_login
@require_billing_role()
async def candidate_management(user: User):
    """Candidate shortlisting (extends ATS functionality)"""

    if not user.role == "employer":
        flash(message="You are not associated with any company please create a company in order to continue",
        category="danger")
        return redirect(url_for('company.create_company_profile'))
    company_controller = get_controller('company')
    if request.method == "GET":
        candidates: list[JobSeekerCV] = await company_controller.get_saved_candidates(user_uid=user.uid)
        context = dict(current_user=user, candidates=candidates)
        return render_template("company/candidates/candidate_management.html", **context)
    
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


@company_bp.route("/candidate/<string:cv_id>", methods=["GET"])
@flask_error_handler
@employer_login
@require_billing_role(minimum=BillingTiersEnum.Starter.value)
async def candidate_details(user: User, cv_id: str):
    company_controller = get_controller('company')
    candidate = await company_controller.get_candidate_details(cv_id)
    return render_template("company/candidates/details.html", candidate=candidate)

@company_bp.route("/analytics/applications", methods=["GET"])
@flask_error_handler
@employer_login
@require_billing_role(minimum=BillingTiersEnum.Starter.value)
async def application_analytics(user: User):
    """Hiring analytics dashboard (integrates with ATS reports)"""

    if not user.role == "employer":
        flash(message="You are not associated with any company please create a company in order to continue", category="danger")
        return redirect(url_for('company.create_company_profile'))
    company_controller = get_controller('company')
    _employer_profile: Employer = await company_controller.get_employer_by_uid(user_uid=user.uid)
    if not _employer_profile or not (_employer_profile.is_valid and _employer_profile.is_verified):
        flash(message="Your Employer Profile is either not complete or not verified", category="danger")
        return redirect(url_for('company.view_employer_profile'))

    analytics: JobApplicationDashboard = await company_controller.get_application_analytics(company_id=_employer_profile.company_id)
    context = dict(current_user=user, analytics=analytics)
    return render_template("company/analytics/application_analytics.html", **context)

@company_bp.route("/verify-employer-profile", methods=["POST"])
@flask_error_handler
@employer_login
async def initiate_employer_verification(user: User):
    """Start company verification process"""
    company_controller = get_controller('company')
    employer_orm = await company_controller.get_employer_by_uid(user_uid=user.uid)
    if not employer_orm:
        flash(message="please create the employer profile first", category='danger')
        return redirect(url_for("company.view_employer_profile"))

    employer = Employer(**employer_orm.to_dict())

    if not employer.is_valid:
        flash(message="please ensure your employer profile is complete before attempting verification",
              category="danger")
        return redirect(url_for("company.view_employer_profile"))
    try:
        response = await company_controller.initiate_employer_profile_verification(employer_id=employer.employer_id)
    except ValueError as e:
        flash(message=str(e), category="danger")
        return redirect(url_for("company.view_employer_profile"))
    
    # await send_verification_email(request.user_email, token)
    flash("Verification initiated - check your email", "success")
    return redirect(url_for("company.view_employer_profile"))

@company_bp.route("/do-verify-employer-profile/<string:token>/<string:employer_id>", methods=["GET"])
@flask_error_handler
async def verify_employer_profile(token: str, employer_id: str):
    """
    The employer lands here after clicking the verification link in the email.
    """
    # Using Factory Pattern to obtain a controller
    company_controller = get_controller('company')
    employer = await company_controller.get_employer_by_employer_id(employer_id=employer_id)
    context = {'current_year': datetime.now().year}

    if not employer:
        flash("Invalid employer ID or the profile does not exist.", "danger")
        return render_template("company/employers/verify_profile.html", **context)

    if not employer.is_token_valid(token):
        flash("The verification link is invalid or has expired.", "danger")
        return render_template("company/employers/verification_status.html", **context)

    # Mark as verified and remove token
    _ = await company_controller.mark_employer_as_verified(employer_id=employer_id)

    flash("Your profile has been successfully verified!", "success")

    return render_template("company/employers/verification_status.html", **context)


@company_bp.route('/submit-company-verification', methods=['GET', 'POST'])
@flask_error_handler
@employer_login
async def initiate_company_verification(user: User):
    """Endpoint for comprehensive company verification submission"""
    # Authorization check
    if user.role != "employer":
        flash("Only employers can verify companies", "danger")
        return redirect(url_for('company.get_dashboard'))

    company_controller = get_controller('company')

    # Get employer and company info
    employer = await company_controller.get_employer_by_uid(user.uid)
    if not employer or not employer.company_id:
        flash("Complete your employer profile first", "danger")
        return redirect(url_for('company.view_employer_profile'))

    company: Company = await company_controller.get_company_by_id(employer.company_id)

    # Check current verification status
    if company.verification_status == CompanyVerificationStatus.VERIFIED.value:
        flash("Company is already verified", "info")
        status_info = await company_controller.get_company_verification_status(company.company_id)
        return render_template('company/verification/status.html', company=company, status_info=status_info)

    if company.verification_status == CompanyVerificationStatus.PENDING.value:
        flash("Verification is already in progress", "warning")
        status_info = await company_controller.get_company_verification_status(company.company_id)
        return render_template('company/verification/status.html', company=company, status_info=status_info)

    # Handle form submission
    if request.method == 'POST':
        # Extract CIPC details from form
        reg_form_data = request.form.to_dict()


        cipc_data = CompanyCIPC(company_name=reg_form_data.get("name"),
                                registration_number= reg_form_data.get('registration_number'),
                                registration_date=reg_form_data.get("registration_date"),
                                bee_status=reg_form_data.get("bee_status"),
                                tax_pin=reg_form_data.get("tax_pin"),
                                company_id=company.company_id,
                                registered_address=reg_form_data.get("registered_address"),
                                company_type=reg_form_data.get("company_type")
                                )

        director_details = DirectorDetails(
            full_names=reg_form_data.get("full_names"),
            id_number=reg_form_data.get("reg_form_data"),
            cipc_id=cipc_data.cipc_id)

        cipc_data.director_details.append(director_details)

        # Validate required CIPC fields
        required_fields = ["name", "registration_number"]
        if not all(cipc_data[field] for field in required_fields):
            flash("Missing required CIPC details", "danger")
            return render_template('company/initiate_verification.html', company=company)

        # Save/update CIPC record
        existing_cipc = await company_controller.get_cipc_record_by_company_id(company.company_id)
        if existing_cipc:
            await company_controller.update_cipc_record(existing_cipc.cipc_id, cipc_data)
        else:
            await company_controller.create_cipc_record(cipc_data)

        # Process uploaded documents
        document_types = {
            "director_id": "DIRECTOR_ID",
            "cipc_cert": "CIPC_CERT",
            "tax_clearance": "TAX_CLEARANCE",
            "bee_cert": "BEE_CERT"
        }

        document_records = []
        for field_name, doc_type in document_types.items():
            file = request.files.get(field_name)
            if file and file.filename != '' and allowed_file(file.filename):
                # Save file TODO - can do better if this is a separate utility
                filename = secure_filename(f"{company.company_id}_{doc_type}_{file.filename}")
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)

                # Create document record
                # noinspection PyTypeChecker
                document_data = CompanyVerificationDocument(
                    company_id=company.company_id,
                    document_type=doc_type,
                    file_url=file_path
                )

                doc_record = await company_controller.create_verification_document(document_data)
                document_records.append(doc_record)

            else:
                flash(f"Missing or invalid file for {doc_type.replace('_', ' ')}", "danger")
                return render_template('company/initiate_verification.html', company=company)

        # Initiate verification process for each document

        verification_tasks = []
        for doc_record in document_records:
            task = company_controller.initiate_document_verification(
                document_id=doc_record.document_id,
                company_id=company.company_id)
            
            verification_tasks.append(task)
        # Run all verifications concurrently
        await asyncio.gather(*verification_tasks)
        # Update company verification status
        await company_controller.update_company_verification_status(
            company.company_id,
            CompanyVerificationStatus.PENDING.value
        )

        flash("Verification process initiated successfully!", "success")
        return redirect(url_for('company.verification_status', company_id=company.company_id))

    # GET request - show verification form
    # Pre-fill CIPC data if exists
    cipc_record = await company_controller.get_cipc_record_by_company_id(company.company_id)
    return render_template(
        'company/initiate_verification.html',
        company=company,
        cipc_data=cipc_record
    )


@company_bp.route('/submit-company-verification-documents', methods=['GET', 'POST'])
@flask_error_handler
@employer_login
async def upload_company_verification_documents(user: User):
    """
    Handles the display of the upload form and the processing of a single
    uploaded company verification document.
    """
    company_controller = get_controller('company')

    # --- 1. Setup: Get company context for both GET and POST ---
    try:
        employer_details = await company_controller.get_employer_by_uid(user_id=user.uid)
        company = await company_controller.get_company_by_id(company_id=employer_details.company_id)
        if not company:
            flash("Associated company not found.", "danger")
            return redirect(url_for('company.get_dashboard'))
    except Exception as e:
        flash(f"An error occurred while fetching company details: {e}", "danger")
        return redirect(url_for('company.get_dashboard'))

    # --- 2. Handle POST Request (Form Submission) ---
    if request.method == 'POST':
        # --- 2a. Validate Input ---
        if 'document_file' not in request.files:
            flash('No file part in the submission. Please select a file to upload.', 'danger')
            return redirect(request.url)

        file = request.files['document_file']
        doc_type = request.form.get('document_type')

        if not doc_type:
            flash('You must select a document type from the list.', 'danger')
            return redirect(request.url)

        if file.filename == '':
            flash('No file selected. Please choose a file to upload.', 'danger')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload a PDF, JPG, or PNG file.', 'danger')
            return redirect(request.url)

        # --- 2b. Process and Save the File ---
        try:
            # Use the utility to save the file and get its URL
            document_id = str(uuid.uuid4())
            file_url_str = save_verification_file(
                file=file,
                company_name=company.name,
                company_id=company.company_id,
                document_id=document_id,
                doc_type=doc_type
            )
            file_url = HttpUrl(file_url_str)

            # --- 2c. Create Database Record ---
            # Create the Pydantic model instance for the database record
            document_data = CompanyVerificationDocument(
                document_id=document_id,
                company_id=company.company_id,
                document_type=doc_type,
                file_url=file_url,
                # Other fields like document_id, updated_at have default factories
            )

            # Call the controller to create the record in the database
            await company_controller.create_verification_document(document_data)

            flash(f"'{doc_type}' document uploaded successfully! It is now pending review.", "success")
            # Redirect to the main verification hub to see the updated status and history
            return redirect(url_for('company.verification_status'))

        except Exception as e:
            # Catch errors from file saving or database creation
            logger.error(str(e))
            flash(f"An unexpected error occurred: {e}", "danger")
            return redirect(request.url)

    # --- 3. Handle GET Request (Display the Form) ---
    # Get the list of document options for the dropdown
    document_options = AllowableCompanyVerificationDocumentsEnum.sa_company_documents_list()

    context = dict(
        current_user=user,
        company=company,
        document_options=document_options
    )
    # The template name should match the file you created
    return redirect(url_for('company.verification_status'))

    # return render_template("company/upload_company_documents.html", **context)


# Pre-defined options for the dropdown menu in the template
BEE_STATUS_OPTIONS = [
    "Level 1", "Level 2", "Level 3", "Level 4",
    "Level 5", "Level 6", "Level 7", "Level 8",
    "Non-Compliant", "Exempt Micro-Enterprise (EME)"
]


@company_bp.route('/registered-cipc-details', methods=['GET', 'POST'])
@flask_error_handler
@employer_login
async def registered_company_cipc_details(user: User):
    """
    Handles the creation and saving of a company's CIPC details.
    - GET: Displays the form for the user to enter details.
    - POST: Validates and saves the submitted details, then redirects to the
            document upload/verification status page.
    :param user: The currently logged-in employer user object.
    :return: Rendered template or a redirect response.
    """
    company_controller = get_controller('company')
    company_id: str | None = None
    # First, we need to get the company ID associated with the logged-in employer
    try:
        employer_details = await company_controller.get_employer_by_uid(user_id=user.uid)
        if not employer_details or not employer_details.company_id:
            flash("Could not find an associated company. Please contact support.", "danger")
            return redirect(url_for('company.get_dashboard'))  # Or some other appropriate page
        company_id = employer_details.company_id
    except Exception as e:
        # Handle cases where the employer or company might not be found
        flash(f"An error occurred while fetching your company details: {e}", "danger")
        return redirect(url_for('company.get_dashboard'))

    # --- Handle the form submission on POST request ---
    if request.method == 'POST':
        form_data = request.form

        # 1. Prepare the data for Pydantic model creation
        try:

            # Convert date string to a timezone-aware datetime object
            reg_date_str = form_data.get('registration_date')
            registration_datetime = None
            if reg_date_str:
                registration_datetime = datetime.strptime(reg_date_str, '%Y-%m-%d')

            # Assemble the data dictionary
            logger.info(f"Form Data : {form_data}")
            cipc_details_dict = {
                "company_name": form_data.get('company_name'),
                "registration_number": form_data.get('registration_number'),
                "registration_date": registration_datetime,
                "registered_address": form_data.get('registered_address'),
                "company_type": form_data.get('company_type'),
                "director_details": [],
                "tax_pin": form_data.get('tax_pin'),
                "bee_status": form_data.get('bee_status'),
                "company_id": company_id
            }

            # Validate and build the final model
            cipc_data_model = CompanyCIPC(**cipc_details_dict)
            logger.info(f"CIPC Model : {cipc_data_model}")
            # Safely parse the JSON string of director names from the hidden input
            director_list_raw = json.loads(form_data.get('director_names', '[]'))

            # Build a list of DirectorDetails objects
            director_details = []
            for director in director_list_raw:
                if isinstance(director, dict):
                    director_details.append(DirectorDetails(
                        director_id=director.get('director_id'),
                        full_names=director.get('full_names'),
                        id_number=director.get('id_number'),
                        cipc_id=cipc_data_model.cipc_id  # this will be set by the ORM layer if needed
                    ))
            if director_details:
                cipc_data_model.director_details = director_details

        except json.JSONDecodeError:
            flash("There was an error processing the director list. Please try again.", "danger")
            # Redirect back to the form
            return redirect(url_for('company.registered_company_cipc_details'))
        except (ValidationError, ValueError) as e:
            # Catches errors from Pydantic validation or date conversion
            flash(f"Please correct the errors in the form: {e}", "danger")
            # Redirect back to the form. For a better UX, you could re-render the template
            # here, passing back the 'form_data' to pre-fill the fields.
            return redirect(url_for('company.registered_company_cipc_details'))

        # 4. Call the controller method to save the validated data
        try:
            # We assume a method like this exists on your controller
            # Save/update CIPC record
            existing_cipc = await company_controller.get_cipc_record_by_company_id(company_id=company_id)
            if existing_cipc:
                logger.info("Company Found updating existing company.")
                cipc_data_model.cipc_id = existing_cipc.cipc_id
                for director in cipc_data_model.director_details:
                    director.cipc_id = existing_cipc.cipc_id

                await company_controller.update_cipc_record(company_id=company_id, cipc_record=cipc_data_model)
                logger.info("Updated Company")
            else:
                logger.info("Company Not Found")
                created_company = await company_controller.create_cipc_record(cipc_data=cipc_data_model)
                logger.info(f"Created Company : {created_company}")

            flash(
                "Your company details have been saved successfully. Please upload a supporting document to complete verification.",
                "success")
        except Exception as e:
            # Handle potential database or other controller errors
            flash(f"An unexpected error occurred while saving your details: {e}", "danger")
            return redirect(url_for('company.registered_company_cipc_details'))

        # 5. Redirect the user to the next step: the verification status/document upload page
        return redirect(url_for('company.verification_status'))

    # --- Handle the GET request: simply render the form ---
    context = dict(current_user=user, bee_options=BEE_STATUS_OPTIONS)
    # if we have a company_id we try to load the registered company with this id.
    if company_id:
        registered_company: CompanyCIPC | None = await company_controller.get_cipc_record_by_company_id(
            company_id=company_id)
        if registered_company is None:
            logger.info(f"No registered company found for company_id: {company_id}")

        logger.info(f"Registered Directors details : {getattr(registered_company, 'director_details', None)}")
        # at this stage either there is actually a registered company or the controller
        # returned None meaning there is no registered Company
        # noinspection PyTypeChecker
        context.update(registered_company=registered_company)

    return render_template("company/details/register_cipc.html", **context)


@company_bp.route('/verification-status', methods=['GET'])
@flask_error_handler
@employer_login
async def verification_status(user: User):
    """
    Displays the central verification dashboard.
    """
    company_controller = get_controller('company')

    # 1. Get the employer and company details
    employer_details = await company_controller.get_employer_by_uid(user_id=user.uid)
    company = await company_controller.get_company_by_id(company_id=employer_details.company_id)

    # 2. Get the saved CIPC details for the company (if they exist)
    cipc_details = await company_controller.get_cipc_record_by_company_id(company_id=company.company_id)

    # 3. Get a list of already uploaded documents for the company
    uploaded_documents = await company_controller.get_verification_documents(company_id=company.company_id)

    # 4. Get the list of allowable document types for the uploader
    document_options = AllowableCompanyVerificationDocumentsEnum.sa_company_documents_list()
    # --- Define the set of statuses that require user action ---
    # This makes the logic clear and easy to modify in one place.
    # noinspection PyPep8Naming
    ACTIONABLE_STATUSES = {
        CompanyVerificationStatus.NOT_VERIFIED,
        CompanyVerificationStatus.DOCUMENTS_REJECTED,
        CompanyVerificationStatus.CIPC_FAILED,
        CompanyVerificationStatus.PENDING
    }
    # We'll check against the string values of the enum members
    actionable_values = {status.value for status in ACTIONABLE_STATUSES}

    # 5. Determine if the user needs to take action
    # This logic helps the template decide whether to show the uploader or a "pending" message.
    needs_action = company.verification_status in actionable_values

    context = dict(
        current_user=user,
        company=company,
        cipc_details=cipc_details,
        uploaded_documents=uploaded_documents,
        document_options=document_options,
        needs_action=needs_action
    )

    return render_template("company/verification/status.html", **context)


# noinspection DuplicatedCode
@company_bp.route("/settings")
@flask_error_handler
@employer_login
async def settings(user: User):
    company_controller = get_controller('company')
    employer_details = await company_controller.get_employer_by_uid(user_id=user.uid)
    company_data = await company_controller.get_company_by_id(company_id=employer_details.company_id)
    settings = CompanySettings(company_id=company_data.company_id)
    context = dict(current_user=user, settings=settings)
    return render_template("company/settings.html", **context)  # Placeholder template


# noinspection DuplicatedCode
@company_bp.route("/settings")
@flask_error_handler
@employer_login
async def save_settings(user: User):
    """

    :param user:
    :return:
    """
    settings_data = request.form.to_dict()

    company_controller = get_controller('company')
    employer_details = await company_controller.get_employer_by_uid(user_id=user.uid)
    company_data = await company_controller.get_company_by_id(company_id=employer_details.company_id)
    settings = CompanySettings(company_id=company_data.company_id)
    context = dict(current_user=user, settings=settings)
    return render_template("company/settings.html", **context)  # Placeholder template


@company_bp.route("/employers")
@flask_error_handler
@employer_login
@require_billing_role()
async def employers_list(user: User):
    """
    List all employers associated with the company
    """
    if user.role != "employer":
        flash("You must be an employer to view this page", "danger")
        return redirect(url_for("company.view_employer_profile"))
    # Fetch company data associated with the user
    company_controller = get_controller('company')
    _employer_profile: Employer = await company_controller.get_employer_by_uid(user_id=user.uid)
    if not _employer_profile:
        flash("You do not have an employer profile", "danger")
        return redirect(url_for("company.view_employer_profile"))

    # This would typically fetch from the database
    employers_profile_list: list[Employer] = await company_controller.get_all_company_employers(
        company_id=_employer_profile.company_id)
    context = {
        "current_user": user,
        "employer_profile": _employer_profile,
        "employers_list": employers_profile_list
    }

    return render_template("company/employers/list.html", **context)


@company_bp.route("/me")
@login_required
async def get_dashboard(user: User):
    company_controller = get_controller('company')
    employer = await company_controller.get_employer_by_uid(user.uid)

    if not employer:
        flash(message="You need to create your Employer Profile before you can access your Dashboard.",
              category="warning")
        return redirect(url_for('company.view_employer_profile'))

    # Get company data
    company: Company = await company_controller.get_company_by_id(employer.company_id)
    if not company:
        flash(message="Please create your Company Profile before you can access your Dashboard.", category="warning")
        return redirect(url_for('company.create_company_profile'))

    # Get dashboard statistics
    dashboard_stats = await _get_dashboard_stats(company_controller, company.company_id)
    performance_stats = await _get_performance_stats(company_controller, company.company_id)
    recent_activities = await _get_recent_activities(company_controller, company.company_id)
    billing_info = await _get_billing_info(company_controller, employer)
    notifications = await _get_notifications(company_controller, employer.employer_id)

    # Calculate unread notifications count
    unread_notifications_count = len([n for n in notifications if not n.get('read', True)])

    # Determine verification progress (for checklist/progress bar)
    verification_steps = [
        {'name': 'Employer Verified', 'complete': employer.is_verified},
        {'name': 'Documents Submitted', 'complete': bool(getattr(company, 'documents_submitted', False))},
        {'name': 'Company Verified',
         'complete': company.verification_status == CompanyVerificationStatus.VERIFIED.value}
    ]

    context = dict(
        current_user=user,
        company=company,
        employer=employer,
        verification_steps=verification_steps,
        dashboard_stats=dashboard_stats,
        performance_stats=performance_stats,
        recent_activities=recent_activities,
        billing_info=billing_info,
        notifications=notifications,
        unread_notifications_count=unread_notifications_count
    )
    return render_template(
        "company/company_dashboard.html",
        **context
    )


async def _get_dashboard_stats(company_controller, company_id: str) -> dict:
    """Calculate basic dashboard statistics"""
    try:
        # Get active jobs count
        active_jobs = await company_controller.get_company_jobs(company_id)
        active_jobs_count = len([job for job in active_jobs if job.status.lower() == 'active'])

        # Get jobs with applications to count total applications
        jobs_with_applications = await company_controller.get_company_jobs_with_job_applications(company_id)
        total_applications = sum(
            len(job.applications) for job in jobs_with_applications if hasattr(job, 'applications'))

        # Calculate new applications this week (you'll need to add date filtering logic)
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        new_applications = 0
        for job in jobs_with_applications:
            if hasattr(job, 'applications'):
                new_applications += len([
                    app for app in job.applications
                    if hasattr(app, 'applied_at') and app.applied_at >= week_ago
                ])

        # Profile views - this would need to be tracked separately
        profile_views = 0  # Placeholder

        return {
            'active_jobs': active_jobs_count,
            'total_applications': total_applications,
            'new_applications': new_applications,
            'profile_views': profile_views
        }
    except Exception as e:
        logger.error(f"Error calculating dashboard stats: {e}")
        return {
            'active_jobs': 0,
            'total_applications': 0,
            'new_applications': 0,
            'profile_views': 0
        }


async def _get_performance_stats(company_controller, company_id: str) -> dict:
    """Calculate performance statistics"""
    try:
        # Get analytics dashboard if available
        analytics = await company_controller.get_application_analytics(company_id)

        if analytics:
            return {
                'job_views': getattr(analytics, 'total_job_views', 0),
                'applications_received': getattr(analytics, 'total_applications', 0),
                'profile_visits': getattr(analytics, 'profile_views', 0),
                'conversion_rate': getattr(analytics, 'conversion_rate', 0)
            }
        else:
            # Fallback calculations
            jobs_with_applications = await company_controller.get_company_jobs_with_job_applications(company_id)
            applications_received = sum(
                len(job.applications) for job in jobs_with_applications if hasattr(job, 'applications'))

            return {
                'job_views': 0,  # Would need tracking
                'applications_received': applications_received,
                'profile_visits': 0,  # Would need tracking
                'conversion_rate': 0  # Would need calculation
            }
    except Exception as e:
        logger.error(f"Error calculating performance stats: {e}")
        return {
            'job_views': 0,
            'applications_received': 0,
            'profile_visits': 0,
            'conversion_rate': 0
        }


async def _get_recent_activities(company_controller, company_id: str) -> list:
    """Get recent company activities"""
    try:
        activities = []

        # Get recent jobs
        recent_jobs = await company_controller.get_company_jobs(company_id)
        # Sort by created_at if available, otherwise use a default order
        recent_jobs = sorted(recent_jobs, key=lambda x: getattr(x, 'created_at', datetime.min), reverse=True)[:3]

        for job in recent_jobs:
            activities.append({
                'type': 'job-posted',
                'icon': 'fas fa-briefcase',
                'title': 'New job posted',
                'description': f'{job.title} position is now live',
                'created_at': getattr(job, 'created_at', datetime.now())
            })

        # Get recent applications
        jobs_with_applications = await company_controller.get_company_jobs_with_job_applications(company_id)
        all_applications = []
        for job in jobs_with_applications:
            if hasattr(job, 'applications'):
                for app in job.applications:
                    app_data = {
                        'type': 'new-application',
                        'icon': 'fas fa-user-plus',
                        'title': 'New application received',
                        'description': f'Application for {job.title}',
                        'created_at': getattr(app, 'applied_at', datetime.now())
                    }
                    all_applications.append(app_data)

        # Sort all applications and take the most recent ones
        all_applications = sorted(all_applications, key=lambda x: x['created_at'], reverse=True)[:2]
        activities.extend(all_applications)

        # Sort all activities by date
        activities = sorted(activities, key=lambda x: x['created_at'], reverse=True)[:5]

        return activities
    except Exception as e:
        logger.error(f"Error getting recent activities: {e}")
        return []


async def _get_billing_info(company_controller, employer: Employer) -> dict:
    """Get billing and subscription information"""
    try:
        # This would typically come from a billing service/controller
        # For now, return default values
        return {
            'plan_name': 'Free Plan',
            'status': 'active',
            'jobs_posted': 0,  # Would need to calculate
            'jobs_remaining': 5,  # Based on plan limits
            'days_remaining': '∞'  # For free plan
        }
    except Exception as e:
        logger.error(f"Error getting billing info: {e}")
        return {
            'plan_name': 'Free Plan',
            'status': 'active',
            'jobs_posted': 0,
            'jobs_remaining': 5,
            'days_remaining': '∞'
        }


async def _get_notifications(company_controller, employer_id: str) -> list:
    """Get recent notifications for the employer"""
    try:
        # This would typically come from a notifications service/controller
        # For now, return some sample notifications
        notifications = [
            {
                'id': 1,
                'type': 'info',
                'icon': 'fas fa-info',
                'title': 'Welcome to Job Finders!',
                'message': 'Complete your company profile to attract more candidates',
                'read': True,
                'created_at': datetime.now() - timedelta(days=2)
            }
        ]

        return notifications
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        return []


@company_bp.route("/job-applications/<string:company_id>", methods=["GET"])
@flask_error_handler
@login_required
async def get_activity_logs(user: User, company_id: str):
    """

    :param user:
    :param company_id:
    :return:
    """
    company_controller = get_controller("company")
    recent_activities = await _get_recent_activities(company_controller=company_controller, company_id=company_id)
    context = dict(current_user=user, activities=recent_activities)
    # TODO - please complete activity logs
    return render_template('company/analytics/activity_logs.html', **context)

@company_bp.route("/job-applications/<string:company_id>", methods=["GET"])
@flask_error_handler
@login_required
async def view_company_job_applications(user: User, company_id: str):
    """
    View applications for all jobs posted by the company.

    :param user: The employer user viewing the applications.
    :param job_id: The ID of the job post.
    :return: Rendered template with job applications.
    """
    company_controller = get_controller('company')
    jobs_workflow_controller: JobsWorkflowController = get_controller('jobs_workflow')
    company_details: Company = await company_controller.get_company_by_id(company_id=company_id)
    jobs_list: list[Job] = await company_controller.get_company_jobs_with_job_applications(company_id=company_id)

    context = dict(
        current_user=user,
        company=company_details,
        jobs_list=jobs_list
    )
    return render_template("company/jobs/applications/list.html", **context)

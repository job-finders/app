import asyncio
import os
from datetime import datetime

from flask import Blueprint, request, render_template, redirect, url_for, flash
from pydantic import ValidationError
from werkzeug.utils import secure_filename

from src.routes import flask_error_handler
from src.authentication import login_required
from src.database.models.company_models import CompanyVerificationStatus, CompanyUpdate, CompanyCIPC, \
    CompanyVerificationDocument
from src.database.models.employer_models import Employer
from src.database.models.jobs_model import Company, JobApplicationDashboard, Job
from src.database.models.resume import JobSeekerCV, SavedCV
from src.database.models.users import User
from src.logger import init_logger

from src.utils.file_uploads import save_company_logo
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
        return render_template("company/create_company.html", **context)

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
        return render_template("company/create_company.html", **context), 400
    try:
        created_company: Company = await company_controller.create_company(company_data=company_data)
        if not created_company:
            flash(message="Unable to create Company - Maybe a Duplicate Company", category="danger")
            context = dict(current_user=user, countries=countries, industries=industries, tech_options=tech_options, form_data=form_data)
            return render_template("company/create_company.html", **context), 400
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
            return render_template("company/create_company.html", **context), 400
        logger.info(f"Successfully created Company & Employer Profiles")
    except ValueError as e:
        logger.error(f"Company creation conflict: {str(e)}")
        flash(str(e), "danger")
        context = dict(current_user=user, countries=countries, industries=industries, tech_options=tech_options, form_data=form_data, error=str(e))
        return render_template("company/create_company.html", **context), 400

    if not (created_company and create_employer_profile):
        logger.error(f'Error creating company using company data : {company_data}')
        flash(message="There was a problem creating your company. Please try again.", category="danger")
        context = dict(current_user=user, countries=countries, industries=industries, tech_options=tech_options, form_data=form_data)
        return render_template("company/create_company.html", **context), 400

    # Update user role if needed (assuming employers need company association)
    if user.role != "employer":
        users_controller = get_controller('users')
        await users_controller.update_user_role(user.uid, "employer")

    flash("Company profile created successfully! Please create your employer profile next.", "success")
    return redirect(url_for("company.view_company"))


@company_bp.route('/profile/edit', methods=['GET'])
@login_required
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

    return render_template('company/company_editor.html',
                           company=company,
                           current_year=datetime.now().year)


@company_bp.route('/profile/update', methods=['POST'])
@login_required
async def update_company_profile(user: User):
    """Process company profile updates"""
    company_controller = get_controller('company')
    try:
        # Process form data
        form_data = request.form.to_dict()

        _employer_profile = await company_controller.get_employer_by_uid(user_id=user.uid)
        if not _employer_profile:
            logger.info(f"Employer Profile not Found")
            return redirect(url_for("company.create"))
        company_id = _employer_profile.company_id
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
        return render_template('company/company_editor.html',**context), 400

    except Exception as e:
        logger.error(f"Error updating company profile: {str(e)}")
        flash('An error occurred while updating your profile. Please try again.', 'danger')
        return redirect(url_for('company.edit_company_profile'))


@company_bp.route("/update-employer", methods=["GET", "POST"])
@login_required
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
            return render_template("company/employer_profile.html", **context), 400

    context = {
        "current_user": user,
        "employer_profile": employer_profile,
        "company_data": company_data
    }
    return render_template("company/employer_profile.html", **context)


@company_bp.route("/profile", methods=["GET"])
@flask_error_handler
@login_required
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

    return render_template("company/view_company_profile.html", **context)

@company_bp.route("/employer/profile", methods=["GET"])
@flask_error_handler
@login_required
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
    return render_template("company/view_employer_profile.html", **context)


@company_bp.route("/jobs", methods=["GET", "POST"])
@flask_error_handler
@login_required
async def manage_jobs(user: User):
    """Job post management (mirrors ATS tool pattern)"""

    if not user.role == "employer":
        flash(message="You are not associated with any company please create a company in order to continue",
        category="danger")
        return redirect(url_for('company.view_employer_profile'))
    company_controller = get_controller('company')
    _employer_profile: Employer = await company_controller.get_employer_by_uid(user_id=user.uid)
    if not _employer_profile:
        flash("Please create your employer profile before posting or viewing jobs", "danger")
        return redirect(url_for('company.view_employer_profile'))

    if not (_employer_profile.is_valid and _employer_profile.is_verified):
        flash("Please verify your employer profile before posting or viewing jobs", "danger")
        return redirect(url_for('company.view_employer_profile'))

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
@flask_error_handler
@login_required
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
@flask_error_handler
@login_required
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
    return render_template("company/analytics.html", **context)

@company_bp.route("/verify-employer-profile", methods=["POST"])
@flask_error_handler
@login_required
async def initiate_employer_verification(user: User):
    """Start company verification process"""
    company_controller = get_controller('company')
    employer_orm = await company_controller.get_employer_by_uid(user_uid=user.uid)
    if not employer_orm:
        flash(message="please create the employer profile first", category='danger')
        return redirect(url_for("company.view_employer_profile"))

    employer = Employer(**employer_orm.to_dict())

    if not employer.is_valid:
        flash(message="please ensure your employer profile is complete before attemmpting verification", category="danger")
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
        return render_template("employers/employer_verification_failed.html", **context)

    if not employer.is_token_valid(token):
        flash("The verification link is invalid or has expired.", "danger")
        return render_template("employers/employer_verification_failed.html", **context)

    # Mark as verified and remove token
    _ = await company_controller.mark_employer_as_verified(employer_id=employer_id)

    flash("Your profile has been successfully verified!", "success")


    return render_template("employers/employer_verification_success.html", **context)


@company_bp.route('/submit-company-verification', methods=['GET', 'POST'])
@flask_error_handler
@login_required
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
        return render_template('company/verification_status.html', company=company, status_info=status_info)

    if company.verification_status == CompanyVerificationStatus.PENDING.value:
        flash("Verification is already in progress", "warning")
        status_info = await company_controller.get_company_verification_status(company.company_id)
        return render_template('company/verification_status.html', company=company, status_info=status_info)

    # Handle form submission
    if request.method == 'POST':
        # Extract CIPC details from form
        reg_form_data = request.form.to_dict()

        cipc_data = CompanyCIPC(company_name=reg_form_data.get("name"),
                                registration_number= reg_form_data.get('registration_number'),
                                registration_date=reg_form_data.get("registration_date"),
                                director_name= reg_form_data.get("director_name"),
                                bee_status=reg_form_data.get("bee_status"),
                                tax_pin=reg_form_data.get("tax_pin"))

        # Validate required CIPC fields
        required_fields = ["name", "registration_number", "director_name"]
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
                # Save file
                filename = secure_filename(f"{company.company_id}_{doc_type}_{file.filename}")
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                await file.save(file_path)

                # Create document record
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
                company_id=company.company_id
            )
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

@company_bp.route('/verification-status')
@flask_error_handler
@login_required
async def verification_status(user: User):
    """Show current verification status"""
    company_controller = get_controller('company')
    employer = await company_controller.get_employer_by_uid(user.uid)
    if not employer or not employer.company_id:
        return redirect(url_for('company.create_company_profile'))

    company = await company_controller.get_company_by_id(employer.company_id)
    status_info = await company_controller.get_company_verification_status(company.company_id)

    return render_template('company/verification_status.html',company=company,status_info=status_info)

@company_bp.route("/billing")
@flask_error_handler
async def billing():
    return render_template("company/billing.html")  # Placeholder template

@company_bp.route("/settings")
async def settings():
    return render_template("company/settings.html")  # Placeholder template

@company_bp.route("/employers")
@flask_error_handler
@login_required
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
    employers = await company_controller.get_all_company_employers(company_id=_employer_profile.company_id)
    context = {
        "current_user": user,
        "employer_profile": _employer_profile,
        "employers": employers
    }

    return render_template("company/employers.html",**context)

@company_bp.route("/me")
@flask_error_handler
@login_required
async def get_dashboard(user: User):
    company_controller = get_controller('company')
    employer = await company_controller.get_employer_by_uid(user.uid)

    if not employer:
        flash(message="You need to create your Employer Profile before you can access your Dashboard.", category="warning")
        return redirect(url_for('company.view_employer_profile'))
    # 2. Get company data
    company: Company = await company_controller.get_company_by_id(employer.company_id)
    if not company:
        flash(message="Please create your Company Profile before you can access your Dashboard.", category="warning")
        return redirect(url_for('company.create_company_profile'))

    # 5. Determine verification progress (for checklist/progress bar)
    verification_steps = [
        {'name': 'Employer Verified', 'complete': employer.is_verified},
        {'name': 'Documents Submitted', 'complete': bool(getattr(company, 'documents_submitted', False))},
        {'name': 'Company Verified', 'complete': company.verification_status == CompanyVerificationStatus.VERIFIED.value}
    ]
    
    context = dict(
        current_user=user,
        company=company,
        employer=employer,
        verification_steps=verification_steps
    )
    return render_template(
        "company/dashboard.html",
        **context
    )
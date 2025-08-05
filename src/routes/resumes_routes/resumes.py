# Standard Library
import asyncio
from datetime import date, datetime

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


from src.controllers.resumes import ResumeController
# Authentication
from src.authentication import jobseeker_login

# Domain Models
from src.database.models import (
    User,
    JobSeekerCV,
    Experience,
    Education,
    Certification,
    Language,
    Project,
    Publication,
    Award,
    CustomSection,
)

# Constants
from src.database.constants import utc_time

# Routes
from src.routes import flask_error_handler

# Utilities
from src.utils.route_helpers import get_controller, get_service

resume_routes = Blueprint(
    "jobseeker_cv",
    __name__,
    url_prefix="/jobseeker/cv",
    template_folder="templates/jobseekers"
)


def _parse_date(date_str: str) -> date:
    """Helper to parse date strings from form data"""
    return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None


def _parse_short_date(date_str):
    """Parse date from YYYY-MM format"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m").date()
    except ValueError:
        return None

def _parse_cv_form_data(form_data, files, user_uid):
    structured_data = {
        'user_uid': user_uid,
        'professional_title': form_data.get('professional_title'),
        'summary': form_data.get('summary'),
        'location': form_data.get('location'),
        'phone': form_data.get('phone'),
        'website': form_data.get('website'),
        'linkedin': form_data.get('linkedin'),
        'github': form_data.get('github'),
        'skills': [s.strip() for s in form_data.get('skills', '').split(',') if s.strip()],
        'portfolio_links': [link.strip() for link in form_data.get('portfolio_links', '').split(',') if link.strip()],
    }

    sections = {
        'experience': Experience,
        'education': Education,
        'certifications': Certification,
        'languages': Language,
        'projects': Project,
        'publications': Publication,
        'awards': Award,
        'custom_sections': CustomSection
    }

    def _parse_date(date_str):
        """Parse date from YYYY-MM format"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m").date()
        except ValueError:
            return None

    for section, model in sections.items():
        structured_data[section] = []
        index = 0

        # Keep processing while we find items with this index
        while True:
            item_data = {}
            has_data = False

            # Get all fields for this section item
            for field in model.model_fields:
                key = f"{section}[{index}][{field}]"
                value = form_data.get(key)

                if value:
                    has_data = True

                # Handle special field types
                if 'date' in field and value:
                    item_data[field] = _parse_date(value)
                elif field == 'technologies' and value:
                    item_data[field] = [t.strip() for t in value.split(',')]
                else:
                    item_data[field] = value

            # Stop if no data found for this index
            if not has_data:
                break

            # Add to section data
            structured_data[section].append(item_data)
            index += 1

    return structured_data


def lenient_cv_parse(user_uid: str, data: dict) -> JobSeekerCV:
    """Lenient CV parsing with fallback values"""
    return JobSeekerCV(user_uid=user_uid, professional_title=data.get('professional_title', 'Draft CV'),
                       summary=data.get('summary', ''), skills=data.get('skills', []),
                       experience=[Experience(**e) for e in data.get('experience', [])],
                       education=[Education(**e) for e in data.get('education', [])],
                       certifications=[Certification(**c) for c in data.get('certifications', [])], )

# Add to your routes
def _parse_ats_form_data(form, files):
    pass



@resume_routes.route("/api/ats-check", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def ats_check(user: User):
    """Real-time ATS analysis endpoint"""
    try:
        # Use lenient parsing for partial CV data
        raw_data = _parse_ats_form_data(request.form, request.files)
        cv_data = lenient_cv_parse(user_uid=user.uid, data=raw_data)

        # Generate ATS report
        ats_controller = get_controller('ats')
        report = await ats_controller.generate_industry_ats_report(cv_data)

        return jsonify({
            "score": report.get('score', 0),
            "matched_keywords": report.get('matched_keywords', []),
            "missing_keywords": report.get('missing_keywords', []),
            "feedback": report.get('feedback', 'Analysis unavailable')
        })

    except ValidationError as e:
        return jsonify({
            "error": "Invalid CV format",
            "details": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "error": "ATS analysis failed",
            "details": str(e)
        }), 500




async def _get_ats_report(cv: JobSeekerCV) -> dict:
    """Get ATS report with fallback mechanism"""
    try:
        # Timeout after 15 seconds to prevent hanging
        ats_controller = get_controller('ats')
        return await asyncio.wait_for(
            ats_controller.generate_industry_ats_report(cv),
            timeout=15
        )
    except TimeoutError:
        return {"feedback": "ATS analysis timed out - results may be incomplete"}
    except Exception as e:
        return {"feedback": f"ATS analysis failed: {str(e)}"}


# noinspection PyBroadException
async def _handle_validation_error(e: ValidationError, cv: JobSeekerCV) -> dict:
    """Handle validation errors with partial ATS analysis"""
    flash(f"Validation error: {_format_pydantic_error(e)}", "danger")

    try:
        ats_controller = get_controller('ats')
        partial_report = await ats_controller.partial_ats_check(cv)
    except Exception:
        partial_report = {}

    return {
        "cv": cv,
        "form_errors": e.errors(),
        "ats_score": partial_report.get('score', 0),
        "missing_keywords": partial_report.get('missing_keywords', []),
        "matched_keywords": partial_report.get('matched_keywords', []),
        "ats_feedback": "Partial analysis due to validation errors"
    }


def _format_pydantic_error(e: ValidationError) -> str:
    """Format Pydantic errors for user display"""
    return ", ".join(
        f"{err['loc'][0]}: {err['msg']}"
        for err in e.errors()
    )


@resume_routes.route("/upload", methods=["GET", "POST"])
@flask_error_handler
@jobseeker_login
async def upload_cv(user: User):
    if request.method == "POST":
        try:
            # Parse and validate form data
            resume_logger = get_service("logger")()("CREATE_CV_ROUTE:")
            raw_data = _parse_cv_form_data(request.form, request.files, user.uid)
            resume_logger.info("---------------------------------------------------------------------")
            resume_logger.info(f" CV RAW data: {raw_data}")
            cv_data = JobSeekerCV(**raw_data)
            resume_logger.info("---------------------------------------------------------------------")
            resume_logger.info(f"Parsed CV data: {cv_data}")
            resume_logger.info("---------------------------------------------------------------------")

            # Call controller
            resumes_controller = get_controller("resume")
            resume: JobSeekerCV | None = await resumes_controller.create_cv(user_uid=user.uid, data=cv_data)
            if not resume:
                resume_logger.error("Failed to create CV - controller returned None")
                flash("Failed to create CV. Please try again.", "danger")
                return redirect(url_for("jobseeker_cv.upload_cv"))

            flash("CV created successfully!", "success")
            return redirect(url_for("jobseeker_cv.view_cv", cv_id=resume.cv_id))

        except ValidationError as e:
            flash(f"Validation error: {str(e)}", "danger")
        except Exception as e:
            flash(f"Error creating CV: {str(e)}", "danger")

    context = dict(current_user=user)
    return render_template("jobseekers/upload_cv.html", **context)


@resume_routes.route("/view/<string:cv_id>")
@flask_error_handler
@jobseeker_login
async def view_cv(user: User, cv_id: str):
    resume_controller: ResumeController = get_controller("resume")
    resume_logger = get_service("logger")()("VIEW_CV_ROUTE:")
    cv = await resume_controller.get_cv_by_id(cv_id)
    resume_logger.info(f"CV IN ROUTER +++++++++++++++++++++++++++++++++: {cv}")
    ats_report = await _get_ats_report(cv=cv)

    context = dict(
        current_user=user,
        cv=cv,  # Keep original for complex operations
        ats_report=ats_report
    )
    return render_template("jobseekers/cv/view_cv.html", **context)

@resume_routes.route("/delete/<string:cv_id>", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def delete_cv(user: User, cv_id: str):

    try:
        resume_controller = get_controller("resume")
        await resume_controller.delete_cv(cv_id)
        flash("CV deleted successfully", "success")
    except Exception as e:
        flash(f"Error deleting CV: {str(e)}", "danger")

    return redirect(url_for("jobseeker_cv.list_cvs"))


@resume_routes.route("/list")
@flask_error_handler
@jobseeker_login
async def list_cvs(user: User):
    resume_controller = get_controller("resume")
    cvs = await resume_controller.list_cvs_for_user(user_uid=user.uid)
    context = dict(current_user=user, cvs=cvs)
    return render_template("jobseekers/cv/cv_list.html", **context)


# --------------------------------------------------------------------------------------------------
# -----------------------------------SECTION EDIT ROUTES--------------------------------------------
# --------------------------------------------------------------------------------------------------
@resume_routes.route("/edit/<string:cv_id>", methods=["GET", "POST"])
@flask_error_handler
@jobseeker_login
async def edit_cv(user: User, cv_id: str):
    resume_controller: ResumeController = get_controller('resume')
    if request.method == "POST":
        try:
            start_time = utc_time()
            raw_data = _parse_cv_form_data(form_data=request.form, files=request.files, user_uid=user.uid)
            updated_data = JobSeekerCV(**raw_data)
            resume_controller = get_controller('resume')
            # Update CV first
            await resume_controller.update_cv(
                user_uid=user.uid,
                cv_id=cv_id,
                data=updated_data
            )

            # Async ATS analysis after successful update
            ats_controller = get_controller('ats')
            await ats_controller.queue_ats_analysis(cv_id)

            flash("CV updated successfully! ATS analysis in progress...", "success")
            return redirect(url_for("jobseeker_cv.view_cv", cv_id=cv_id))

        except ValidationError as e:
            # Get partial CV data for error recovery
            cv = await resume_controller.get_cv_by_id(cv_id)
            context = await _handle_validation_error(e, cv)
            return render_template("jobseekers/cv/edit_cv.html", **context)

        except Exception as e:
            flash(f"Error updating CV: {str(e)}", "danger")
            return redirect(url_for("jobseeker_cv.list_cvs"))

    # GET: Load with real-time ATS analysis
    try:
        cv = await resume_controller.get_cv_by_id(cv_id)
        ats_report = await _get_ats_report(cv)

        context = {
            "current_user": user,
            "cv": cv,
            "ats_report": ats_report,
            "section_completeness": ats_report.get('section_completeness', {})
        }
        return render_template("jobseekers/cv/edit_cv.html", **context)

    except Exception as e:
        flash(f"Error loading CV: {str(e)}", "danger")
        return redirect(url_for("jobseeker_cv.list_cvs"))


@resume_routes.route("/add/experience/<string:cv_id>", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def add_experience(user: User, cv_id: str):
    form_data = request.form
    experience_data = Experience(**{
        'cv_id': cv_id,
        'job_title': form_data.get('job_title'),
        'company': form_data.get('company'),
        'start_date': _parse_short_date(form_data.get('start_date')),
        'end_date': _parse_short_date(form_data.get('end_date')),
        'location': form_data.get('location'),
        'description': form_data.get('description')
    })
    resume_logger = get_service('logger')()("ADD_EXPERIENCE_ROUTE:")
    resume_logger.info(f"Adding experience for user {user.uid}: {experience_data}")
    resume_controller = get_controller('resume')
    await resume_controller.add_experience(user.uid, experience_data)
    flash("Experience added successfully!", "success")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=cv_id))


@resume_routes.route("/edit/experience/<string:exp_id>", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def edit_experience(user: User, exp_id: str):
    form_data = request.form
    experience_data = Experience(**{
        'id': exp_id,
        'cv_id': form_data.get('cv_id'),
        'job_title': form_data.get('job_title'),
        'company': form_data.get('company'),
        'start_date': _parse_short_date(form_data.get('start_date')),
        'end_date': _parse_short_date(form_data.get('end_date')),
        'location': form_data.get('location'),
        'description': form_data.get('description')
    })
    resume_logger = get_service('logger')()("EDIT_EXPERIENCE_ROUTE:")
    resume_logger.info(f"Editing experience {exp_id} for user {user.uid}: {experience_data}")
    resume_controller = get_controller('resume')
    await resume_controller.update_experience(exp_id, experience_data)
    flash("Experience updated successfully!", "success")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/add/education<string:cv_id>", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def add_education(user: User, cv_id: str):
    """Add education details to the CV"""
    form_data = request.form
    education_data = Education(**{
        'cv_id': cv_id,
        'qualification': form_data.get('qualification'),
        'institution': form_data.get('institution'),
        'start_date': _parse_short_date(form_data.get('start_date')),
        'end_date': _parse_short_date(form_data.get('end_date')),
        'field_of_study': form_data.get('field_of_study'),
        'description': form_data.get('description')
    })

    resume_controller = get_controller('resume')
    await resume_controller.add_education(user.uid, education_data)
    flash("Education added successfully!", "success")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=cv_id))


@resume_routes.route("/edit/education/<string:edu_id>", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def edit_education(user: User, edu_id: str):
    try:
        form_data = request.form
        education_data = Education(**{
            "id": edu_id,
            'cv_id': form_data.get('cv_id'),
            'qualification': form_data.get('qualification'),
            'institution': form_data.get('institution'),
            'start_date': _parse_short_date(form_data.get('start_date')),
            'end_date': _parse_short_date(form_data.get('end_date')),
            'field_of_study': form_data.get('field_of_study'),
            'description': form_data.get('description')
        })

        resume_controller = get_controller('resume')
        await resume_controller.update_education(edu_id, education_data)
        flash("Education updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating education: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/add/certification/<string:cv_id>", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def add_certification(user: User, cv_id: str):
    try:
        form_data = request.form
        certification_data = Certification(**{
            'cv_id': cv_id,
            'name': form_data.get('name'),
            'issuer': form_data.get('issuer'),
            'issue_date': _parse_short_date(form_data.get('issue_date')),
            'expiry_date': _parse_short_date(form_data.get('expiry_date')),
            'credential_url': form_data.get('credential_url')
        })

        resume_controller = get_controller('resume')
        await resume_controller.add_certification(user.uid, certification_data)
        flash("Certification added successfully!", "success")
    except Exception as e:
        flash(f"Error adding certification: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/edit/certification/<string:cert_id>", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def edit_certification(user: User, cert_id: str):
    try:
        form_data = request.form
        certification_data = Certification(**{
            'id': cert_id,
            'cv_id': form_data.get('cv_id'),
            'name': form_data.get('name'),
            'issuer': form_data.get('issuer'),
            'issue_date': _parse_short_date(form_data.get('issue_date')),
            'expiry_date': _parse_short_date(form_data.get('expiry_date')),
            'credential_url': form_data.get('credential_url')
        })
        resume_controller = get_controller('resume')
        await resume_controller.update_certification(cert_id, certification_data)
        flash("Certification updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating certification: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/add/language", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def add_language(user: User):
    try:
        form_data = request.form
        language_data = {
            'name': form_data.get('name'),
            'proficiency': form_data.get('proficiency')
        }
        resume_controller = get_controller('resume')
        await resume_controller.add_language(user.uid, language_data)
        flash("Language added successfully!", "success")
    except Exception as e:
        flash(f"Error adding language: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/edit/language/<string:lang_id>", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def edit_language(user: User, lang_id: str):
    try:
        form_data = request.form
        language_data = {
            'name': form_data.get('name'),
            'proficiency': form_data.get('proficiency')
        }
        resume_controller = get_controller('resume')
        await resume_controller.update_language(lang_id, language_data)
        flash("Language updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating language: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/add/project", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def add_project(user: User):
    try:
        form_data = request.form
        project_data = {
            'title': form_data.get('title'),
            'description': form_data.get('description'),
            'technologies': [tech.strip() for tech in form_data.get('technologies', '').split(',')],
            'link': form_data.get('link')
        }
        resume_controller = get_controller('resume')
        await resume_controller.add_project(user.uid, project_data)
        flash("Project added successfully!", "success")
    except Exception as e:
        flash(f"Error adding project: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/edit/project/<string:project_id>", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def edit_project(user: User, project_id: str):
    try:
        form_data = request.form
        project_data = {
            'title': form_data.get('title'),
            'description': form_data.get('description'),
            'technologies': [tech.strip() for tech in form_data.get('technologies', '').split(',')],
            'link': form_data.get('link')
        }
        resume_controller = get_controller('resume')
        await resume_controller.update_project(project_id, project_data)
        flash("Project updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating project: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/add/publication", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def add_publication(user: User):
    try:
        form_data = request.form
        publication_data = {
            'title': form_data.get('title'),
            'publisher': form_data.get('publisher'),
            'date': _parse_date(form_data.get('date')),
            'link': form_data.get('link')
        }
        resume_controller = get_controller('resume')
        await resume_controller.add_publication(user.uid, publication_data)
        flash("Publication added successfully!", "success")
    except Exception as e:
        flash(f"Error adding publication: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/edit/publication/<string:pub_id>", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def edit_publication(user: User, pub_id: str):
    try:
        form_data = request.form
        publication_data = {
            'title': form_data.get('title'),
            'publisher': form_data.get('publisher'),
            'date': _parse_date(form_data.get('date')),
            'link': form_data.get('link')
        }
        resume_controller = get_controller('resume')
        await resume_controller.update_publication(pub_id, publication_data)
        flash("Publication updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating publication: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/add/award", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def add_award(user: User):
    try:
        form_data = request.form
        award_data = {
            'title': form_data.get('title'),
            'issuer': form_data.get('issuer'),
            'date': _parse_date(form_data.get('date')),
            'description': form_data.get('description')
        }
        resume_controller = get_controller('resume')
        await resume_controller.add_award(user.uid, award_data)
        flash("Award added successfully!", "success")
    except Exception as e:
        flash(f"Error adding award: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/edit/award/<string:award_id>", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def edit_award(user: User, award_id: str):
    try:
        form_data = request.form
        award_data = {
            'title': form_data.get('title'),
            'issuer': form_data.get('issuer'),
            'date': _parse_date(form_data.get('date')),
            'description': form_data.get('description')
        }
        resume_controller = get_controller('resume')
        await resume_controller.update_award(award_id, award_data)
        flash("Award updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating award: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/add/custom_section", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def add_custom_section(user: User):
    try:
        form_data = request.form
        custom_section_data = {
            'title': form_data.get('title'),
            'content': form_data.get('content')
        }
        resume_controller = get_controller('resume')
        await resume_controller.add_custom_section(user.uid, custom_section_data)
        flash("Custom section added successfully!", "success")
    except Exception as e:
        flash(f"Error adding custom section: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/edit/custom_section/<string:section_id>", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def edit_custom_section(user: User, section_id: str):
    try:
        form_data = request.form
        custom_section_data = {
            'title': form_data.get('title'),
            'content': form_data.get('content')
        }
        resume_controller = get_controller('resume')
        await resume_controller.update_custom_section(section_id, custom_section_data)
        flash("Custom section updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating custom section: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/add/skill", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def add_skill(user: User):
    try:
        form_data = request.form
        skills_data = {
            'skills': [skill.strip() for skill in form_data.get('skills', '').split(',')]
        }
        resume_controller = get_controller('resume')
        await resume_controller.add_skills(user.uid, skills_data)
        flash("Skill added successfully!", "success")
    except Exception as e:
        flash(f"Error adding skill: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/edit/skills", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def edit_skills(user: User):
    try:
        form_data = request.form
        skills_data = {
            'skills': [skill.strip() for skill in form_data.get('skills', '').split(',')]
        }
        resume_controller = get_controller('resume')
        await resume_controller.update_skills(user.uid, skills_data)
        flash("Skills updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating skills: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/add/portfolio_link", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def add_portfolio_link(user: User):
    try:
        form_data = request.form
        portfolio_links_data = {
            'portfolio_links': [link.strip() for link in form_data.get('portfolio_links', '').split(',')]
        }
        resume_controller = get_controller('resume')
        await resume_controller.add_portfolio_links(user.uid, portfolio_links_data)
        flash("Portfolio link added successfully!", "success")
    except Exception as e:
        flash(f"Error adding portfolio link: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))


@resume_routes.route("/edit/portfolio_links", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def edit_portfolio_links(user: User):
    try:
        form_data = request.form
        portfolio_links_data = {
            'portfolio_links': [link.strip() for link in form_data.get('portfolio_links', '').split(',')]
        }
        resume_controller = get_controller('resume')
        await resume_controller.update_portfolio_links(user.uid, portfolio_links_data)
        flash("Portfolio links updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating portfolio links: {str(e)}", "danger")
    return redirect(url_for("jobseeker_cv.edit_cv", cv_id=form_data.get('cv_id')))

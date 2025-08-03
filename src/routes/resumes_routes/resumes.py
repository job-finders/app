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
from src.utils.route_helpers import get_controller

resume_routes = Blueprint(
    "jobseeker_cv",
    __name__,
    url_prefix="/jobseeker/cv",
    template_folder="templates/jobseekers"
)


def _parse_date(date_str: str) -> date:
    """Helper to parse date strings from form data"""
    return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None


def _parse_cv_form_data(form_data, files, user_uid):
    """Enhanced form parser with all CV sections"""
    structured_data = {
        'user_uid': user_uid,  # Include user_uid in the structured data
        'professional_title': form_data.get('professional_title'),
        'summary': form_data.get('summary'),
        'location': form_data.get('location'),
        'phone': form_data.get('phone'),
        'website': form_data.get('website'),
        'linkedin': form_data.get('linkedin'),
        'github': form_data.get('github'),
        'skills': [s.strip() for s in form_data.get('skills', '').split(',') if s.strip()], }

    # Process all sections dynamically using Pydantic v2 syntax
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
    resume_controller = get_controller('resume')
    for section, model in sections.items():
        structured_data[section] = []
        index = 0

        while True:
            prefix = f"{section}[{index}]"
            field_data = {}

            # Use model.model_fields instead of __fields__
            # noinspection PyTypeChecker
            for field_name in model.model_fields:
                form_key = f"{prefix}[{field_name}]"
                value = form_data.get(form_key)

                # Handle special field types
                if 'date' in field_name and value:
                    field_data[field_name] = _parse_date(value)
                elif field_name == 'technologies' and value:
                    field_data[field_name] = [t.strip() for t in value.split(',')]
                else:
                    field_data[field_name] = value
            # Check if we have at least one field with data
            if not any(field_data.values()):
                break
            # Handle file uploads for certifications
            if section == 'certifications':
                file = files.get(f"{prefix}[file]")
                if file and file.filename != '':
                    file_url = resume_controller.store_certificate_file(file)
                    field_data['credential_url'] = file_url

            structured_data[section].append(field_data)
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



@resume_routes.route("/edit/<string:cv_id>", methods=["GET", "POST"])
@flask_error_handler
@jobseeker_login
async def edit_cv(user: User, cv_id: str):
    resume_controller: ResumeController = get_controller('resume')
    if request.method == "POST":
        try:
            start_time = utc_time()
            raw_data = _parse_cv_form_data(request.form, request.files)
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
            "ats_score": ats_report.get('score', 0),
            "missing_keywords": ats_report.get('missing_keywords', []),
            "matched_keywords": ats_report.get('matched_keywords', []),
            "quality_metrics": ats_report.get('quality_metrics', {}),
            "ats_feedback": ats_report.get('feedback', 'Analysis pending'),
            "section_completeness": ats_report.get('section_completeness', {})
        }
        return render_template("jobseekers/cv/edit_cv.html", **context)

    except Exception as e:
        flash(f"Error loading CV: {str(e)}", "danger")
        return redirect(url_for("jobseeker_cv.list_cvs"))


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
            raw_data = _parse_cv_form_data(request.form, request.files, user.uid)
            cv_data = JobSeekerCV(**raw_data)

            # Call controller
            resumes_controller = get_controller("resume")
            result = await resumes_controller.create_cv(
                user_uid=user.uid,
                data=cv_data
            )

            flash("CV created successfully!", "success")
            return redirect(url_for("jobseeker_cv.view_cv", cv_id=result['cv_id']))

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
    cv = await resume_controller.get_cv_by_id(cv_id)
    ats_report = await _get_ats_report(cv=cv)
    context = dict(current_user=user, cv=cv, ats_report=ats_report)
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

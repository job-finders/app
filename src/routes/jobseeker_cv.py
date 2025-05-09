from flask import Blueprint, render_template, request, redirect, url_for, flash
from pydantic import ValidationError
from src.authentication import login_required
from src.database.models.users import User
from src.main import resume_controller
from src.routes import flask_error_handler
from src.database.models.resume import JobSeekerCV

jobseeker_cv_bp = Blueprint(
    "jobseeker_cv",
    __name__,
    url_prefix="/jobseeker/cv",
    template_folder="templates/jobseekers"
)


def _parse_cv_form_data(form_data, files):
    """Helper to structure form data into JobSeekerCV model format"""
    structured_data = {
        'professional_title': form_data.get('professional_title'),
        'summary': form_data.get('summary'),
        'location': form_data.get('location'),
        'phone': form_data.get('phone'),
        'website': form_data.get('website'),
        'linkedin': form_data.get('linkedin'),
        'github': form_data.get('github'),
        'skills': [s.strip() for s in form_data.get('skills', '').split(',') if s.strip()],
    }

    # Process dynamic sections
    for section in ['experience', 'education', 'certifications']:
        structured_data[section] = []
        index = 0

        while True:
            # Check if at least one field exists for this index
            if not form_data.get(f'{section}[{index}][name]'):
                break

            entry = {
                'name': form_data.get(f'{section}[{index}][name]'),
                'issuer': form_data.get(f'{section}[{index}][issuer]'),
                'start_date': form_data.get(f'{section}[{index}][start_date]'),
                'end_date': form_data.get(f'{section}[{index}][end_date]'),
                'description': form_data.get(f'{section}[{index}][description]'),
            }

            # Handle file upload for certifications
            if section == 'certifications':
                file = files.get(f'{section}[{index}][file]')
                if file and file.filename != '':
                    # In real implementation: Save file and get URL
                    entry['credential_url'] = f"/uploads/{file.filename}"

            structured_data[section].append(entry)
            index += 1

    return structured_data


@jobseeker_cv_bp.route("/upload", methods=["GET", "POST"])
@login_required
@flask_error_handler
async def upload_cv(user: User):


    if request.method == "POST":
        try:
            # Parse and validate form data
            raw_data = _parse_cv_form_data(request.form, request.files)
            cv_data = JobSeekerCV(**raw_data)

            # Call controller
            result = await resume_controller.create_cv(
                user_uid=user.uid,
                data=cv_data
            )

            flash("CV created successfully!", "success")
            return redirect(url_for("jobseeker_cv.view_cv", cv_id=result['cv_id']))

        except ValidationError as e:
            flash(f"Validation error: {str(e)}", "danger")
        except Exception as e:
            flash(f"Error creating CV: {str(e)}", "danger")

    return render_template("jobseekers/upload_cv.html")


@jobseeker_cv_bp.route("/edit/<string:cv_id>", methods=["GET", "POST"])
@login_required
@flask_error_handler
async def edit_cv(user: User, cv_id: str):


    if request.method == "POST":
        try:
            # Parse and validate updated data
            raw_data = _parse_cv_form_data(request.form, request.files)
            updated_data = JobSeekerCV(**raw_data)

            # Call controller
            await resume_controller.update_cv(
                user_uid=user.uid,
                cv_id=cv_id,
                data=updated_data
            )

            flash("CV updated successfully!", "success")
            return redirect(url_for("jobseeker_cv.view_cv", cv_id=cv_id))

        except ValidationError as e:
            flash(f"Validation error: {str(e)}", "danger")
        except Exception as e:
            flash(f"Error updating CV: {str(e)}", "danger")

    # GET: Load existing CV data
    cv = resume_controller.get_cv_by_id(cv_id)
    context = dict(current_user=user, cv=cv)
    return render_template("jobseekers/cv/edit_cv.html", **context)


@jobseeker_cv_bp.route("/view/<string:cv_id>")
@login_required
@flask_error_handler
async def view_cv(user: User, cv_id: str):

    cv = await resume_controller.get_cv_by_id(cv_id)
    context = dict(current_user=user, cv=cv)
    return render_template("jobseekers/cv/view_cv.html", **context)


@jobseeker_cv_bp.route("/delete/<string:cv_id>", methods=["POST"])
@login_required
@flask_error_handler
async def delete_cv(user: User, cv_id: str):


    try:
        await resume_controller.delete_cv(cv_id)
        flash("CV deleted successfully", "success")
    except Exception as e:
        flash(f"Error deleting CV: {str(e)}", "danger")

    return redirect(url_for("jobseeker_cv.list_cvs"))


@jobseeker_cv_bp.route("/list")
@login_required
@flask_error_handler
async def list_cvs(user: User):

    cvs = await resume_controller.list_cvs_for_user(user_uid=user.uid)
    context = dict(current_user=user, cvs=cvs)
    return render_template("jobseekers/cv/cv_list.html", **context)

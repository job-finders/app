from pydantic import ValidationError
from flask import Blueprint, render_template, request, redirect, url_for, flash

from src.routes import flask_error_handler
from src.authentication import login_required
from src.database.models.users import User
from src.main import job_seeker_profile_controller
from src.database.models.jobseeker_profile import JobSeekerProfile

jobseeker_profiles_bp = Blueprint("jobseeker_profiles", __name__, url_prefix="/profiles/jobseekers")


@jobseeker_profiles_bp.route("/create", methods=["GET", "POST"])
@flask_error_handler
@login_required
async def create_profile(user: User):
    # Fetch config options for form
    locations = await job_seeker_profile_controller.get_default_work_locations()
    industries = await job_seeker_profile_controller.get_industries_of_interest()
    job_titles = await job_seeker_profile_controller.get_job_titles_of_interest()

    if request.method == "POST":
        try:
            form_data = request.form.to_dict()
            form_data["user_uid"] = user.uid
            form_data["job_titles_of_interest"] = request.form.getlist("job_titles_of_interest")
            form_data["industries_of_interest"] = request.form.getlist("industries_of_interest")
            form_data["locations_of_interest"] = request.form.getlist("locations_of_interest")

            profile_data = JobSeekerProfile(**form_data)
            jobseeker_profile = await job_seeker_profile_controller.create_profile(profile_data)
            if jobseeker_profile:
                flash("Profile created successfully.", "success")
                return redirect(url_for("jobseeker_profiles.view_profile"))
        except ValidationError as e:
            flash("Validation error. Please check your inputs.", "danger")
            context = dict(
                current_user=user,
                locations=locations,
                industries=industries,
                job_titles=job_titles,
                errors=e.errors(),
                form_data=form_data)

            return render_template("jobseekers/profiles/create.html", **context)

    # GET request
    context = dict(current_user=user,job_titles=job_titles, locations=locations, industries=industries)
    return render_template("jobseekers/profiles/create.html", **context)


@jobseeker_profiles_bp.route("/me")
@login_required
async def view_profile(user: User):
    profile: JobSeekerProfile = await job_seeker_profile_controller.get_profile_by_uid(user_uid=user.uid)
    if not profile:
        flash("Profile not found.", "warning")
        return redirect(url_for("home.get_home"))  # or a 404 page
    context = dict(current_user=user, profile=profile)
    return render_template("jobseekers/profiles/view.html", **context)


@jobseeker_profiles_bp.route("/edit", methods=["GET", "POST"])
@login_required
async def edit_profile(user: User):
    if request.method == "POST":
        update_data = request.form.to_dict()
        update_data["job_titles_of_interest"] = request.form.getlist("job_titles_of_interest")
        update_data["industries_of_interest"] = request.form.getlist("industries_of_interest")
        update_data["locations_of_interest"] = request.form.getlist("locations_of_interest")
        profile: JobSeekerProfile = await job_seeker_profile_controller.update_profile(user_uid=user.uid,
                                                                                       update_data=update_data)

        if not profile:
            flash("Profile update failed.", "danger")
            return redirect(url_for("jobseeker_profiles.view_profile"))

        flash("Profile updated successfully.", "success")
        return redirect(url_for("jobseeker_profiles.view_profile"))

    profile : JobSeekerProfile = await job_seeker_profile_controller.get_profile_by_uid(user_uid=user.uid)

    if not profile:
        flash("Profile not found.", "warning")
        return redirect(url_for("home.get_home"))

    context = dict(current_user=user, profile=profile)
    return render_template("profiles/jobsseker/edit.html", **context)


@jobseeker_profiles_bp.route("/delete", methods=["POST"])
@login_required
async def delete_profile(user: User):
    result = await job_seeker_profile_controller.delete_profile(user_uid=user.uid)
    if not result:
        flash("Failed to delete profile.", "danger")
    else:
        flash("Profile deleted successfully.", "success")
    return redirect(url_for("home.get_home"))


@jobseeker_profiles_bp.route("/search")
@login_required
async def search_profiles(user:User):
    """could be used by employers and other seekers"""
    query = request.args.get("q", "")
    profiles: list[JobSeekerProfile] = await job_seeker_profile_controller.search_profiles(query=query)
    context = dict(profiles=profiles, current_user=user, query=query)
    return render_template("profiles/jobsseker/search.html", **context)


@jobseeker_profiles_bp.route("/upload-picture", methods=["POST"])
@login_required
async def upload_picture(user: User):
    if 'file' not in request.files:
        flash("No file part in request.", "danger")
        return redirect(request.referrer)

    file = request.files
    result = await job_seeker_profile_controller.upload_profile_picture(
        user_uid=user.uid,
        file=file,
        sub_folder="profile_pics",
        allowed_extensions=["png", "jpg", "jpeg", "gif"]
    )

    if "error" in result:
        flash(result["error"], "danger")
    else:
        flash("Profile picture uploaded successfully.", "success")

    return redirect(url_for("jobseeker_profiles.view_profile"))


@jobseeker_profiles_bp.route("/role/<string:role>")
@login_required
async def list_profiles_by_role(user: User, role: str):
    profiles = await job_seeker_profile_controller.list_profiles_by_role(role)
    context = dict(profiles=profiles, current_user=user, role=role)
    return render_template("profiles/jobsseker/list.html", profiles=profiles, role=role)

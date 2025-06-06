from pydantic import ValidationError
from flask import Blueprint, render_template, request, redirect, url_for, flash

from authentication import user_details
from src.routes import flask_error_handler
from src.authentication import login_required, jobseeker_login
from src.database.models.users import User

from src.database.models.jobseeker_profile import JobSeekerProfile
from src.utils.route_helpers import get_controller
jobseeker_profiles_bp = Blueprint("jobseeker_profiles", __name__, url_prefix="/jobseeker/profile")

def parse_profile_form(form_data, user_uid):
    # Parse job titles
    job_titles = form_data.getlist("job_titles_of_interest")
    if 'other' in job_titles:
        job_titles.remove('other')
        custom_job_title = form_data.get("custom_job_title", "").strip()
        if custom_job_title:
            job_titles.append(custom_job_title)

    # Parse industries
    industries = form_data.getlist("industries_of_interest")
    if 'other' in industries:
        industries.remove('other')
        custom_industry = form_data.get("custom_industry", "").strip()
        if custom_industry:
            industries.append(custom_industry)

    # Return parsed data in a dictionary format
    return {
        "user_uid": user_uid,
        "job_titles_of_interest": job_titles,
        "industries_of_interest": industries,
        "locations_of_interest": form_data.getlist("locations_of_interest"),
        "bio": form_data.get("bio"),
        "profile_image_url": form_data.get("profile_image_url"),
        "location": form_data.get("location"),
        "phone": form_data.get("phone"),
        "website": form_data.get("website"),
        "linkedin": form_data.get("linkedin"),
        "github": form_data.get("github"),
        "remote_preference": bool(form_data.get("remote_preference")),
        "availability": form_data.get("availability"),
        "is_freelancer": bool(form_data.get("is_freelancer")),
        "freelance_skills": form_data.getlist("freelance_skills"),
        "hourly_rate": form_data.get("hourly_rate"),
        "freelance_experience": form_data.get("freelance_experience"),
        "freelance_availability": form_data.get("freelance_availability"),
        "visibility": bool(form_data.get("visibility")),
    }


@jobseeker_profiles_bp.route("/create", methods=["GET", "POST"])
@flask_error_handler
@jobseeker_login
async def create_profile(user: User):
    """
        Job Seekers Profile can be called only by Job Seekers
    :param user:
    :return:
    """
    # Fetch config options for form

    job_seeker_profile_controller = get_controller('job_seeker_profile')

    locations = await job_seeker_profile_controller.get_default_work_locations()
    industries = await job_seeker_profile_controller.get_industries_of_interest()
    job_titles = await job_seeker_profile_controller.get_job_titles_of_interest()

    if request.method == "POST":
        try:
            # Parse the form data using the parse_profile_form function
            parsed_data = parse_profile_form(request.form, user.uid)
            # Create JobSeekerProfile instance from parsed data
            profile_data = JobSeekerProfile(**parsed_data)
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
                form_data=request.form
            )
            return render_template("jobseekers/profiles/create.html", **context)

    # Handle GET request and render the form
    return render_template("jobseekers/profiles/create.html",
                           current_user=user,
                           locations=locations,
                           industries=industries,
                           job_titles=job_titles)


@jobseeker_profiles_bp.route("/me")
@flask_error_handler
@jobseeker_login
async def view_profile(user: User):
    job_seeker_profile_controller = get_controller('job_seeker_profile')
    profile: JobSeekerProfile = await job_seeker_profile_controller.get_profile_by_uid(user_uid=user.uid)

    # if not profile:
    #     flash("Please create your profile to get started", "info")
    #     return redirect(url_for("jobseeker_profiles.create_profile"))

    context = dict(current_user=user, profile=profile)
    return render_template("jobseekers/profiles/view.html", **context)


@jobseeker_profiles_bp.route("/edit", methods=["GET", "POST"])
@flask_error_handler
@jobseeker_login
async def edit_profile(user: User):
    # Fetch config options for form
    job_seeker_profile_controller = get_controller('job_seeker_profile')
    locations = await job_seeker_profile_controller.get_default_work_locations()
    industries = await job_seeker_profile_controller.get_industries_of_interest()
    job_titles = await job_seeker_profile_controller.get_job_titles_of_interest()

    if request.method == "POST":
        try:
            # Parse the form data using the parse_profile_form function
            parsed_data = parse_profile_form(request.form, user.uid)

            # Update the profile with the new parsed data
            profile_data = JobSeekerProfile(**parsed_data)
            updated_profile = await job_seeker_profile_controller.update_profile(user_uid=user.uid, update_data=profile_data.dict())

            if not updated_profile:
                flash("Profile update failed.", "danger")
                return redirect(url_for("jobseeker_profiles.view_profile"))

            flash("Profile updated successfully.", "success")
            return redirect(url_for("jobseeker_profiles.view_profile"))

        except ValidationError as e:
            flash("Validation error. Please check your inputs.", "danger")
            context = dict(
                current_user=user,
                locations=locations,
                industries=industries,
                job_titles=job_titles,
                errors=e.errors(),
                form_data=request.form
            )
            return render_template("jobseekers/profiles/edit.html", **context)

    # Fetch current profile data for GET request
    profile: JobSeekerProfile = await job_seeker_profile_controller.get_profile_by_uid(user_uid=user.uid)

    if not profile:
        flash("Profile not found.", "warning")
        return redirect(url_for("home.get_home"))

    # Pre-fill form with existing profile data for editing
    context = dict(
        current_user=user,
        profile=profile,
        locations=locations,
        industries=industries,
        job_titles=job_titles
    )
    return render_template("jobseekers/profiles/edit.html", **context)


@jobseeker_profiles_bp.route("/delete", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def delete_profile(user: User):
    job_seeker_profile_controller = get_controller('job_seeker_profile')
    result = await job_seeker_profile_controller.delete_profile(user_uid=user.uid)
    if not result:
        flash("Failed to delete profile.", "danger")
    else:
        flash("Profile deleted successfully.", "success")
    return redirect(url_for("home.get_home"))


@jobseeker_profiles_bp.route("/search")
@flask_error_handler
@login_required
async def search_profiles(user:User):
    """
        could be used by employers and other seekers
        This is a view only endpoint that displays None Sensitive Information.

        TODO - consider displaying here a public endpoint accessible through google. for profiles marked visible.
    """
    query = request.args.get("q", "")
    job_seeker_profile_controller = get_controller('job_seeker_profile')
    profiles: list[JobSeekerProfile] = await job_seeker_profile_controller.search_profiles(query=query)
    context = dict(profiles=profiles, current_user=user, query=query)
    return render_template("jobseekers/profiles/search.html", **context)


@jobseeker_profiles_bp.route("/upload-picture", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def upload_picture(user: User):
    """This will Upload a picture into a profile of a job seeker"""
    if 'file' not in request.files:
        flash("No file part in request.", "danger")
        return redirect(request.referrer)

    file = request.files
    job_seeker_profile_controller = get_controller('job_seeker_profile')
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
@flask_error_handler
@user_details
async def list_profiles_by_role(user: User, role: str):
    """
        This is a public accessible endpoint listing only public profiles.
    :param user:
    :param role:
    :return:
    """
    job_seeker_profile_controller = get_controller('job_seeker_profile')
    profiles = await job_seeker_profile_controller.list_profiles_by_role(role)

    context = dict(profiles=profiles, current_user=user, role=role)
    return render_template("jobseekers/profiles/list.html", profiles=profiles, role=role)


@jobseeker_profiles_bp.route('/activity/metrics')
@flask_error_handler
@jobseeker_login
async def get_activity_metrics(user: User):
    """
        Each Job Seeker can review their Activity in this endpoint.
    :param user:
    :return:
    """
    job_seeker_profile_controller = get_controller('job_seeker_profile')
    return await job_seeker_profile_controller.track_job_search_activity(user.user_id)



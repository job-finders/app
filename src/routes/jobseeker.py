from crypt import methods

from flask import Blueprint, render_template, request, redirect, url_for

from src.authentication import login_required
from src.authentication import user_details
from src.database.models import Job, Role
from src.database.models.users import User
from src.main import scrapper, resume_controller
from src.routes import flask_error_handler
from src.routes.utils import (create_common_context, not_found, gone, TOWN_TO_PROVINCE, create_search_context,
                              sub_job_detail)

jobseeker_route = Blueprint('jobseekers', __name__)



@jobseeker_route.route('/jobseeker/dashboard', methods=['GET'])
@login_required
@flask_error_handler
async def dashboard(user: User):
    """

    :param user:
    :return:
    """
    user_cvs = await resume_controller.list_cvs_for_user(user_uid=user.uid)
    saved_jobs = []
    seeker_stats = dict(count=len(user_cvs),cv_uploaded=bool(user_cvs), saved_jobs=saved_jobs)
    context = dict(user=user, seeker_stats=seeker_stats)
    return render_template("jobseekers/dashboard.html", **context)


@jobseeker_route.route('/jobseeker/apply', methods=['GET'])
@login_required
@flask_error_handler
async def apply(user: User):
    context = dict(user=user)
    return render_template("jobseekers/apply.html", **context)


@jobseeker_route.route('/jobseeker/saved-jobs', methods=['GET'])
@login_required
@flask_error_handler
async def saved_jobs(user: User):
    context = dict(user=user)
    return render_template("jobseekers/saved_jobs.html", **context)


@jobseeker_route.route('/jobseeker/upload-cv', methods=['GET', 'POST'])
@login_required
@flask_error_handler
async def upload_cv(user: User):
    context = dict(user=user)
    return render_template("jobseekers/upload_cv.html", **context)


@jobseeker_route.route('/jobseeker/profile', methods=['GET', 'POST'])
@login_required
@flask_error_handler
async def profile(user: User):
    context = dict(user=user)
    return render_template("jobseekers/profile.html", **context)


@jobseeker_route.route('/jobseeker/applications', methods=['GET'])
@login_required
@flask_error_handler
async def applications(user: User):
    context = dict(user=user)
    return render_template("jobseekers/applications.html", **context)


@jobseeker_route.route('/jobseeker/notifications', methods=['GET'])
@login_required
@flask_error_handler
async def notifications(user: User):
    context = dict(user=user)
    return render_template("jobseekers/notifications.html", **context)

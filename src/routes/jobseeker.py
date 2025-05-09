from flask import Blueprint, render_template

from flask import Blueprint, render_template

from src.authentication import login_required
from src.database.models.users import User
from src.main import resume_controller
from src.routes import flask_error_handler

jobseeker_route = Blueprint('jobseekers', __name__,  url_prefix="/jobseeker")



@jobseeker_route.route('/dashboard', methods=['GET'])
@flask_error_handler
@login_required
async def dashboard(user: User):
    """

    :param user:
    :return:
    """
    user_cvs = await resume_controller.list_cvs_for_user(user_uid=user.uid)
    saved_jobs = []
    seeker_stats = dict(count=len(user_cvs),cv_uploaded=bool(user_cvs), saved_jobs=saved_jobs)
    context = dict(current_user=user, seeker_stats=seeker_stats)
    return render_template("jobseekers/dashboard.html", **context)

@jobseeker_route.route('/apply', methods=['GET'])
@flask_error_handler
@login_required
async def apply(user: User):
    context = dict(current_user=user)
    return render_template("jobseekers/apply.html", **context)


@jobseeker_route.route('/saved-jobs', methods=['GET'])
@flask_error_handler
@login_required
async def saved_jobs(user: User):
    context = dict(current_user=user)
    return render_template("jobseekers/saved_jobs.html", **context)


@jobseeker_route.route('/applications', methods=['GET'])
@flask_error_handler
@login_required
async def applications(user: User):
    context = dict(current_user=user)
    return render_template("jobseekers/applications.html", **context)


@jobseeker_route.route('/notifications', methods=['GET'])
@flask_error_handler
@login_required
async def notifications(user: User):
    context = dict(current_user=user)
    return render_template("jobseekers/notifications.html", **context)

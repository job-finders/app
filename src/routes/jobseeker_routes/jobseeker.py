from flask import Blueprint, render_template, jsonify

from flask import Blueprint, render_template

from src.database.models.resume import JobSeekerCV
from src.authentication import login_required
from src.database.models.users import User

from src.routes import flask_error_handler
from src.utils.route_helpers import get_controller
jobseeker_route = Blueprint('jobseekers', __name__,  url_prefix="/jobseeker")


async def get_user_cv(uid):
    pass


@jobseeker_route.route("/ai/cv/optimize", methods=["POST"])
@login_required
async def optimize_cv(user: User):
    # TODO - please Note this is just an API
    resume_controller = get_controller('resume')
    employee_agents_controller = get_controller('employee_agents')
    primary_resume: JobSeekerCV = await resume_controller.get_primary_resume(user_uid=user.uid)
    optimized_resume: JobSeekerCV = await employee_agents_controller.optimize_primary_cv(primary_resume=primary_resume)
    return jsonify(optimized_resume.model_dump())



@jobseeker_route.route('/dashboard', methods=['GET'])
@flask_error_handler
@login_required
async def dashboard(user: User):
    """
    :param user:
    :return:
    """
    resume_controller = get_controller('resume')
    user_cvs = await resume_controller.list_cvs_for_user(user_uid=user.uid)
    _saved_jobs = []
    seeker_stats = dict(count=len(user_cvs),cv_uploaded=bool(user_cvs), saved_jobs=_saved_jobs)
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




@jobseeker_route.route('/notifications', methods=['GET'])
@flask_error_handler
@login_required
async def notifications(user: User):
    context = dict(current_user=user)
    return render_template("jobseekers/notifications.html", **context)

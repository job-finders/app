from crypt import methods

from flask import Blueprint, render_template, request, redirect, url_for

from authentication import login_required
from src.authentication import user_details
from src.database.models import Job, Role
from src.database.models.users import User
from src.main import scrapper
from src.routes import flask_error_handler
from src.routes.utils import (create_common_context, not_found, gone, TOWN_TO_PROVINCE, create_search_context,
                              sub_job_detail)

jobseeker_route = Blueprint('jobs', __name__)



@jobseeker_route.route('/jobseeker/dashboard', methods=['GET'])
@login_required
async def dashboard(user: User):
    """

    :param user:
    :return:
    """
    pass

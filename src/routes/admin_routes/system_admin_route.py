# routes/employee_agents.py
from flask import Blueprint, jsonify, render_template

from src.authentication import system_admin_login
from src.database.models.users import User
from src.routes import flask_error_handler
from src.utils.route_helpers import get_controller

system_admin_route = Blueprint('system_admin', __name__, url_prefix='/system/admin/v1')


@system_admin_route.route("/dashboard", methods=["GET"])
@flask_error_handler
@system_admin_login
async def get_admin_dashboard(user: User):
    """
    Admin endpoint to retrieve the admin dashboard data.
    :param user: The admin user making the request.
    :return: Rendered admin dashboard template.
    """
    admin_controller = get_controller('admin_controller')
    result = await admin_controller.get_admin_dashboard_data(user=user)

    return render_template('admin/dashboard.html', dashboard_data=result.data, admin_user=user)

@system_admin_route.route("/users/<string:user_id>/reset-password", methods=["POST"])
@flask_error_handler
@system_admin_login
async def reset_user_password(user: User, user_id: str):
    """
    Admin endpoint to reset a user's password.
    :param user: The admin user making the request.
    :param user_id: The ID of the user whose password is being reset.
    :return: JSON response indicating success or failure.
    """
    controller = get_controller('users')
    result = await controller.reset_user_password(user_id)

    return jsonify({
        "success": result.success,
        "message": result.message,
        "data": result.data
    }), 200 if result.success else 400

@system_admin_route.route("/users/<string:user_id>/deactivate", methods=["POST"])
@flask_error_handler
@system_admin_login
async def deactivate_user(user: User, user_id: str):
    """
    Admin endpoint to deactivate a user account.
    :param user: The admin user making the request.
    :param user_id: The ID of the user to be deactivated.
    :return: JSON response indicating success or failure.
    """
    controller = get_controller('users')
    result = await controller.deactivate_user(user_id)

    return jsonify({
        "success": result.success,
        "message": result.message,
        "data": result.data
    }), 200 if result.success else 400

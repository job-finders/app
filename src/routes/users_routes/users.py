from flask import Blueprint, request, jsonify

from src.authentication import system_admin_login
from src.logger import init_logger

from src.routes import flask_error_handler
from src.utils.route_helpers import get_controller

users_route = Blueprint('user', __name__)
users_logger = init_logger("home_logger")


@users_route.route('/create', methods=['POST'])
@flask_error_handler
@system_admin_login
async def create_user():
    data = request.get_json()
    users_controller = get_controller('users')
    user = users_controller.create_user(data)
    return jsonify(user.dict()), 201


@users_route.route('/users/<user_id>', methods=['GET'])
@flask_error_handler
@system_admin_login
async def get_user_by_id(user_id):
    users_controller = get_controller('users')
    user = users_controller.get_user_by_id(user_id)
    return jsonify(user.dict() if user else {"message": "User not found"}), 200

@users_route.route('/update/<user_id>', methods=['PUT'])
@flask_error_handler
@system_admin_login
async def update_user(user_id):
    data = request.get_json()
    users_controller = get_controller('users')
    user = users_controller.update_user(user_id, data)
    return jsonify(user.dict() if user else {"message": "User not found"}), 200

@users_route.route('/delete/<user_id>', methods=['DELETE'])
@flask_error_handler
@system_admin_login
async def delete_user(user_id):
    users_controller = get_controller('users')
    response = users_controller.delete_user(user_id)
    return jsonify(response), 200

@users_route.route('/role/<role>', methods=['GET'])
@flask_error_handler
@system_admin_login
async def get_users_by_role(role):
    users_controller = get_controller('users')
    users = users_controller.get_users_by_role(role)
    return jsonify([user.dict() for user in users] if users else {"message": "No users found"}), 200

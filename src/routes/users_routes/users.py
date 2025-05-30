from flask import Blueprint, request, jsonify

from src.logger import init_logger
from src.main import users_controller
from src.routes import flask_error_handler

users_route = Blueprint('user', __name__)
users_logger = init_logger("home_logger")


@users_route.route('/create', methods=['POST'])
@flask_error_handler
async def create_user():
    data = request.get_json()
    user = users_controller.create_user(data)
    return jsonify(user.dict()), 201


@users_route.route('/users/<user_id>', methods=['GET'])
@flask_error_handler
async def get_user_by_id(user_id):
    user = users_controller.get_user_by_id(user_id)
    return jsonify(user.dict() if user else {"message": "User not found"}), 200

@users_route.route('/update/<user_id>', methods=['PUT'])
@flask_error_handler
async def update_user(user_id):
    data = request.get_json()
    user = users_controller.update_user(user_id, data)
    return jsonify(user.dict() if user else {"message": "User not found"}), 200

@users_route.route('/delete/<user_id>', methods=['DELETE'])
@flask_error_handler
async def delete_user(user_id):
    response = users_controller.delete_user(user_id)
    return jsonify(response), 200

@users_route.route('/role/<role>', methods=['GET'])
@flask_error_handler
async def get_users_by_role(role):
    users = users_controller.get_users_by_role(role)
    return jsonify([user.dict() for user in users] if users else {"message": "No users found"}), 200

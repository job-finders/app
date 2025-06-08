from flask import Blueprint

from utils.route_helpers import get_controller

billing_routes = Blueprint("billing", __name__)

billing_controller = get_controller("billing_controller")


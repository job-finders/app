from flask import Blueprint, jsonify

from src.authentication import system_admin_login
from src.tasks.health.redies_stream_health import check_redis_stream_health

monitor_route = Blueprint("monitor", __name__, url_prefix="/system/monitor")

@monitor_route.route("/health/redis-stream", methods=["GET"])
@system_admin_login
async def redis_stream_health_check(user: User):
    result = check_redis_stream_health()
    status = 200 if result["ok"] else 503
    return jsonify(result), status

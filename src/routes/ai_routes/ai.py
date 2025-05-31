# routes/agents.py

from flask import Blueprint, request, jsonify
from src.authentication import login_required
from src.database.models.users import User
from src.logger import init_logger
from src.controllers.agents_controller import AgentsController

agents_route = Blueprint('agents', __name__, url_prefix='/agents/v1')
agents_logger = init_logger("agents_tool")

agents_controller = AgentsController()


@agents_route.route("/jobs/enhance-job-post", methods=["POST"])
@login_required
async def enhance_job_post(user: User):
    try:
        raw_data = request.get_json()
        result = await agents_controller.enhance_job_post(user_id=user.id, input_data=raw_data)
        return jsonify(result.dict()), 200
    except Exception as e:
        agents_logger.exception("Job post enhancement failed")
        return jsonify({"error": str(e)}), 500

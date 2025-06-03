# routes/agents.py

from flask import Blueprint, request, jsonify

from src.database.models import Job
from src.database.models.agent_models import JobPostInsights
from src.agents.employer import EnhanceJobPostOutput
from src.authentication import login_required
from src.database.models.users import User
from src.logger import init_logger
from src.utils.route_helpers import get_controller

employer_agents_route = Blueprint('employer_agents', __name__, url_prefix='/agents/employer/v1')
agents_logger = init_logger("agents_tool")


@employer_agents_route.route("/jobs/enhance-job-post", methods=["POST"])
@login_required
async def enhance_job_post(user: User):
    """
        partial_job_data = {
            "title": "Python Developer",
            "description": "Need developer for web applications",
            "position_type": "FULL_TIME",
            "city": "Cape Town",
            "country": "South Africa",
            "experience_level": "MID"}
    :param user:
    :return:
    """
    employer_agents_controller = get_controller('employer_agents')
    company_controller = get_controller('company')

    try:
        raw_data = request.get_json()
        result: EnhanceJobPostOutput = await employer_agents_controller.enhance_job_post(
            user_id=user.id,
            input_data=raw_data
        )
        employer_details = await company_controller.get_employer_by_uid(user_id=user.uid)
        job: Job = Job.create_from_enhanced_agent_output(agent_output=result,
                                                         employer_id=employer_details.employer_id,
                                                         company_id=employer_details.company_id)

        # Consider doing this from a sub form called create Job with AI - The Form will call this endpoint
        # and it will return a Job Post Complete - Then having another Manual Job Creation Form.
        return jsonify(job.model_dump()), 200

    except Exception as e:
        agents_logger.exception("Job post enhancement failed")
        return jsonify({"error": "Job post enhancement failed", "details": str(e)}), 500


# NEW AGENT ENDPOINT - Job Post Analysis
@employer_agents_route.route("/jobs/analyze-job-post/<string:job_id>", methods=["POST"])
@login_required
async def analyze_job_post(user: User, job_id: str):
    """
        given an existing job post analyze it and return
    :param user:
    :param job_id:
    :return:
    """
    employer_agents_controller = get_controller('employer_agents')
    try:
        # Call the agent directly through the controller
        result: JobPostInsights = await employer_agents_controller.analyze_job_post(
            user_id=user.id,
            job_id=job_id
        )
        return jsonify(result.model_dump()), 200
    except Exception as e:
        agents_logger.exception("Job post analysis failed")
        return jsonify({"error": "Job post analysis failed", "details": str(e)}), 500


# routes/agents.py
import json

from flask import Blueprint, request, jsonify, Response
from pydantic import HttpUrl

from src.controllers.agents import EmployerAgentsController
from src.controllers.jobs import JobsWorkflowController
from src.routes import flask_error_handler
from src.database.models import Job
from src.database.models.agent_models import JobPostInsights
from src.agents.employer import EnhanceJobPostOutput
from src.authentication import login_required, employer_login
from src.database.models.users import User
from src.logger import init_logger
from src.utils.route_helpers import get_controller
from src.utils import split_csv, parse_date_to_aware

employer_agents_route = Blueprint('employer_agents', __name__, url_prefix='/agents/employer/v1')
agents_logger = init_logger("agents_tool")


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, HttpUrl):
            return str(o)
        return super().default(o)


@employer_agents_route.route("/jobs/enhance-job-post/<string:job_id>", methods=["POST"])
@flask_error_handler
@employer_login
async def enhance_job_post(user: User, job_id: str):
    """
    AI-enhance a job post while preserving all dates and user-education dict.
    """
    employer_agents_controller: EmployerAgentsController = get_controller('employer_agents')
    jobs_workflow_controller: JobsWorkflowController = get_controller('jobs_workflow')

    form = request.form
    user_prompt = form.get('user_prompt', '')

    # 1. keep original dates untouched
    original_job = await jobs_workflow_controller.get_job_details(job_id=job_id)

    # 2. build partial payload exactly as the agent expects
    payload = {
        k: v
        for k, v in form.items()
        if k not in {'expires_at', 'application_deadline'}  # skip dates
    }

    # 3. parse arrays & dict so the agent sees proper Python types
    # noinspection PyTypeChecker
    payload.update(
        required_skills=split_csv(form.get('required_skills', '')),
        preferred_skills=split_csv(form.get('preferred_skills', '')),
        education_requirements=json.loads(form.get('education_requirements', '{}')),
    )

    agents_logger.info(
        f"Enhancing job post with payload: {payload} and user prompt: {user_prompt}"
    )

    # 4. run enhancement
    agent_output: EnhanceJobPostOutput = await employer_agents_controller.enhance_job_post(
        user_id=user.uid,
        user_prompt=user_prompt,
        input_data=payload,
    )

    # 5. re-apply original dates
    updated_job = await employer_agents_controller.update_enhance_existing_job(
        agent_output=agent_output,
        job=original_job,
    )

    return Response(
        updated_job.model_dump_json(exclude_unset=True),
        mimetype="application/json",
        status=200,
    )

# NEW AGENT ENDPOINT - Job Post Analysis
@employer_agents_route.route("/jobs/analyze-job-post/<string:job_id>", methods=["POST"])
@flask_error_handler
@employer_login
async def analyze_job_post(user: User, job_id: str):
    """
        given an existing job post analyze it and return
    :param user:
    :param job_id:
    :return:
    """
    agents_logger.info(f"Analyzing job post for job_id: {job_id} by user: {user.uid}")
    employer_agents_controller = get_controller('employer_agents')
    try:
        # Call the agent directly through the controller
        result: JobPostInsights = await employer_agents_controller.analyze_job_post(
            user_id=user.uid,
            job_id=job_id
        )
        return jsonify(result.model_dump()), 200
    except Exception as e:
        agents_logger.exception("Job post analysis failed")
        return jsonify({"error": "Job post analysis failed", "details": str(e)}), 500


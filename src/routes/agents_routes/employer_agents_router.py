# Standard Library
import json
# Flask Core
from flask import Blueprint, request, jsonify, Response
# Third-Party
from pydantic import HttpUrl

from src.controllers.company import CompanyController
from src.controllers.agents.candidate_benchmark_controller import CandidateBenchMarkController
# Controllers
from src.controllers.agents import EmployerAgentsController
from src.controllers.jobs import JobsWorkflowController
# Routes
from src.routes import flask_error_handler
# Domain Models
from src.database.models import JobPostInsights, User
# Agents
from src.agents.employer import EnhanceJobPostOutput
# Auth
from src.authentication import login_required, employer_login
# Logger
from src.logger import init_logger
# Utilities
from src.utils import split_csv, parse_date_to_aware
from src.utils.route_helpers import get_controller

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
    if not agent_output:
        return jsonify({"error": "Failed to enhance job post"}), 500
    # 5. re-apply original dates
    updated_job = await employer_agents_controller.update_enhance_existing_job(
        agent_output=agent_output,
        job=original_job,
    )
    if not updated_job:
        return jsonify({"error": "Failed to update job post with enhanced data"}), 500

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
        if not result:
            return jsonify({"error": "Job post analysis failed", "details": "No insights generated"}), 500

        return jsonify(result.model_dump()), 200
    except Exception as e:
        agents_logger.exception("Job post analysis failed")
        return jsonify({"error": "Job post analysis failed", "details": str(e)}), 500


@employer_agents_route.route("/jobs/candidate-benchmarking/<string:job_application_id>", methods=["POST"])
@flask_error_handler
@employer_login
async def candidate_job_application_benchmarking_employer(user: User, job_application_id: str):
    """
    Benchmark a job application from the employer's perspective.
    """
    agents_logger.info(f"Benchmarking job application {job_application_id} for user {user.uid}")
    benchmarking_controller: CandidateBenchMarkController = get_controller('candidate_benchmarking')
    company_controller: CompanyController = get_controller("company")
    try:
        employer_details = await company_controller.get_employer_by_uid(user_id=user.uid)
        result = await benchmarking_controller.benchmark_for_employer(
            job_application_id=job_application_id, employer_id=employer_details.employer_id)
        if not result:
            agents_logger.exception("Job Application Benchmarking cannot be run on fake data")
            details = "Job Application Data not Found"
            return jsonify({"error": "Job application benchmarking failed", "details": details}), 500

        return jsonify(result.model_dump()), 200
    except Exception as e:
        agents_logger.exception("Job application benchmarking failed")
        return jsonify({"error": "Job application benchmarking failed", "details": str(e)}), 500

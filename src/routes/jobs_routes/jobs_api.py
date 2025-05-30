from flask import Blueprint, jsonify, request, abort
from pydantic import BaseModel, ValidationError
from typing import List, Optional
from datetime import datetime

from src.database.models import Job, SEO
from src.logger import init_logger
from src.main import scrapper
from src.utils import static_folder, format_title

jobs_api = Blueprint('jobs_api', __name__, url_prefix='/api/v1/job')
jobs_logger = init_logger("jobs_api_logger")


# Pydantic Models for Request/Response Validation
class JobCreate(BaseModel):
    title: str
    description: str
    location: str
    salary_range: Optional[str] = None
    tags: List[str] = []
    company_id: str


class JobUpdate(JobCreate):
    status: Optional[str] = 'active'


class SimilarJobsRequest(BaseModel):
    search_term: str
    title: str
    max_results: Optional[int] = 10


# Error Handlers
@jobs_api.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify({
        "error": "Validation Error",
        "details": e.errors()
    }), 400


@jobs_api.errorhandler(404)
def handle_not_found(e):
    return jsonify({
        "error": "Resource Not Found",
        "message": str(e)
    }), 404


# API Endpoints
@jobs_api.route('/', methods=['GET'])
async def list_jobs():
    """
    List all jobs with pagination
    ---
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: List of job objects
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    jobs = await Job.find_all(skip=(page - 1) * per_page, limit=per_page)
    return jsonify([job.dict() for job in jobs])


@jobs_api.route('/<string:job_id>', methods=['GET'])
async def get_job(job_id: str):
    """
    Get single job by ID
    """
    job = await Job.find_by_id(job_id)
    if not job:
        abort(404, description="Job not found")
    return jsonify(job.dict())


@jobs_api.route('/', methods=['POST'])
async def create_job():
    """
    Create new job listing
    """
    try:
        job_data = JobCreate(**request.json)
    except ValidationError as e:
        abort(400, description=str(e))

    new_job = await Job.create(**job_data.dict())
    return jsonify(new_job.dict()), 201


@jobs_api.route('/similar', methods=['GET'])
async def find_similar_jobs():
    """
    Find similar jobs using AI matching
    ---
    parameters:
      - name: search_term
        in: query
        required: true
      - name: title
        in: query
        required: true
      - name: max_results
        in: query
        type: integer
        default: 10
    """
    try:
        params = SimilarJobsRequest(**request.args)
    except ValidationError as e:
        abort(400, description=str(e))

    jobs = await scrapper.similar_jobs(
        search_term=params.search_term,
        title=params.title,
        max_results=params.max_results
    )
    return jsonify([job.dict() for job in jobs])


@jobs_api.route('/<string:job_id>', methods=['PUT'])
async def update_job(job_id: str):
    """
    Update existing job listing
    """
    job = await Job.find_by_id(job_id)
    if not job:
        abort(404, description="Job not found")

    try:
        update_data = JobUpdate(**request.json)
    except ValidationError as e:
        abort(400, description=str(e))

    updated_job = await job.update(**update_data.dict())
    return jsonify(updated_job.dict())


@jobs_api.route('/<string:job_id>', methods=['DELETE'])
async def delete_job(job_id: str):
    """
    Delete job listing
    """
    job = await Job.find_by_id(job_id)
    if not job:
        abort(404, description="Job not found")

    await job.delete()
    return jsonify({"status": "deleted"}), 204
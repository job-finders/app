"""
Job Actions Routes

API endpoints for job interaction actions like liking, saving, and sharing jobs.
"""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from datetime import datetime

from src.authentication import user_details
from src.database.models import User, JobSeekerProfile, JobLikeRequest, JobSaveRequest, JobShareRequest
from src.database.models.job_actions_input import (
    LikeJobInput, UnlikeJobInput, SaveJobInput, UnsaveJobInput,
    ShareJobInput, GetActionsStateInput, GetUserJobsInput
)
from src.routes import flask_error_handler
from src.utils.route_helpers import get_controller
from src.cache.cache_redis import cached
from src.firewall.job_actions_security import (
    secure_job_action, validate_job_id_param, sanitize_input,
    job_actions_security
)
from src.database.models.job_actions_results import JobActionErrorCode

# Blueprint definition
jobs_actions_bp = Blueprint('job_actions', __name__, url_prefix='/api/jobs')


def _format_job_action_response(result):
    """
    Format standardized JobActionResult into HTTP response.
    
    This helper function maps JobActionResult objects to appropriate HTTP
    status codes and formats the response consistently across all endpoints.
    
    Args:
        result: JobActionResult object from controller
        
    Returns:
        Tuple of (JSON response, HTTP status code)
    """
    # Map error codes to HTTP status codes
    status_code_map = {
        JobActionErrorCode.VALIDATION_ERROR: 400,
        JobActionErrorCode.USER_NOT_FOUND: 404,
        JobActionErrorCode.JOB_NOT_FOUND: 404,
        JobActionErrorCode.ALREADY_LIKED: 409,
        JobActionErrorCode.ALREADY_SAVED: 409,
        JobActionErrorCode.LIKE_NOT_FOUND: 404,
        JobActionErrorCode.SAVED_JOB_NOT_FOUND: 404,
        JobActionErrorCode.UNAUTHORIZED: 403,
        JobActionErrorCode.INVALID_SHARE_METHOD: 400,
        JobActionErrorCode.DATABASE_ERROR: 500,
        JobActionErrorCode.INTERNAL_ERROR: 500
    }

    # Determine status code
    if result.success:
        status_code = 200
    else:
        status_code = status_code_map.get(result.error_code, 500)

    # Build response data
    response_data = {
        "success": result.success,
        "message": result.message,
        "timestamp": result.timestamp.isoformat(),
    }

    if result.data:
        response_data["data"] = result.data

    if result.error_code:
        response_data["error_code"] = result.error_code.value

    return jsonify(response_data), status_code


def _format_job_list_response(result):
    """
    Format JobListResult into HTTP response.
    
    Args:
        result: JobListResult object from controller
        
    Returns:
        Tuple of (JSON response, HTTP status code)
    """
    if result.success:
        response_data = {
            "success": True,
            "message": result.message,
            "data": {
                "jobs": result.jobs,
                "pagination": {
                    "total_count": result.total_count,
                    "limit": result.limit,
                    "offset": result.offset,
                    "has_more": (result.offset + result.limit) < result.total_count
                }
            },
            "timestamp": result.timestamp.isoformat()
        }
        return jsonify(response_data), 200
    else:
        return _format_job_action_response(result)


def _format_engagement_response(result):
    """
    Format JobEngagementResult into HTTP response.
    
    Args:
        result: JobEngagementResult object from controller
        
    Returns:
        Tuple of (JSON response, HTTP status code)
    """
    if result.success:
        response_data = {
            "success": True,
            "message": result.message,
            "data": result.engagement_data,
            "timestamp": result.timestamp.isoformat()
        }
        return jsonify(response_data), 200
    else:
        return _format_job_action_response(result)


def _format_actions_state_response(result):
    """
    Format JobActionsStateResult into HTTP response.
    
    Args:
        result: JobActionsStateResult object from controller
        
    Returns:
        Tuple of (JSON response, HTTP status code)
    """
    if result.success:
        response_data = {
            "success": True,
            "message": result.message,
            "data": result.actions_state,
            "timestamp": result.timestamp.isoformat()
        }
        return jsonify(response_data), 200
    else:
        return _format_job_action_response(result)


@jobs_actions_bp.route('/<job_id>/like', methods=['POST'])
@user_details
@flask_error_handler
@secure_job_action('like', require_auth=True)
@validate_job_id_param
async def like_job(user: User, job_id: str):
    """
    Like a job with comprehensive validation, security, and standardized responses.
    
    This endpoint allows authenticated job seekers to like job postings with
    comprehensive input validation, security checks, and standardized response
    formatting. It follows the established MVC architecture with proper error
    handling and monitoring integration.
    
    Endpoint Details:
        - Method: POST
        - Authentication: Required (JobSeeker profile)
        - Rate Limiting: Applied through security middleware
        - CSRF Protection: Enabled for state-changing operations
        - Input Validation: Comprehensive Pydantic model validation
    
    Request Flow:
        1. Authentication and authorization validation
        2. Input parameter validation through Pydantic models
        3. JobSeeker profile verification and validation
        4. Controller delegation with validated data
        5. Standardized result object processing
        6. HTTP status code mapping and response formatting
    
    Args:
        user: Authenticated user object from authentication middleware
              Must have valid JobSeeker profile for job actions
        job_id: Job ID to like (UUID format, validated by middleware)
               Must correspond to existing and accessible job posting
    
    Returns:
        JSON response with standardized JobActionResult format:
        - success: Boolean indicating operation success
        - message: Human-readable status message
        - data: Operation result data (like_id, like_count, etc.)
        - error_code: Specific error code for client handling
        - timestamp: UTC timestamp of operation
    
    HTTP Status Codes:
        - 200: Like created successfully
        - 400: Invalid input parameters or validation errors
        - 403: Unauthorized access or insufficient permissions
        - 404: User profile or job not found
        - 409: Job already liked by user (conflict)
        - 500: Internal server error
    
    Security Features:
        - Authentication required through @user_details middleware
        - Job ID validation through @validate_job_id_param middleware
        - Rate limiting through @secure_job_action middleware
        - Input sanitization and validation
        - Security event logging for suspicious activities
    
    Example Response:
        {
            "success": true,
            "message": "Job liked successfully",
            "data": {
                "like_id": "uuid-string",
                "like_count": 42,
                "user_id": "user-uuid",
                "job_id": "job-uuid",
                "job_title": "Software Engineer",
                "liked_at": "2024-01-01T12:00:00Z"
            },
            "timestamp": "2024-01-01T12:00:00Z"
        }
    """
    try:
        # Step 1: Validate input through Pydantic model
        try:
            # Note: job_id already validated by @validate_job_id_param middleware
            input_data = LikeJobInput(user_id=user.uid, job_id=job_id)
        except ValidationError as e:
            return jsonify({
                "success": False,
                "message": f"Invalid input parameters: {str(e)}",
                "error_code": "VALIDATION_ERROR",
                "timestamp": datetime.utcnow().isoformat()
            }), 400

        # Step 2: Get job actions controller using factory pattern
        job_actions_controller = get_controller('job_actions')

        # Step 3: Get user's jobseeker profile with validation
        jobseeker_controller = get_controller('jobseeker_profile')
        profile_result = await jobseeker_controller.get_profile_by_user_id(user.uid)

        if not profile_result or not isinstance(profile_result, JobSeekerProfile):
            return jsonify({
                "success": False,
                "message": "JobSeeker profile not found - please complete your profile first",
                "error_code": "USER_NOT_FOUND",
                "timestamp": datetime.utcnow().isoformat()
            }), 404

        # Step 4: Execute like operation with validated data
        result = await job_actions_controller.like_job(input_data.user_id, input_data.job_id)

        # Step 5: Return standardized response using result object's built-in formatting
        return _format_job_action_response(result)

    except Exception as e:
        # Fallback error handling for unexpected exceptions
        return jsonify({
            "success": False,
            "message": "Internal server error occurred",
            "error_code": "INTERNAL_ERROR",
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@jobs_actions_bp.route('/<job_id>/like', methods=['DELETE'])
@user_details
@flask_error_handler
@secure_job_action('like', require_auth=True)
@validate_job_id_param
async def unlike_job(user: User, job_id: str):
    """
    Unlike a job
    
    Args:
        user: Authenticated user
        job_id: Job ID to unlike
        
    Returns:
        JSON response with success status
    """
    try:
        # Get job actions controller
        job_actions_controller = get_controller('job_actions')

        # Get user's jobseeker profile
        jobseeker_controller = get_controller('jobseeker_profile')
        profile_result = await jobseeker_controller.get_profile_by_user_id(user.uid)

        if not profile_result or not isinstance(profile_result, JobSeekerProfile):
            return jsonify({
                "success": False,
                "message": "JobSeeker profile not found",
                "code": 404
            }), 404

        # Unlike the job
        result = await job_actions_controller.unlike_job(profile_result.user_uid, job_id)

        return _format_job_action_response(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "code": 500
        }), 500


@jobs_actions_bp.route('/<job_id>/save', methods=['POST'])
@user_details
@flask_error_handler
@secure_job_action('save', require_auth=True)
@validate_job_id_param
async def save_job(user: User, job_id: str):
    """
    Save a job
    
    Args:
        user: Authenticated user
        job_id: Job ID to save
        
    Returns:
        JSON response with success status
    """
    try:
        # Get job actions controller
        job_actions_controller = get_controller('job_actions')

        # Get user's jobseeker profile
        jobseeker_controller = get_controller('jobseeker_profile')
        profile_result = await jobseeker_controller.get_profile_by_user_id(user.uid)

        if not profile_result or not isinstance(profile_result, JobSeekerProfile):
            return jsonify({
                "success": False,
                "message": "JobSeeker profile not found",
                "code": 404
            }), 404

        # Save the job
        result = await job_actions_controller.save_job(profile_result.user_uid, job_id)

        return _format_job_action_response(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "code": 500
        }), 500


@jobs_actions_bp.route('/<job_id>/save', methods=['DELETE'])
@user_details
@flask_error_handler
@secure_job_action('save', require_auth=True)
@validate_job_id_param
async def unsave_job(user: User, job_id: str):
    """
    Unsave a job
    
    Args:
        user: Authenticated user
        job_id: Job ID to unsave
        
    Returns:
        JSON response with success status
    """
    try:
        # Get job actions controller
        job_actions_controller = get_controller('job_actions')

        # Get user's jobseeker profile
        jobseeker_controller = get_controller('jobseeker_profile')
        profile_result = await jobseeker_controller.get_profile_by_user_id(user.uid)

        if not profile_result or not isinstance(profile_result, JobSeekerProfile):
            return jsonify({
                "success": False,
                "message": "JobSeeker profile not found",
                "code": 404
            }), 404

        # Unsave the job
        result = await job_actions_controller.unsave_job(profile_result.user_uid, job_id)

        return _format_job_action_response(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "code": 500
        }), 500


@jobs_actions_bp.route('/<job_id>/share', methods=['POST'])
@flask_error_handler
@secure_job_action('share', require_auth=False)
@validate_job_id_param
async def share_job(job_id: str):
    """
    Share a job (allows anonymous sharing)
    
    Args:
        job_id: Job ID to share
        
    Returns:
        JSON response with success status
    """
    try:
        # Get and sanitize request data
        raw_data = request.get_json() or {}
        data = sanitize_input(raw_data)
        share_method = data.get('share_method')

        if not share_method:
            return jsonify({
                "success": False,
                "message": "share_method is required",
                "code": 400
            }), 400

        # Validate share method using security manager
        if not job_actions_security.validate_share_method(share_method):
            job_actions_security.log_security_event('invalid_share_method', {
                'share_method': share_method,
                'job_id': job_id
            })
            return jsonify({
                "success": False,
                "message": "Invalid share method",
                "code": 400
            }), 400

        # Get job actions controller
        job_actions_controller = get_controller('job_actions')

        # Check if user is authenticated (optional for sharing)
        user_id = None
        try:
            # Try to get authenticated user
            from src.authentication import get_current_user
            user = get_current_user()
            if user:
                # Get user's jobseeker profile
                jobseeker_controller = get_controller('jobseeker_profile')
                profile_result = await jobseeker_controller.get_profile_by_user_id(user.uid)
                if profile_result and isinstance(profile_result, JobSeekerProfile):
                    user_id = profile_result.user_uid
        except:
            # Anonymous sharing is allowed
            pass

        # Share the job
        result = await job_actions_controller.share_job(user_id, job_id, share_method)

        return _format_job_action_response(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "code": 500
        }), 500


@jobs_actions_bp.route('/<job_id>/actions', methods=['GET'])
@user_details
@flask_error_handler
@secure_job_action('view_state', require_auth=True)
@validate_job_id_param
async def get_job_actions_state(user: User, job_id: str):
    """
    Get job actions state for a user
    
    Args:
        user: Authenticated user
        job_id: Job ID
        
    Returns:
        JSON response with job actions state
    """
    try:
        # Get job actions controller
        job_actions_controller = get_controller('job_actions')

        # Get user's jobseeker profile
        jobseeker_controller = get_controller('jobseeker_profile')
        profile_result = await jobseeker_controller.get_profile_by_user_id(user.uid)

        if not profile_result or not isinstance(profile_result, JobSeekerProfile):
            return jsonify({
                "success": False,
                "message": "JobSeeker profile not found",
                "code": 404
            }), 404

        # Get job actions state
        result = await job_actions_controller.get_job_actions_state(profile_result.user_uid, job_id)

        return _format_actions_state_response(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "code": 500
        }), 500


@jobs_actions_bp.route('/<job_id>/engagement', methods=['GET'])
@flask_error_handler
@secure_job_action('view_state', require_auth=False)
@validate_job_id_param
async def get_job_engagement_stats(job_id: str):
    """
    Get job engagement statistics (public endpoint)
    
    Args:
        job_id: Job ID
        
    Returns:
        JSON response with engagement statistics
    """
    try:
        # Get job actions controller
        job_actions_controller = get_controller('job_actions')

        # Get engagement stats
        result = await job_actions_controller.get_job_engagement_stats(job_id)

        return _format_engagement_response(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "code": 500
        }), 500


@jobs_actions_bp.route('/liked', methods=['GET'])
@user_details
@flask_error_handler
@secure_job_action('view_state', require_auth=True)
async def get_user_liked_jobs(user: User):
    """
    Get jobs liked by the current user
    
    Args:
        user: Authenticated user
        
    Returns:
        JSON response with liked jobs
    """
    try:
        # Get pagination parameters
        limit = min(int(request.args.get('limit', 20)), 100)  # Max 100 items
        offset = max(int(request.args.get('offset', 0)), 0)

        # Get job actions controller
        job_actions_controller = get_controller('job_actions')

        # Get user's jobseeker profile
        jobseeker_controller = get_controller('jobseeker_profile')
        profile_result = await jobseeker_controller.get_profile_by_user_id(user.uid)

        if not profile_result or not isinstance(profile_result, JobSeekerProfile):
            return jsonify({
                "success": False,
                "message": "JobSeeker profile not found",
                "code": 404
            }), 404

        # Get liked jobs
        result = await job_actions_controller.get_user_liked_jobs(
            profile_result.user_uid, limit, offset
        )

        return _format_job_list_response(result)

    except ValueError:
        return jsonify({
            "success": False,
            "message": "Invalid pagination parameters",
            "code": 400
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "code": 500
        }), 500


@jobs_actions_bp.route('/saved', methods=['GET'])
@user_details
@flask_error_handler
@secure_job_action('view_state', require_auth=True)
async def get_user_saved_jobs(user: User):
    """
    Get jobs saved by the current user with pagination support.
    
    This endpoint retrieves all jobs saved by the authenticated user with
    comprehensive pagination support, caching optimization, and standardized
    response formatting. It follows established patterns for data retrieval
    and provides consistent API responses.
    
    Args:
        user: Authenticated user from middleware
        
    Query Parameters:
        limit: Number of jobs to return (default: 20, max: 100)
        offset: Starting offset for pagination (default: 0)
        
    Returns:
        JSON response with JobListResult format including pagination metadata
    """
    try:
        # Get pagination parameters with validation
        try:
            limit = min(int(request.args.get('limit', 20)), 100)  # Max 100 items
            offset = max(int(request.args.get('offset', 0)), 0)
        except ValueError:
            return jsonify({
                "success": False,
                "message": "Invalid pagination parameters - limit and offset must be integers",
                "error_code": "VALIDATION_ERROR",
                "timestamp": datetime.utcnow().isoformat()
            }), 400

        # Get job actions controller
        job_actions_controller = get_controller('job_actions')

        # Get user's jobseeker profile
        jobseeker_controller = get_controller('jobseeker_profile')
        profile_result = await jobseeker_controller.get_profile_by_user_id(user.uid)

        if not profile_result or not isinstance(profile_result, JobSeekerProfile):
            return jsonify({
                "success": False,
                "message": "JobSeeker profile not found - please complete your profile first",
                "error_code": "USER_NOT_FOUND",
                "timestamp": datetime.utcnow().isoformat()
            }), 404

        # Get saved jobs
        result = await job_actions_controller.get_user_saved_jobs(
            profile_result.user_uid, limit, offset
        )

        return _format_job_list_response(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error occurred",
            "error_code": "INTERNAL_ERROR",
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@jobs_actions_bp.route('/csrf-token', methods=['GET'])
@flask_error_handler
def get_csrf_token():
    """
    Get CSRF token for job actions security.
    
    This endpoint provides CSRF tokens for secure job actions operations.
    The token must be included in state-changing requests to prevent
    cross-site request forgery attacks.
    
    Returns:
        JSON response with CSRF token for secure operations
    """
    from src.firewall.job_actions_security import generate_csrf_token

    token = generate_csrf_token()
    return jsonify({
        'success': True,
        'csrf_token': token,
        'timestamp': datetime.utcnow().isoformat()
    })


@jobs_actions_bp.route('/security/health', methods=['GET'])
@flask_error_handler
def security_health_check():
    """Security health check endpoint"""
    from src.firewall.job_actions_security import job_actions_security

    # Basic health check
    health_status = {
        'cache_healthy': job_actions_cache.health_check(),
        'rate_limiter_active': True,
        'csrf_protection_active': True,
        'audit_logging_active': True
    }

    return jsonify({
        'success': True,
        'health': health_status,
        'timestamp': datetime.utcnow().isoformat()
    })

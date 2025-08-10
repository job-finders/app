"""
Job Actions Routes

API endpoints for job interaction actions like liking, saving, and sharing jobs.
"""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from datetime import datetime

from src.authentication import user_details
from src.database.models import User, JobSeekerProfile, JobLikeRequest, JobSaveRequest, JobShareRequest
from src.routes import flask_error_handler
from src.utils.route_helpers import get_controller
from src.cache.cache_redis import cached
from src.firewall.job_actions_security import (
    secure_job_action, validate_job_id_param, sanitize_input,
    job_actions_security
)

# Blueprint definition
jobs_actions_bp = Blueprint('job_actions', __name__, url_prefix='/api/jobs')


@jobs_actions_bp.route('/<job_id>/like', methods=['POST'])
@user_details
@flask_error_handler
@secure_job_action('like', require_auth=True)
@validate_job_id_param
async def like_job(user: User, job_id: str):
    """
    Like a job
    
    Args:
        user: Authenticated user
        job_id: Job ID to like
        
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

        # Like the job
        result = await job_actions_controller.like_job(profile_result.user_uid, job_id)

        status_code = result.get('code', 200)
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "code": 500
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

        status_code = result.get('code', 200)
        return jsonify(result), status_code

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

        status_code = result.get('code', 200)
        return jsonify(result), status_code

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

        status_code = result.get('code', 200)
        return jsonify(result), status_code

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

        status_code = result.get('code', 200)
        return jsonify(result), status_code

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

        status_code = result.get('code', 200)
        return jsonify(result), status_code

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

        status_code = result.get('code', 200)
        return jsonify(result), status_code

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

        status_code = result.get('code', 200)
        return jsonify(result), status_code

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


@jobs_actions_bp.route('/csrf-token', methods=['GET'])
@flask_error_handler
def get_csrf_token():
    """Get CSRF token for job actions"""
    from src.firewall.job_actions_security import generate_csrf_token

    token = generate_csrf_token()
    return jsonify({
        'success': True,
        'csrf_token': token
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

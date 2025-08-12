"""
Job Actions Analytics Routes

API endpoints for job actions analytics and reporting.
"""

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin

from src.controllers.controller import error_handler
from src.utils.route_helpers import get_controller, get_service

from src.authentication import (
    employer_login,
    system_admin_login,
    jobseeker_login,
    employer_job_access_required,
    require_billing_role,
)
from src.database.models.users import User
# Create blueprint
jobs_analytics_bp = Blueprint('jobs_analytics', __name__)


@jobs_analytics_bp.route('/api/jobs/<string:job_id>/engagement', methods=['GET'])
@employer_login
@error_handler
async def get_job_engagement_metrics(user: User, job_id: str):
    """Get engagement metrics for a specific job"""
    try:
        analytics_service = get_service('job_actions_analytics')
        if not analytics_service:
            return jsonify({
                "success": False,
                "message": "Analytics service not available"
            }), 503

        metrics = await analytics_service.execute('get_job_engagement_metrics', job_id)

        if not metrics:
            return jsonify({
                "success": False,
                "message": "Job not found or no engagement data"
            }), 404

        return jsonify({
            "success": True,
            "data": metrics.model_dump()
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500


@jobs_analytics_bp.route('/api/jobs/popular', methods=['GET'])
@cross_origin()
@error_handler
async def get_popular_jobs():
    """Get most popular jobs based on engagement"""
    try:
        # Get query parameters
        limit = min(int(request.args.get('limit', 10)), 50)  # Max 50 jobs
        days = min(int(request.args.get('days', 7)), 30)  # Max 30 days

        analytics_service = get_service('job_actions_analytics')
        if not analytics_service:
            return jsonify({
                "success": False,
                "message": "Analytics service not available"
            }), 503

        popular_jobs = await analytics_service.execute('get_popular_jobs_by_engagement', 
            limit=limit,
            days=days
        )

        return jsonify({
            "success": True,
            "data": {
                "jobs": popular_jobs,
                "period_days": days,
                "limit": limit
            }
        }), 200

    except ValueError as e:
        return jsonify({
            "success": False,
            "message": "Invalid query parameters"
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500


@jobs_analytics_bp.route('/api/company/<string:company_id>/engagement', methods=['GET'])
@cross_origin()
@employer_login
@error_handler
async def get_company_engagement_stats(user: User, company_id: str):
    """Get engagement statistics for a company (requires authentication)"""
    try:
        current_user = user
        if not current_user:
            return jsonify({
                "success": False,
                "message": "Authentication required"
            }), 401

        # Get query parameters
        days = min(int(request.args.get('days', 30)), 90)  # Max 90 days

        analytics_service = get_service('job_actions_analytics')
        if not analytics_service:
            return jsonify({
                "success": False,
                "message": "Analytics service not available"
            }), 503

        # TODO: Add authorization check - ensure user can access this company's data

        engagement_stats = await analytics_service.execute('get_company_engagement_stats',
            company_id=company_id,
            days=days
        )

        if not engagement_stats:
            return jsonify({
                "success": False,
                "message": "Company not found or no engagement data"
            }), 404

        return jsonify({
            "success": True,
            "data": engagement_stats.model_dump()
        }), 200

    except ValueError as e:
        return jsonify({
            "success": False,
            "message": "Invalid query parameters"
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500


@jobs_analytics_bp.route('/api/company/<company_id>/analytics-report', methods=['GET'])
@cross_origin()
@employer_login
@error_handler
async def get_company_analytics_report(user: User, company_id: str):
    """Get comprehensive analytics report for a company"""
    try:
        current_user = user
        if not current_user:
            return jsonify({
                "success": False,
                "message": "Authentication required"
            }), 401

        # Get query parameters
        days = min(int(request.args.get('days', 30)), 90)  # Max 90 days

        analytics_service = get_service('job_actions_analytics')
        if not analytics_service:
            return jsonify({
                "success": False,
                "message": "Analytics service not available"
            }), 503

        # TODO: Add authorization check - ensure user can access this company's data

        report = await analytics_service.execute('generate_job_actions_report',
            company_id=company_id,
            days=days
        )

        if not report:
            return jsonify({
                "success": False,
                "message": "Company not found or unable to generate report"
            }), 404

        return jsonify({
            "success": True,
            "data": report.model_dump()
        }), 200

    except ValueError as e:
        return jsonify({
            "success": False,
            "message": "Invalid query parameters"
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500


@jobs_analytics_bp.route('/api/company/<string:company_id>/dashboard/enhanced', methods=['GET'])
@cross_origin()
@employer_login
@error_handler
async def get_enhanced_company_dashboard(user: User, company_id: str):
    """Get enhanced company dashboard with job actions analytics"""
    try:
        current_user = user
        if not current_user:
            return jsonify({
                "success": False,
                "message": "Authentication required"
            }), 401

        jobs_controller = get_controller('jobs_workflow')
        if not jobs_controller:
            return jsonify({
                "success": False,
                "message": "Jobs service not available"
            }), 503

        # TODO: Add authorization check - ensure user can access this company's data

        dashboard = await jobs_controller.get_enhanced_company_analytics_dashboard(company_id)

        if not dashboard:
            return jsonify({
                "success": False,
                "message": "Company not found or unable to generate dashboard"
            }), 404

        return jsonify({
            "success": True,
            "data": dashboard
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500


@jobs_analytics_bp.route('/api/jobs/<string:job_id>/performance', methods=['GET'])
@cross_origin()
@employer_login
@error_handler
async def get_job_performance_metrics(user: User, job_id: str):
    """Get comprehensive performance metrics for a specific job"""
    try:
        current_user = user
        if not current_user:
            return jsonify({
                "success": False,
                "message": "Authentication required"
            }), 401

        jobs_controller = get_controller('jobs_workflow')
        if not jobs_controller:
            return jsonify({
                "success": False,
                "message": "Jobs service not available"
            }), 503

        # TODO: Add authorization check - ensure user can access this job's data

        metrics = await jobs_controller.get_job_performance_metrics(job_id)

        if not metrics:
            return jsonify({
                "success": False,
                "message": "Job not found or unable to generate metrics"
            }), 404

        return jsonify({
            "success": True,
            "data": metrics
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500


@jobs_analytics_bp.route('/api/users/<string:user_id>/engagement-history', methods=['GET'])
@cross_origin()
@employer_login
@error_handler
async def get_user_engagement_history(user: User, user_id: str):
    """Get user's job engagement history"""
    try:
        current_user = user
        if not current_user:
            return jsonify({
                "success": False,
                "message": "Authentication required"
            }), 401

        # TODO: Add authorization check - ensure user can access this user's data
        # (typically only the user themselves or admin)

        # Get query parameters
        days = min(int(request.args.get('days', 30)), 90)  # Max 90 days

        analytics_service = get_service('job_actions_analytics')
        if not analytics_service:
            return jsonify({
                "success": False,
                "message": "Analytics service not available"
            }), 503

        history = await analytics_service.execute('get_user_engagement_history',
            user_id=user_id,
            days=days
        )

        return jsonify({
            "success": True,
            "data": history
        }), 200

    except ValueError as e:
        return jsonify({
            "success": False,
            "message": "Invalid query parameters"
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500

# # Rate limiting for analytics endpoints
# @jobs_analytics_bp.before_request
# def apply_rate_limiting():
#     """Apply rate limiting to analytics endpoints"""
#     if request.endpoint and 'analytics' in request.endpoint:
#         # Apply more lenient rate limiting for analytics (read-only operations)
#         return job_actions_rate_limiter.check_rate_limit(
#             identifier=request.remote_addr,
#             limit=100,  # 100 requests per minute for analytics
#             window=60
#         )

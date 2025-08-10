"""
Company Public Profile Routes

Public-facing routes for company profiles that job seekers can view.
"""

from flask import Blueprint, render_template, request, jsonify, abort
from typing import Optional

from src.routes import flask_error_handler
from src.utils.route_helpers import get_controller
from src.cache.cache_redis import cached
from src.firewall.job_actions_security import secure_job_action, sanitize_input

# Blueprint definition
company_public_bp = Blueprint('company_public', __name__, url_prefix='/company')


@company_public_bp.route('/<company_id>')
@flask_error_handler
@secure_job_action('company_profile', require_auth=False)
async def company_profile(company_id: str):
    """
    Display public company profile page
    
    Args:
        company_id: Company ID
        
    Returns:
        Rendered company profile template
    """
    try:
        # Get company public controller
        company_public_controller = get_controller('company_public')

        # Get company profile
        profile_result = await company_public_controller.get_public_profile(company_id)

        if not profile_result.get('success'):
            if profile_result.get('code') == 404:
                abort(404)
            else:
                abort(500)

        company_data = profile_result['data']

        # Get recent jobs (first 6 for display)
        jobs_result = await company_public_controller.get_company_active_jobs(
            company_id, limit=6, offset=0
        )

        recent_jobs = []
        if jobs_result.get('success'):
            recent_jobs = jobs_result['data']['jobs']

        # Get job categories
        categories_result = await company_public_controller.get_company_job_categories(company_id)
        categories = []
        if categories_result.get('success'):
            categories = categories_result['data']['categories']

        return render_template(
            'company/public/profile.html',
            company=company_data,
            recent_jobs=recent_jobs,
            categories=categories,
            page_title=f"{company_data['name']} - Company Profile"
        )

    except Exception as e:
        abort(500)


@company_public_bp.route('/<company_id>/jobs')
@flask_error_handler
@secure_job_action('company_profile', require_auth=False)
async def company_jobs(company_id: str):
    """
    Display all jobs for a company with pagination and filtering
    
    Args:
        company_id: Company ID
        
    Returns:
        Rendered company jobs template
    """
    try:
        # Get pagination parameters
        page = max(int(request.args.get('page', 1)), 1)
        per_page = min(int(request.args.get('per_page', 20)), 50)
        offset = (page - 1) * per_page

        # Get filter parameters
        query = request.args.get('q', '').strip()
        category_id = request.args.get('category', '').strip()

        # Get company public controller
        company_public_controller = get_controller('company_public')

        # Get company profile (basic info)
        profile_result = await company_public_controller.get_public_profile(company_id)

        if not profile_result.get('success'):
            if profile_result.get('code') == 404:
                abort(404)
            else:
                abort(500)

        company_data = profile_result['data']

        # Search/filter jobs
        if query or category_id:
            jobs_result = await company_public_controller.search_company_jobs(
                company_id, query=query, category_id=category_id,
                limit=per_page, offset=offset
            )
        else:
            jobs_result = await company_public_controller.get_company_active_jobs(
                company_id, limit=per_page, offset=offset
            )

        jobs_data = []
        total_count = 0
        if jobs_result.get('success'):
            jobs_data = jobs_result['data']['jobs']
            total_count = jobs_result['data']['total_count']

        # Calculate pagination
        total_pages = (total_count + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages

        # Get job categories for filter dropdown
        categories_result = await company_public_controller.get_company_job_categories(company_id)
        categories = []
        if categories_result.get('success'):
            categories = categories_result['data']['categories']

        return render_template(
            'company/public/jobs.html',
            company=company_data,
            jobs=jobs_data,
            categories=categories,
            pagination={
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_prev': has_prev,
                'has_next': has_next
            },
            filters={
                'query': query,
                'category_id': category_id
            },
            page_title=f"Jobs at {company_data['name']}"
        )

    except ValueError:
        # Invalid pagination parameters
        abort(400)
    except Exception as e:
        abort(500)


@company_public_bp.route('/api/<company_id>/profile')
@flask_error_handler
async def api_company_profile(company_id: str):
    """
    API endpoint for company profile data
    
    Args:
        company_id: Company ID
        
    Returns:
        JSON response with company profile
    """
    try:
        # Get company public controller
        company_public_controller = get_controller('company_public')

        # Get company profile
        result = await company_public_controller.get_public_profile(company_id)

        status_code = result.get('code', 200)
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "code": 500
        }), 500


@company_public_bp.route('/api/<company_id>/jobs')
@flask_error_handler
async def api_company_jobs(company_id: str):
    """
    API endpoint for company jobs with pagination and filtering
    
    Args:
        company_id: Company ID
        
    Returns:
        JSON response with company jobs
    """
    try:
        # Get pagination parameters
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = max(int(request.args.get('offset', 0)), 0)

        # Get filter parameters
        query = request.args.get('q', '').strip()
        category_id = request.args.get('category', '').strip()

        # Get company public controller
        company_public_controller = get_controller('company_public')

        # Search/filter jobs
        if query or category_id:
            result = await company_public_controller.search_company_jobs(
                company_id, query=query, category_id=category_id,
                limit=limit, offset=offset
            )
        else:
            result = await company_public_controller.get_company_active_jobs(
                company_id, limit=limit, offset=offset
            )

        status_code = result.get('code', 200)
        return jsonify(result), status_code

    except ValueError:
        return jsonify({
            "success": False,
            "message": "Invalid parameters",
            "code": 400
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "code": 500
        }), 500


@company_public_bp.route('/api/<company_id>/statistics')
@flask_error_handler
async def api_company_statistics(company_id: str):
    """
    API endpoint for company statistics
    
    Args:
        company_id: Company ID
        
    Returns:
        JSON response with company statistics
    """
    try:
        # Get company public controller
        company_public_controller = get_controller('company_public')

        # Get statistics
        result = await company_public_controller.get_company_statistics(company_id)

        status_code = result.get('code', 200)
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "code": 500
        }), 500


@company_public_bp.route('/api/<company_id>/categories')
@flask_error_handler
async def api_company_categories(company_id: str):
    """
    API endpoint for company job categories
    
    Args:
        company_id: Company ID
        
    Returns:
        JSON response with job categories
    """
    try:
        # Get company public controller
        company_public_controller = get_controller('company_public')

        # Get categories
        result = await company_public_controller.get_company_job_categories(company_id)

        status_code = result.get('code', 200)
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "code": 500
        }), 500


# Add caching to frequently accessed endpoints
try:
    from src.cache.cache_redis import cached

    # Cache company profile for 30 minutes
    api_company_profile = cached(timeout=1800)(api_company_profile)

    # Cache company statistics for 1 hour
    api_company_statistics = cached(timeout=3600)(api_company_statistics)

    # Cache company categories for 2 hours
    api_company_categories = cached(timeout=7200)(api_company_categories)

except ImportError:
    # Caching not available
    pass

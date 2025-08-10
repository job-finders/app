"""
Job Application Routes with Referral Tracking Support
"""

from flask import Blueprint, request, jsonify
from src.controllers.job_applications import JobApplicationsController
from src.authentication.auth import require_jobseeker_auth

# Create blueprint
job_applications_bp = Blueprint(
    'job_applications',
    __name__,
    url_prefix='/api/applications'
)


@job_applications_bp.route('', methods=['POST'])
@require_jobseeker_auth
def create_application():
    """Create new job application with referral tracking"""
    try:
        data = request.get_json()
        user_id = request.user['uid']

        if not data or not data.get('job_id'):
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400

        # Get referral code if provided
        referral_code = request.args.get('ref') or data.get('referral_code')

        # Create application
        controller = JobApplicationsController()
        result = controller.create_application(
            user_id=user_id,
            job_id=data['job_id'],
            application_data=data,
            referral_code=referral_code
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@job_applications_bp.route('/<application_id>', methods=['PATCH'])
@require_jobseeker_auth
def update_application(application_id):
    """Update application status"""
    try:
        data = request.get_json()
        if not data or not data.get('status'):
            return jsonify({
                'success': False,
                'message': 'Missing status'
            }), 400

        controller = JobApplicationsController()
        result = controller.update_application_status(
            application_id=application_id,
            status=data['status'],
            notes=data.get('notes')
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@job_applications_bp.route('/referral-stats', methods=['GET'])
@require_jobseeker_auth
def get_referral_stats():
    """Get referral statistics for current user"""
    try:
        user_id = request.user['uid']
        controller = JobApplicationsController()
        stats = controller.referral_service.get_referral_stats(user_id)

        return jsonify({
            'success': True,
            'data': stats
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

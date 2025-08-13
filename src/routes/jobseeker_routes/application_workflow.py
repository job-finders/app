"""
Application Workflow Routes

RESTful API endpoints for managing the job application workflow process
including application initiation, questionnaire handling, and submission.
"""

from flask import Blueprint, request, jsonify
from src.authentication import jobseeker_login
from src.database.models import User
from src.utils.route_helpers import get_controller
from src.routes import flask_error_handler

# Create blueprint
application_workflow_bp = Blueprint(
    'application_workflow',
    __name__,
    url_prefix='/api/applications/workflow'
)


@application_workflow_bp.route('/jobs/<string:job_id>/start', methods=['POST'])
@flask_error_handler
@jobseeker_login
async def start_application_process(user: User, job_id: str):
    """
    Start the application process for a job
    
    Args:
        user: Authenticated user from decorator
        job_id: ID of the job to apply for
        
    Returns:
        JSON response with application workflow result
    """
    controller = get_controller('application_workflow')
    
    try:
        result = await controller.start_application_process(
            user_id=user.id,
            job_id=job_id
        )
        
        status_code = 200 if result.success else 400
        return jsonify(result.model_dump()), status_code
        
    except Exception as e:
        controller.logger.exception("Failed to start application process")
        return jsonify({
            "success": False,
            "message": "Failed to start application process",
            "error": str(e)
        }), 500


@application_workflow_bp.route('/jobs/<string:job_id>/questionnaires', methods=['GET'])
@flask_error_handler
@jobseeker_login
async def get_job_questionnaires(user: User, job_id: str):
    """
    Get required questionnaires for a job
    
    Args:
        user: Authenticated user from decorator
        job_id: ID of the job
        
    Returns:
        JSON response with questionnaire definitions
    """
    controller = get_controller('application_workflow')
    
    try:
        result = await controller.get_job_questionnaires(job_id=job_id)
        
        status_code = 200 if result.success else 400
        return jsonify(result.model_dump()), status_code
        
    except Exception as e:
        controller.logger.exception("Failed to get job questionnaires")
        return jsonify({
            "success": False,
            "message": "Failed to get questionnaires",
            "error": str(e)
        }), 500


@application_workflow_bp.route('/applications/<string:application_id>/status', methods=['GET'])
@flask_error_handler
@jobseeker_login
async def get_application_status(user: User, application_id: str):
    """
    Get current status and progress of an application
    
    Args:
        user: Authenticated user from decorator
        application_id: ID of the application
        
    Returns:
        JSON response with application status and progress
    """
    controller = get_controller('application_workflow')
    
    try:
        result = await controller.get_application_status(
            application_id=application_id,
            user_id=user.id
        )
        
        status_code = 200 if result.get("success", False) else 404
        return jsonify(result), status_code
        
    except Exception as e:
        controller.logger.exception("Failed to get application status")
        return jsonify({
            "success": False,
            "message": "Failed to get application status",
            "error": str(e)
        }), 500


@application_workflow_bp.route('/cover-letter/sessions', methods=['POST'])
@flask_error_handler
@jobseeker_login
async def create_cover_letter_session(user: User):
    """
    Create a cover letter generation session
    
    Args:
        user: Authenticated user from decorator
        
    Request Body:
        job_id: ID of the job
        cv_id: ID of the CV to use (optional)
        draft_text: Initial draft text (optional)
        selected_tone: Tone for generation (default: professional)
        
    Returns:
        JSON response with session information
    """
    controller = get_controller('application_workflow')
    
    try:
        data = request.get_json() or {}
        
        # Validate required fields
        job_id = data.get('job_id')
        if not job_id:
            return jsonify({
                "success": False,
                "message": "job_id is required"
            }), 400
        
        result = await controller.create_cover_letter_session(
            user_id=user.id,
            job_id=job_id,
            cv_id=data.get('cv_id'),
            draft_text=data.get('draft_text'),
            selected_tone=data.get('selected_tone', 'professional')
        )
        
        status_code = 200 if result.get("success", False) else 400
        return jsonify(result), status_code
        
    except Exception as e:
        controller.logger.exception("Failed to create cover letter session")
        return jsonify({
            "success": False,
            "message": "Failed to create cover letter session",
            "error": str(e)
        }), 500


@application_workflow_bp.route('/applications/<string:application_id>/cover-letter', methods=['POST'])
@flask_error_handler
@jobseeker_login
async def link_cover_letter_to_application(user: User, application_id: str):
    """
    Link a cover letter session to an application
    
    Args:
        user: Authenticated user from decorator
        application_id: ID of the application
        
    Request Body:
        session_id: ID of the cover letter session
        
    Returns:
        JSON response with linking result
    """
    controller = get_controller('application_workflow')
    
    try:
        data = request.get_json() or {}
        
        # Validate required fields
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({
                "success": False,
                "message": "session_id is required"
            }), 400
        
        result = await controller.link_cover_letter_to_application(
            application_id=application_id,
            session_id=session_id,
            user_id=user.id
        )
        
        status_code = 200 if result.get("success", False) else 400
        return jsonify(result), status_code
        
    except Exception as e:
        controller.logger.exception("Failed to link cover letter to application")
        return jsonify({
            "success": False,
            "message": "Failed to link cover letter",
            "error": str(e)
        }), 500


@application_workflow_bp.route('/cover-letter/sessions/<string:session_id>', methods=['PATCH'])
@flask_error_handler
@jobseeker_login
async def update_cover_letter_session(user: User, session_id: str):
    """
    Update a cover letter session with generated content
    
    Args:
        user: Authenticated user from decorator
        session_id: ID of the cover letter session
        
    Request Body:
        generated_letter: Generated cover letter content
        
    Returns:
        JSON response with update result
    """
    controller = get_controller('application_workflow')
    
    try:
        data = request.get_json() or {}
        
        result = await controller.update_cover_letter_session(
            session_id=session_id,
            user_id=user.id,
            generated_letter=data.get('generated_letter')
        )
        
        status_code = 200 if result.get("success", False) else 400
        return jsonify(result), status_code
        
    except Exception as e:
        controller.logger.exception("Failed to update cover letter session")
        return jsonify({
            "success": False,
            "message": "Failed to update cover letter session",
            "error": str(e)
        }), 500


@application_workflow_bp.route('/applications/<string:application_id>/questionnaires', methods=['GET'])
@flask_error_handler
@jobseeker_login
async def questionnaire_page(user: User, application_id: str):
    """
    Display the questionnaire completion page
    
    Args:
        user: Authenticated user from decorator
        application_id: ID of the application
        
    Returns:
        Rendered questionnaire template
    """
    from flask import render_template
    
    controller = get_controller('application_workflow')
    
    try:
        # Get application details
        application_result = await controller.get_application_status(
            application_id=application_id,
            user_id=user.id
        )
        
        if not application_result.get("success", False):
            return render_template('errors/404.html'), 404
        
        application = application_result.get("application")
        if not application:
            return render_template('errors/404.html'), 404
        
        # Get job details
        job_controller = get_controller('jobs_search')
        job = await job_controller.get_job_by_id(job_id=application.job_id)
        
        if not job:
            return render_template('errors/404.html'), 404
        
        # Get questionnaire details
        questionnaire_result = await controller.get_job_questionnaires(job_id=application.job_id)
        
        if not questionnaire_result.get("success", False) or not questionnaire_result.get("questionnaires"):
            # No questionnaires required, redirect to review
            from flask import redirect, url_for
            return redirect(url_for('application_workflow.review_application', application_id=application_id))
        
        questionnaire = questionnaire_result.get("questionnaires")[0]  # Get first questionnaire
        
        return render_template('applications/questionnaire.html', 
                             application=application,
                             job=job,
                             questionnaire=questionnaire)
        
    except Exception as e:
        controller.logger.exception("Failed to load questionnaire page")
        return render_template('errors/500.html'), 500


@application_workflow_bp.route('/questionnaires/save-progress', methods=['POST'])
@flask_error_handler
@jobseeker_login
async def save_questionnaire_progress(user: User):
    """
    Save questionnaire progress (auto-save)
    
    Args:
        user: Authenticated user from decorator
        
    Returns:
        JSON response with save result
    """
    controller = get_controller('application_workflow')
    
    try:
        data = request.get_json() or {}
        
        result = await controller.save_questionnaire_progress(
            application_id=data.get('application_id'),
            questionnaire_id=data.get('questionnaire_id'),
            user_id=user.id,
            answers=data.get('answers', {}),
            current_question=data.get('current_question', 1),
            time_spent=data.get('time_spent', 0)
        )
        
        status_code = 200 if result.get("success", False) else 400
        return jsonify(result), status_code
        
    except Exception as e:
        controller.logger.exception("Failed to save questionnaire progress")
        return jsonify({
            "success": False,
            "message": "Failed to save progress",
            "error": str(e)
        }), 500


@application_workflow_bp.route('/questionnaires/submit', methods=['POST'])
@flask_error_handler
@jobseeker_login
async def submit_questionnaire(user: User):
    """
    Submit completed questionnaire
    
    Args:
        user: Authenticated user from decorator
        
    Returns:
        JSON response with submission result
    """
    controller = get_controller('application_workflow')
    
    try:
        data = request.get_json() or {}
        
        result = await controller.submit_questionnaire(
            application_id=data.get('application_id'),
            questionnaire_id=data.get('questionnaire_id'),
            user_id=user.id,
            answers=data.get('answers', {}),
            time_spent_seconds=data.get('time_spent_seconds', 0),
            is_auto_submit=data.get('is_auto_submit', False)
        )
        
        status_code = 200 if result.get("success", False) else 400
        return jsonify(result), status_code
        
    except Exception as e:
        controller.logger.exception("Failed to submit questionnaire")
        return jsonify({
            "success": False,
            "message": "Failed to submit questionnaire",
            "error": str(e)
        }), 500


@application_workflow_bp.route('/applications/<string:application_id>/questionnaires/timer/start', methods=['POST'])
@flask_error_handler
@jobseeker_login
async def start_questionnaire_timer(user: User, application_id: str):
    """
    Start the questionnaire timer for an application
    
    Args:
        user: Authenticated user from decorator
        application_id: ID of the application
        
    Returns:
        JSON response with timer information
    """
    controller = get_controller('application_workflow')
    
    try:
        result = await controller.start_questionnaire_timer(
            application_id=application_id,
            user_id=user.id
        )
        
        status_code = 200 if result.get("success", False) else 400
        return jsonify(result), status_code
        
    except Exception as e:
        controller.logger.exception("Failed to start questionnaire timer")
        return jsonify({
            "success": False,
            "message": "Failed to start questionnaire timer",
            "error": str(e)
        }), 500

@applic
ation_workflow_bp.route('/applications/<string:application_id>/questionnaires', methods=['POST'])
@flask_error_handler
@jobseeker_login
async def submit_questionnaire_answers(user: User, application_id: str):
    """
    Submit questionnaire answers for an application
    
    Args:
        user: Authenticated user from decorator
        application_id: ID of the application
        
    Request Body:
        answers: Dictionary of question_id -> answer_list mappings
        time_spent_seconds: Time spent on questionnaires (optional)
        
    Returns:
        JSON response with submission result
    """
    controller = get_controller('application_workflow')
    
    try:
        data = request.get_json() or {}
        
        # Validate required fields
        answers = data.get('answers')
        if not answers or not isinstance(answers, dict):
            return jsonify({
                "success": False,
                "message": "answers dictionary is required"
            }), 400
        
        result = await controller.submit_questionnaire_answers(
            application_id=application_id,
            answers=answers,
            user_id=user.id,
            time_spent_seconds=data.get('time_spent_seconds')
        )
        
        status_code = 200 if result.success else 400
        return jsonify(result.model_dump()), status_code
        
    except Exception as e:
        controller.logger.exception("Failed to submit questionnaire answers")
        return jsonify({
            "success": False,
            "message": "Failed to submit questionnaire answers",
            "error": str(e)
        }), 500


@application_workflow_bp.route('/applications/<string:application_id>/submit', methods=['POST'])
@flask_error_handler
@jobseeker_login
async def submit_application(user: User, application_id: str):
    """
    Submit final application after all workflow steps are complete
    
    Args:
        user: Authenticated user from decorator
        application_id: ID of the application
        
    Returns:
        JSON response with submission result
    """
    controller = get_controller('application_workflow')
    
    try:
        result = await controller.submit_application(
            application_id=application_id,
            user_id=user.id
        )
        
        status_code = 200 if result.success else 400
        return jsonify(result.model_dump()), status_code
        
    except Exception as e:
        controller.logger.exception("Failed to submit application")
        return jsonify({
            "success": False,
            "message": "Failed to submit application",
            "error": str(e)
        }), 500


@application_workflow_bp.route('/applications/<string:application_id>/validate', methods=['POST'])
@flask_error_handler
@jobseeker_login
async def validate_application(user: User, application_id: str):
    """
    Validate application before final submission
    
    Args:
        user: Authenticated user from decorator
        application_id: ID of the application
        
    Returns:
        JSON response with validation result
    """
    controller = get_controller('application_workflow')
    
    try:
        # Get application status which includes validation information
        result = await controller.get_application_status(
            application_id=application_id,
            user_id=user.id
        )
        
        if not result.get("success", False):
            return jsonify(result), 404
        
        # Extract validation information
        validation_result = {
            "success": True,
            "application_id": application_id,
            "is_valid": result.get("validation_score", 0) >= 70,  # 70% threshold
            "validation_score": result.get("validation_score", 0),
            "completion_percentage": result.get("completion_percentage", 0),
            "workflow_step": result.get("workflow_step"),
            "next_step": result.get("next_step"),
            "missing_requirements": [],
            "validation_details": {
                "has_cover_letter": result.get("has_cover_letter", False),
                "has_ats_report": result.get("has_ats_report", False),
                "questionnaires_completed": result.get("questionnaires_completed", False),
                "workflow_complete": result.get("is_complete", False)
            }
        }
        
        # Add missing requirements based on status
        if not result.get("has_cover_letter", False):
            validation_result["missing_requirements"].append("Cover letter is required")
        
        if not result.get("questionnaires_completed", False) and result.get("workflow_step") in ["questionnaires", "draft"]:
            validation_result["missing_requirements"].append("Questionnaires must be completed")
        
        if result.get("workflow_step") not in ["review", "submitted"]:
            validation_result["missing_requirements"].append("Application workflow must be completed")
        
        return jsonify(validation_result), 200
        
    except Exception as e:
        controller.logger.exception("Failed to validate application")
        return jsonify({
            "success": False,
            "message": "Failed to validate application",
            "error": str(e)
        }), 500


@application_workflow_bp.route('/applications/<string:application_id>/progress', methods=['GET'])
@flask_error_handler
@jobseeker_login
async def get_application_progress(user: User, application_id: str):
    """
    Get detailed application progress information
    
    Args:
        user: Authenticated user from decorator
        application_id: ID of the application
        
    Returns:
        JSON response with detailed progress information
    """
    controller = get_controller('application_workflow')
    
    try:
        # Get application status
        status_result = await controller.get_application_status(
            application_id=application_id,
            user_id=user.id
        )
        
        if not status_result.get("success", False):
            return jsonify(status_result), 404
        
        # Build detailed progress response
        progress_result = {
            "success": True,
            "application_id": application_id,
            "current_step": status_result.get("workflow_step"),
            "current_step_display": status_result.get("workflow_step_display"),
            "completion_percentage": status_result.get("completion_percentage", 0),
            "next_step": status_result.get("next_step"),
            "is_complete": status_result.get("is_complete", False),
            "steps": [
                {
                    "step": "draft",
                    "display_name": "Application Started",
                    "completed": True,
                    "current": status_result.get("workflow_step") == "draft"
                },
                {
                    "step": "cover_letter",
                    "display_name": "Cover Letter Generated",
                    "completed": status_result.get("has_cover_letter", False),
                    "current": status_result.get("workflow_step") == "cover_letter"
                },
                {
                    "step": "questionnaires",
                    "display_name": "Questionnaires Completed",
                    "completed": status_result.get("questionnaires_completed", False),
                    "current": status_result.get("workflow_step") == "questionnaires"
                },
                {
                    "step": "review",
                    "display_name": "Ready for Review",
                    "completed": status_result.get("workflow_step") in ["review", "submitted"],
                    "current": status_result.get("workflow_step") == "review"
                },
                {
                    "step": "submitted",
                    "display_name": "Application Submitted",
                    "completed": status_result.get("workflow_step") == "submitted",
                    "current": status_result.get("workflow_step") == "submitted"
                }
            ],
            "validation_score": status_result.get("validation_score"),
            "applied_date": status_result.get("applied_date"),
            "workflow_duration_minutes": status_result.get("workflow_duration_minutes")
        }
        
        return jsonify(progress_result), 200
        
    except Exception as e:
        controller.logger.exception("Failed to get application progress")
        return jsonify({
            "success": False,
            "message": "Failed to get application progress",
            "error": str(e)
        }), 500
# routes/employee_agents.py
from flask import Blueprint, request, jsonify

from src.routes import flask_error_handler
from src.authentication import login_required, jobseeker_login
from src.database.models import User
from src.utils.route_helpers import get_controller

employee_agents_route = Blueprint('employee_agents', __name__, url_prefix='/agents/employee/v1')


@employee_agents_route.route("/jobs/<string:job_id>/match-analysis", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def analyze_job_match(user: User, job_id: str):
    """
        job_seekers will call this endpoint to check if they qualify to apply for the position
    :param user:
    :param job_id:
    :return:
    """
    employee_agents_controller = get_controller('employee_agents')
    try:
        # Get optional cover letter from request body
        data = request.get_json()
        cover_letter = data.get("cover_letter") if data else None
        cv_id = data.get('cv_id') if data else None
        # Call controller

        result = await employee_agents_controller.analyze_job_match(
            user_id=user.uid,
            job_id=job_id,
            cv_id=cv_id,
            cover_letter=cover_letter
        )
        # this works wonderfully the result of this call will be displayed inline with the job advert
        return (jsonify(result.model_dump()), 200) if result is not None else (None, 204)

    except ValueError as e:
        employee_agents_controller.logger.warning(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        employee_agents_controller.logger.exception("Job match analysis failed")
        return jsonify({"error": "Job match analysis failed", "details": str(e)}), 500


@employee_agents_route.route("/jobs/<string:job_id>/candidate-fit-analysis", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def analyze_candidate_fit(user: User, job_id: str):
    """
    Analyze how well a candidate's CV fits a specific job using AI-powered candidate benchmarking
    :param user: Authenticated job seeker user
    :param job_id: ID of the job to analyze fit against
    :return: CandidateBenchmarkReport with detailed fit analysis
    """
    import logging
    import time
    from flask import request
    from src.monitoring.candidate_analysis_metrics import candidate_analysis_monitor, log_analysis_event

    # Initialize logging and monitoring
    logger = logging.getLogger('candidate_fit_analysis')
    start_time = time.time()
    request_id = None

    # Log request initiation
    logger.info(f"Candidate fit analysis started - User: {user.uid}, Job: {job_id}")
    log_analysis_event('request_started', user_id=user.uid, job_id=job_id)

    candidate_benchmark_controller = get_controller('candidate_benchmarking')
    try:
        # Get CV ID from request body
        data = request.get_json()
        cv_id = data.get('cv_id') if data else None

        # Log request details and start monitoring
        logger.info(f"Analysis request details - CV: {cv_id}, User: {user.uid}, Job: {job_id}")

        if not cv_id:
            logger.warning(f"Missing CV ID in request - User: {user.uid}, Job: {job_id}")
            log_analysis_event('validation_error', user_id=user.uid, job_id=job_id, error='missing_cv_id')
            return jsonify({"error": "CV ID is required for candidate fit analysis"}), 400

        # Start monitoring this request
        request_id = candidate_analysis_monitor.record_request_start(user.uid, job_id, cv_id)

        # Call candidate benchmark controller for employee perspective
        logger.info(f"Calling benchmark controller - User: {user.uid}, Job: {job_id}, CV: {cv_id}")
        result = await candidate_benchmark_controller.benchmark_for_employee(
            user_id=user.uid,
            job_id=job_id,
            cv_id=cv_id
        )

        if result is None:
            logger.error(f"Benchmark controller returned None - User: {user.uid}, Job: {job_id}, CV: {cv_id}")
            return jsonify({"error": "Candidate fit analysis failed", "details": "Unable to generate analysis"}), 500

        # Log successful completion and record metrics
        duration = time.time() - start_time
        percentile = getattr(result, 'percentile_rank', 0)

        logger.info(f"Analysis completed successfully - User: {user.uid}, Job: {job_id}, CV: {cv_id}, "
                    f"Duration: {duration:.2f}s, Percentile: {percentile}")

        # Record success in monitoring
        if request_id:
            candidate_analysis_monitor.record_request_success(request_id, duration, percentile)

        # Log performance metrics
        if duration > 30:
            logger.warning(f"Slow analysis detected - Duration: {duration:.2f}s, User: {user.uid}")

        # Log analysis event
        log_analysis_event('analysis_completed',
                           user_id=user.uid, job_id=job_id, cv_id=cv_id,
                           duration=duration, percentile_rank=percentile)

        return jsonify(result.model_dump()), 200

    except ValueError as e:
        duration = time.time() - start_time
        logger.warning(
            f"Validation error - User: {user.uid}, Job: {job_id}, Error: {str(e)}, Duration: {duration:.2f}s")

        # Record failure in monitoring
        if request_id:
            candidate_analysis_monitor.record_request_failure(request_id, duration, 'ValidationError', str(e))

        log_analysis_event('validation_error',
                           user_id=user.uid, job_id=job_id,
                           error=str(e), duration=duration)

        return jsonify({"error": f"Validation error: {str(e)}"}), 400
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Analysis failed with exception - User: {user.uid}, Job: {job_id}, "
                     f"Error: {str(e)}, Duration: {duration:.2f}s", exc_info=True)

        # Record failure in monitoring
        if request_id:
            candidate_analysis_monitor.record_request_failure(request_id, duration, type(e).__name__, str(e))

        log_analysis_event('analysis_failed',
                           user_id=user.uid, job_id=job_id,
                           error_type=type(e).__name__, error=str(e), duration=duration)

        return jsonify({"error": "Candidate fit analysis failed", "details": str(e)}), 500


@employee_agents_route.route("/jobs/<string:job_id>/cover-letter", methods=["POST"])
@flask_error_handler
@jobseeker_login
async def generate_cover_letter(user: User, job_id: str):

    employee_agents_controller = get_controller('employee_agents')
    try:
        # Get optional tone from request body
        data = request.get_json()
        tone = data.get("tone", "professional") if data else "professional"
        cv_id: str = data.get("cv_id") if data else None

        # Validate tone input
        valid_tones = ["professional", "enthusiastic", "confident", "friendly", "creative", "analytical", "formal", "concise"]
        if tone.lower() not in valid_tones:
            return jsonify({
                "error": f"Invalid tone. Valid options: {', '.join(valid_tones)}"
            }), 400

        # Call controller
        result = await employee_agents_controller.generate_cover_letter(
            user_id=user.uid,
            job_id=job_id,
            cv_id=cv_id,
            tone=tone
        )
        return (jsonify(result.model_dump()), 200) if result is not None else (None, 204)

    except ValueError as e:
        employee_agents_controller.logger.warning(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        employee_agents_controller.logger.exception("Cover letter generation failed")
        return jsonify({"error": "Cover letter generation failed", "details": str(e)}), 500
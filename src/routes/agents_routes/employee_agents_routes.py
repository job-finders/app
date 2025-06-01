# routes/employee_agents.py
from flask import Blueprint, request, jsonify
from src.authentication import login_required
from src.database.models.users import User
from src.main import employee_agents_controller

employee_agents_route = Blueprint('employee_agents', __name__, url_prefix='/agents/employee/v1')


@employee_agents_route.route("/jobs/<string:job_id>/match-analysis", methods=["POST"])
@login_required
async def analyze_job_match(user: User, job_id: str):
    """
        job_seekers will call this endpoint to check if they qualify to apply for the position
    :param user:
    :param job_id:
    :return:
    """
    try:
        # Get optional cover letter from request body
        data = request.get_json()
        cover_letter = data.get("cover_letter") if data else None
        cv_id = data.get('cv_id') if data else None
        # Call controller
        result = await employee_agents_controller.analyze_job_match(
            user_id=user.id,
            job_id=job_id,
            cv_id=cv_id,
            cover_letter=cover_letter
        )
        # this works wonderfully the result of this call will be displayed inline with the job advert
        return jsonify(result.model_dump()), 200

    except ValueError as e:
        employee_agents_controller.logger.warning(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        employee_agents_controller.logger.exception("Job match analysis failed")
        return jsonify({"error": "Job match analysis failed", "details": str(e)}), 500


@employee_agents_route.route("/jobs/<string:job_id>/cover-letter", methods=["POST"])
@login_required
async def generate_cover_letter(user: User, job_id: str):
    try:
        # Get optional tone from request body
        data = request.get_json()
        tone = data.get("tone", "professional") if data else "professional"
        cv_id: str = data.get("cv_id") if data else None

        # Validate tone input
        valid_tones = ["professional", "enthusiastic", "friendly", "formal", "concise"]
        if tone.lower() not in valid_tones:
            return jsonify({
                "error": f"Invalid tone. Valid options: {', '.join(valid_tones)}"
            }), 400

        # Call controller
        result = await employee_agents_controller.generate_cover_letter(
            user_id=user.id,
            job_id=job_id,
            cv_id=cv_id,
            tone=tone
        )
        return jsonify(result.model_dump()), 200

    except ValueError as e:
        employee_agents_controller.logger.warning(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        employee_agents_controller.logger.exception("Cover letter generation failed")
        return jsonify({"error": "Cover letter generation failed", "details": str(e)}), 500
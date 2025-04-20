
import functools
from flask import jsonify, request, flash, redirect, url_for
from werkzeug.exceptions import BadRequest, NotFound, Unauthorized, InternalServerError
from src.logger import init_logger


error_logger = init_logger('flask_error_handler')

class UnauthorizedError(Exception):
    """Raised when a user is not authorized to access a resource."""
    def __init__(self, message="You are not authorized to access this resource"):
        self.message = message
        super().__init__(self.message)


def flask_error_handler(view_func):
    @functools.wraps(view_func)
    def wrapped_method(*args, **kwargs):
        try:
            return view_func(*args, **kwargs)
        except BadRequest as e:
            error_message = f"Bad Request: {str(e)}"
            error_logger.error(error_message)
            return jsonify({"error": "Bad Request", "message": str(e)}), 400
        except NotFound as e:
            error_message = f"Not Found: {str(e)}"
            error_logger.error(error_message)
            return jsonify({"error": "Not Found", "message": str(e)}), 404
        except Unauthorized as e:
            error_message = f"Unauthorized: {str(e)}"
            error_logger.error(error_message)
            return jsonify({"error": "Unauthorized", "message": str(e)}), 401
        except UnauthorizedError as e:
            error_message = f"UnauthorizedError: {str(e)}"
            error_logger.error(error_message)
            return jsonify({"error": "Unauthorized", "message": str(e)}), 403
        except InternalServerError as e:
            error_message = f"Internal Server Error: {str(e)}"
            error_logger.error(error_message)
            return jsonify({"error": "Internal Server Error", "message": str(e)}), 500
        except Exception as e:
            error_message = f"Unexpected Error: {str(e)}"
            error_logger.error(error_message)
            return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}), 500

    return wrapped_method



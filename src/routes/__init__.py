
import functools
import inspect

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
    async def async_wrapper(*args, **kwargs):
        method_name = view_func.__name__
        try:
            return await view_func(*args, **kwargs)
        except BadRequest as e:
            error_logger.error(f"[{method_name}] Bad Request: {e}")
            return jsonify({"error": "Bad Request", "message": str(e)}), 400
        except NotFound as e:
            error_logger.error(f"[{method_name}] Not Found: {e}")
            return jsonify({"error": "Not Found", "message": str(e)}), 404
        except Unauthorized as e:
            error_logger.error(f"[{method_name}] Unauthorized: {e}")
            return jsonify({"error": "Unauthorized", "message": str(e)}), 401
        except UnauthorizedError as e:
            error_logger.error(f"[{method_name}] UnauthorizedError: {e}")
            return jsonify({"error": "Unauthorized", "message": str(e)}), 403
        except InternalServerError as e:
            error_logger.error(f"[{method_name}] Internal Server Error: {e}")
            return jsonify({"error": "Internal Server Error", "message": str(e)}), 500
        except Exception as e:
            error_logger.exception(f"[{method_name}] Unexpected Error: {e}")
            return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}), 500
    return async_wrapper


    @functools.wraps(view_func)
    def sync_wrapper(*args, **kwargs):
        try:
            return view_func(*args, **kwargs)
        except BadRequest as e:
            error_logger.error(f"Bad Request: {e}")
            return jsonify({"error": "Bad Request", "message": str(e)}), 400
        except NotFound as e:
            error_logger.error(f"Not Found: {e}")
            return jsonify({"error": "Not Found", "message": str(e)}), 404
        except Unauthorized as e:
            error_logger.error(f"Unauthorized: {e}")
            return jsonify({"error": "Unauthorized", "message": str(e)}), 401
        except UnauthorizedError as e:
            error_logger.error(f"UnauthorizedError: {e}")
            return jsonify({"error": "Unauthorized", "message": str(e)}), 403
        except InternalServerError as e:
            error_logger.error(f"Internal Server Error: {e}")
            return jsonify({"error": "Internal Server Error", "message": str(e)}), 500
        except Exception as e:
            error_logger.error(f"Unexpected Error: {e}")
            return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}), 500

    return async_wrapper if inspect.iscoroutinefunction(view_func) else sync_wrapper

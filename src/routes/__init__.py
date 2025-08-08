
import functools
import inspect
from flask import jsonify, request, flash, redirect, url_for
from pydantic import ValidationError
from pymysql import DatabaseError
from werkzeug.exceptions import BadRequest, NotFound, Unauthorized, InternalServerError
from src.logger import init_logger


error_logger = init_logger('flask_error_handler')

class UnauthorizedError(Exception):
    """Raised when a user is not authorized to access a resource."""
    def __init__(self, message="You are not authorized to access this resource"):
        self.message = message
        super().__init__(self.message)

def flask_error_handler(view_func):
    error_map = {
        BadRequest: ("Bad Request", 400),
        NotFound: ("Not Found", 404),
        Unauthorized: ("Unauthorized", 401),
        UnauthorizedError: ("Unauthorized", 403),
        InternalServerError: ("Internal Server Error", 500),
        ValidationError: ("Validation Error", 400),
        DatabaseError: ("Database Error", 503),
        TimeoutError: ("Service Timeout", 504),
        FileNotFoundError: ("File Not Found", 404)}

    def handle_exception(e, method_name=None):
        error_type = type(e)
        error_name, status = error_map.get(error_type, ("Internal Server Error", 500))
        log_func = error_logger.error if status != 500 else error_logger.exception
        prefix = f"[{method_name}] " if method_name else ""
        log_func(f"{prefix}{error_name}: {e}")

        # Enhanced user messaging
        if status == 400:
            message = f"Validation error: {str(e)}"
        elif status == 404:
            message = "The requested resource was not found"
        elif status == 403:
            message = "You don't have permission to access this resource"
        elif status in (503, 504):
            message = "Service temporarily unavailable. Please try again later."
        else:
            message = "An unexpected error occurred"

        # Return appropriate response based on request type
        if request.accept_mimetypes.accept_json:
            return jsonify({
                "error": error_name,
                "message": message,
                "code": status,
                "details": str(e) if status != 500 else None
            }), status
        else:
            flash(message, "danger" if status >= 400 else "warning")
            return redirect(url_for("home.get_home"))

    @functools.wraps(view_func)
    async def async_wrapper(*args, **kwargs):
        method_name = view_func.__name__
        try:
            return await view_func(*args, **kwargs)
        except Exception as e:
            return handle_exception(e, method_name)

    @functools.wraps(view_func)
    def sync_wrapper(*args, **kwargs):
        try:
            return view_func(*args, **kwargs)
        except Exception as e:
            return handle_exception(e)

    return async_wrapper if inspect.iscoroutinefunction(view_func) else sync_wrapper
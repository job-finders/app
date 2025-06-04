
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
    error_map = {
        BadRequest: ("Bad Request", 400),
        NotFound: ("Not Found", 404),
        Unauthorized: ("Unauthorized", 401),
        UnauthorizedError: ("Unauthorized", 403),
        InternalServerError: ("Internal Server Error", 500),
    }

    def handle_exception(e, method_name=None):
        error_type = type(e)
        error_name, status = error_map.get(error_type, ("Internal Server Error", 500))
        log_func = error_logger.error if status != 500 else error_logger.exception
        prefix = f"[{method_name}] " if method_name else ""
        log_func(f"{prefix}{error_name}: {e}")
        message = str(e) if status != 500 else "An unexpected error occurred"
        return jsonify({"error": error_name, "message": message}), status

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
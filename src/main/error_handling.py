# src/error_handling.py
from flask import jsonify,Flask, flash, render_template
from werkzeug.exceptions import HTTPException


# noinspection PyMethodMayBeStatic
def register_error_handlers(app: Flask):
    @app.errorhandler(404)
    def page_not_found(error):
        app.logger.error("Resource Not Found")
        flash(message="Resource Not Found", category="danger")
        return render_template('error.html'), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error("Internal Server Error Please try again later")
        flash(message="Internal Server Error Please try again later", category="danger")
        return render_template('error.html'), 500

    @app.errorhandler(401)
    def unauthorized(error):
        app.logger.error("Unauthorized Request")
        flash(message="Unauthorized Request", category="danger")
        return render_template('error.html'), 401

    @app.errorhandler(404)
    def not_found(error):
        flash(message="Resource not found", category="danger")
        app.logger.error("Resource not found")
        return render_template('error.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal error: {error}")
        flash(message="Internal server error", category="danger")
        return render_template('error.html'), 500

    # Handle all other exceptions
    @app.errorhandler(Exception)
    def handle_exception(error):
        if isinstance(error, HTTPException):
            return error
        app.logger.exception("Unhandled exception")
        flash(message="Unhandled exception", category="danger")
        return render_template('error.html'), 500

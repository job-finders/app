import functools
from sqlalchemy.exc import SQLAlchemyError
from flask import redirect, url_for, flash, Flask, render_template
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError
from contextlib import contextmanager
from src.database.sql import Session
from src.logger import init_logger

error_logger = init_logger("error_logger")


class Controllers:
    """
        **Controllers**
            registers controllers
    """
    session_limit: int = 25

    def __init__(self, session_maker=Session):
        self.session_maker = session_maker
        self.sessions = [session_maker() for _ in range(self.session_limit)]
        self.logger = init_logger(self.__class__.__name__)

    def init_app(self, app: Flask):
        """
            **init_app**
        :param app:
        :return:
        """
        self.setup_error_handler(app=app)

        session_maker = app.config.get('session_maker')
        session_limit = app.config.get('session_limit')

        if session_maker and session_limit:
            self.sessions = [session_maker() for _ in range(session_limit)]

    @contextmanager
    def get_session(self):
        """
        Generator-based context manager for managing sessions.
        Ensures that sessions are properly released after use.
        """
        session = None
        try:
            if not self.sessions:
                self.sessions = [self.session_maker() for _ in range(self.session_limit)]

            session = self.sessions.pop()
            self.logger.debug(f"Session acquired: {session}")
            yield session

            if session.dirty or session.new or session.deleted:
                session.commit()
                self.logger.debug("Session changes committed")

        except SQLAlchemyError as e:
            self.logger.error(f"Error while using session: {e}")
            if session:
                session.rollback()  # Rollback any uncommitted changes on error
            raise
        finally:
            if session:
                session.close()
                self.logger.debug(f"Session released: {session}")
            else:
                self.sessions.append(self.session_maker())
                self.logger.debug("Session pool replenished")

    def __del__(self):
        for session in self.sessions:
            session.close()
            self.logger.debug(f"Session closed on delete: {session}")

    # noinspection PyMethodMayBeStatic
    def setup_error_handler(self, app: Flask):
        @app.errorhandler(404)
        def page_not_found(error):
            self.logger.error(str(error))
            flash(message="we where unable to find the resource you where looking for", category="danger")
            return render_template('index.html'), 404

        @app.errorhandler(500)
        def internal_server_error(error):
            self.logger.error(str(error))
            flash(message="Internal Server Error Please try again later", category="danger")
            return render_template('index.html'), 500


class UnauthorizedError(Exception):
    def __init__(self, description: str = "You are not Authorized to access that resource", code: int = 401):
        self.description = description
        self.code = code
        super().__init__(self.description)
        error_logger.error(self.description)


def error_handler(view_func):
    @functools.wraps(view_func)
    async def wrapped_method(*args, **kwargs):
        try:
            return await view_func(*args, **kwargs)

        # Database-related errors (Operational, Integrity, Programming errors)
        except (OperationalError, ProgrammingError, IntegrityError) as e:
            message = f"{view_func.__name__} : Database error: {str(e)}"
            error_logger.error(message)
            flash("Error accessing database - please try again.", category='danger')
            return None

        # Unauthorized access errors
        except UnauthorizedError as e:
            message = f"{view_func.__name__} : Unauthorized access: {str(e)}"
            error_logger.error(message)
            flash("You are not authorized to access this resource.", category='danger')
            return redirect(url_for('home.get_home'), code=302)

        # Connection issues (e.g., reset connection)
        except ConnectionResetError as e:
            message = f"{view_func.__name__} : Connection reset: {str(e)}"
            error_logger.error(message)
            flash("Unable to connect to the database, please try again.", category='danger')
            return None

        # Validation errors from Pydantic (input validation)
        except ValidationError as e:
            message = f"{view_func.__name__} : Validation error: {str(e)}"
            error_logger.error(message)
            flash("There was an issue with the provided data. Please check your input.", category='danger')
            return None

        # General unexpected errors
        except Exception as e:
            message = f"{view_func.__name__} : Unexpected error: {str(e)}"
            error_logger.error(message)
            flash("Oops! Something went wrong. Please try again later.", category='danger')
            return None

    return wrapped_method

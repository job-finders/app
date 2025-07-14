import functools
from contextlib import contextmanager

from flask import redirect, url_for, Flask
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError
from sqlalchemy.exc import SQLAlchemyError

from src.database import UserORM
from src.database.models.users import RolesEnum, User
from src.database.sql import Session
from src.logger import init_logger
from src.config import config_instance
error_logger = init_logger("error_logger")

class ControllerInitException(Exception):
    """Exception raised when a controller fails to initialize properly."""

    def __init__(self, controller_name: str, controller_class: type, message: str = "", original_exception: Exception = None):
        self.controller_name = controller_name
        self.controller_class = controller_class
        self.original_exception = original_exception

        class_name = controller_class.__name__ if controller_class else "UnknownClass"
        full_message = (
            f"Initialization failed for controller '{controller_name}' "
            f"(class: {class_name})."
        )
        if message:
            full_message += f" {message}"
        if original_exception:
            full_message += f" Original error: {str(original_exception)}"

        super().__init__(full_message)


class Controllers:
    """
        **Controllers**
            registers controllers
    """
    session_limit: int = 5

    def __init__(self, factory, session_maker=Session):
        self.factory = factory
        self.session_maker = session_maker
        self.sessions = []
        self.logger = init_logger(self.__class__.__name__)
        self.app: Flask | None = None
        self.config = config_instance()
        self.deepseek_api_key: str | None  = None
        # Initialize sessions if session_maker is provided
        if session_maker:
            self._initialize_sessions()

    def _initialize_sessions(self):
        """Initialize session pool"""
        self.sessions = [self.session_maker() for _ in range(self.session_limit)]
        self.logger.info(f"Initialized {self.session_limit} database sessions")

    def init_app(self, app: Flask):
        """
        Initialize with Flask application
        """
        self.app = app

        # Update configuration from app
        session_maker = self.app.config.get('session_maker')
        session_limit = self.app.config.get('session_limit', self.session_limit)
        self.deepseek_api_key = self.app.config.get('DEEPSEEK_API_KEY')

    async def get_system_admin(self) -> User:
        """
        Retrieve the system admin user.
        This method checks if a system admin user exists and returns it.
        If no admin user exists, it will return an empty result.
        """
        with self.get_session() as session:
            admin_user_orm = session.query(UserORM).filter_by(role=RolesEnum.SYSTEM_ADMIN.value).first()
            self.logger.info(f"Retrieved system admin user: {admin_user_orm}")
            if not admin_user_orm:
                self.logger.info("No system admin found, creating a new one.")
                return await self.create_system_admin()

            data = User(**admin_user_orm.to_dict()) if isinstance(admin_user_orm, UserORM) else None
            self.logger.info(f"System admin user data: {data}")
            return data

    async def create_system_admin(self) -> User:
        """
        Create a system admin user if it does not exist.
        This is a one-time setup method to ensure the system has an admin user.
        """
        with self.get_session() as session:
            existing_admin = session.query(UserORM).filter_by(role=RolesEnum.SYSTEM_ADMIN.value).first()
            if existing_admin:
                return User(**existing_admin.to_dict())

            # Create new admin user
            admin_email = self.config.ADMIN_USERNAME
            admin_password = self.config.ADMIN_PASSWORD
            self.logger.info(f"Creating new system admin user. {admin_email} ")

            user = User.create(name="System Admin", email=admin_email, password=admin_password,
                               role=RolesEnum.SYSTEM_ADMIN.value, )

            new_admin_orm = UserORM(uid=user.uid,
                                    name=user.name,
                                    email=user.email,
                                    password_hash=user.password_hash,
                                    role=RolesEnum.SYSTEM_ADMIN.value,
                                    is_active=True)
            session.add(new_admin_orm)
            return user


    def close(self):
        """Release all resources including database sessions"""
        self.logger.info(f"Closing {len(self.sessions)} database sessions")
        for session in self.sessions:
            try:
                session.close()
            except Exception as e:
                self.logger.error(f"Error closing session: {e}")
        self.sessions = []
        self.logger.debug("All sessions closed")

    @contextmanager
    def get_session(self):
        """
        Context manager for session management
        """
        session = None
        try:
            if not self.sessions:
                self.logger.warning("Session pool empty, creating new session")
                session = self.session_maker()
            else:
                session = self.sessions.pop()

            self.logger.debug(f"Session acquired: {id(session)}")
            yield session

            # Commit if there are changes
            if session.dirty or session.new or session.deleted:
                session.commit()
                self.logger.debug("Session changes committed")

        except SQLAlchemyError as e:
            self.logger.error(f"Database error: {e}")
            if session:
                session.rollback()
            raise
        finally:
            if session:
                try:
                    session.close()
                    self.logger.debug(f"Session closed: {id(session)}")

                    # Only return to pool if it's not a temporary session
                    if len(self.sessions) < self.session_limit:
                        self.sessions.append(self.session_maker())
                        self.logger.debug("Session returned to pool")
                except Exception as e:
                    self.logger.error(f"Error releasing session: {e}")

    def __del__(self):
        """Destructor to ensure resource cleanup"""
        self.close()



class UnauthorizedError(Exception):
    def __init__(self, description: str = "You are not Authorized to access that resource", code: int = 401):
        self.description = description
        self.code = code
        super().__init__(self.description)
        error_logger.error(self.description)

class ATSProcessingError(Exception):
    def __init__(self, message="There was an error processing the resume."):
        super().__init__(message)
        error_logger.error(f"ATSProcessingError: {message}")


def error_handler(view_func):
    @functools.wraps(view_func)
    async def wrapped_method(*args, **kwargs):
        try:
            return await view_func(*args, **kwargs)

        # Database-related errors (Operational, Integrity, Programming errors)
        except (OperationalError, ProgrammingError, IntegrityError) as e:
            message = f"{view_func.__name__} : Database error: {str(e)}"
            error_logger.error(message)
            # flash("Error accessing database - please try again.", category='danger')
            return None

        # Unauthorized access errors
        except UnauthorizedError as e:
            message = f"{view_func.__name__} : Unauthorized access: {str(e)}"
            error_logger.error(message)
            # flash("You are not authorized to access this resource.", category='danger')
            return redirect(url_for('home.get_home'), code=302)

        # Connection issues (e.g., reset connection)
        except ConnectionResetError as e:
            message = f"{view_func.__name__} : Connection reset: {str(e)}"
            error_logger.error(message)
            # flash("Unable to connect to the database, please try again.", category='danger')
            return None

        # Validation errors from Pydantic (input validation)
        except ValidationError as e:
            message = f"{view_func.__name__} : Validation error: {str(e)}"
            error_logger.error(message)
            # flash("There was an issue with the provided data. Please check your input.", category='danger')
            return None

        # General unexpected errors
        except Exception as e:
            message = f"{view_func.__name__} : Unexpected error: {str(e)}"
            error_logger.error(message)
            # flash("Oops! Something went wrong. Please try again later.", category='danger')
            return None

    return wrapped_method

# Controller Base Class Documentation

## Overview
The `Controllers` class serves as the base class for all controllers in the application. It provides common functionality such as session management, logging, and error handling.

## Purpose
-   To provide a consistent base class for all controllers.
-   To centralize session management, logging, and error handling.
-   To facilitate dependency injection and configuration.

## Dependencies

-   SQLAlchemy: For database interactions.
-   Flask: For application context.
-   Pydantic: For data validation.
-   `init_logger`: Function for initializing a logger instance.
-   `config_instance`: Provides access to configuration settings.

## Methods

### `__init__(self, factory, session_maker=Session)`

-   **Description:** Initializes the controller with a session factory, logger, and optional session maker.
    -   Calls the superclass constructor (`Controllers.__init__(factory)`).
    -   Initializes a logging instance
    -   Initializes the database sessions.
-   **Parameters:**
    -   `factory`: The dependency injection factory.
    -   `session_maker` (optional): The SQLAlchemy session maker (defaults to `Session`).
-   **Returns:** None

### `init_app(self, app: Flask)`

-   **Description:** Initializes the controller with a Flask application.
-   **Parameters:**
    -   `app`: The Flask application instance.
-   **Returns:** None
-   **Details:**
    -   Sets the `app` attribute to the Flask application instance.
    -   Updates the configuration from the app, including the session maker and session limit.

### `get_system_admin(self) -> User`

-   **Description:** Retrieves the system admin user.
    This method checks if a system admin user exists and returns it.
    If no admin user exists, it will return an empty result.
-   **Parameters:** None
-   **Returns:** A `User` object representing the system admin.
-   **Details:**
    -   Queries the `UserORM` table for a user with the `SYSTEM_ADMIN` role.
    -   If no admin user exists, it will return an empty result.

### `create_system_admin(self) -> User`

-   **Description:** Create a system admin user if it does not exist.
        This is a one-time setup method to ensure the system has an admin user.
    -   :param company_id:
    -   :return:
### `close(self)`

-   **Description:** Closes all database sessions.
-   **Parameters:** None
-   **Returns:** None
-   **Details:**
    -   Iterates over the sessions and closes them.

### `get_session(self)`

-   **Description:** A context manager for getting a database session.
-   **Parameters:** None
-   **Returns:** A context manager that yields a database session.
-   **Details:**
    -   Retrieves a session from the pool, or creates a new session if the pool is empty.
    -   Commits the session if there are any changes.
    -   Rolls back the session in case of an exception.
    -   Returns the session to the pool.

### `error_handler(view_func)`

-   **Description:** A decorator that wraps controller methods to handle exceptions.
-   **Parameters:**
    -   `view_func`: The controller method to decorate.
-   **Returns:** A wrapped method that handles exceptions.
-   **Details:**
    -   Catches exceptions such as `OperationalError`, `ProgrammingError`, `IntegrityError`, `UnauthorizedError`, `ConnectionResetError`, and `ValidationError`.
    -   Logs the error and returns an appropriate response (e.g., redirect, flash message, None).

## Input Validation

-   The controller itself does not perform explicit input validation, but relies on other validation layers such as Pydantic models.

## Error Handling

-   The `error_handler` decorator provides a centralized mechanism for handling exceptions in controller methods.

## Notes

-   The `Controllers` class is designed to be subclassed by specific controllers, which implement the actual business logic.
-   The session management and error handling mechanisms are intended to be consistent across all controllers.
# NotificationsController Documentation

## Overview

The `NotificationsController` is responsible for sending various notifications, including application submission confirmations, new application alerts for employers, and application status updates to job seekers.

## Purpose

-   To send email notifications to users and employers related to job applications.
-   To confirm job submissions.
-   To notify employers of new applications.
-   To update job seekers on their application status.

## Dependencies

-   `EmailModel`: Pydantic model for email message structure.
-   `get_service`: Helper function for retrieving services (e.g., `send_mail`).
-   Flask: Used for application context and template rendering.
-   `Controllers`: Base class for all controllers, provides `get_session` and `init_app`.
-   `error_handler`: Decorator for handling exceptions.

## Methods

### `__init__(self, factory)`

-   **Description:** Initializes the controller with a session factory.
    -   Calls the superclass constructor (`Controllers.__init__(factory)`).
-   **Parameters:**
    -   `factory`: The session factory used to create database sessions.
-   **Returns:** None

### `init_app(self, app: Flask)`

-   **Description:** Initializes the controller with a Flask application.
-   **Parameters:**
    -   `app`: The Flask application instance.
-   **Returns:** None
-   **Details:**
    -   Calls the superclass's `init_app` method.

### `send_application_submission_notification(self, application_data: dict, user_email: str, user_name: str)`

-   **Description:** Sends an application submission confirmation email to the job seeker.
-   **Parameters:**
    -   `application_data` (dict): Dictionary containing application details (e.g., job title, company name, application ID).
    -   `user_email` (str): The job seeker's email address.
    -   `user_name` (str): The job seeker's name.
-   **Returns:** `True` if the email was sent successfully, `False` otherwise.
-   **Details:**
    1.  Renders the email body using a Jinja2 template (`email/application_submission_confirmation.html`).
    2.  Creates an `EmailModel` instance with the subject, recipient, and HTML body.
    3.  Sends the email using the `send_mail` service.

### `send_new_application_notification(self, application_data: dict, employer_email: str, employer_name: str)`

-   **Description:** Sends a new application notification email to the employer.
-   **Parameters:**
    -   `application_data` (dict): Dictionary containing application details.
    -   `employer_email` (str): The employer's email address.
    -   `employer_name` (str): The employer's name.
-   **Returns:** `True` if the email was sent successfully, `False` otherwise.
-   **Details:**
    1.  Renders the email body using a Jinja2 template (`email/new_application_notification.html`).
    2.  Creates an `EmailModel` instance with the subject, recipient, and HTML body.
    3.  Sends the email using the `send_mail` service.

### `send_application_status_update(self, application_data: dict, user_email: str, user_name: str, new_status: str)`

-   **Description:** Sends an application status update notification to the job seeker.
-   **Parameters:**
    -   `application_data` (dict): Dictionary containing application details.
    -   `user_email` (str): The job seeker's email address.
    -   `user_name` (str): The job seeker's name.
    -   `new_status` (str): The new application status.
-   **Returns:** `True` if the email was sent successfully, `False` otherwise.
-   **Details:**
    1.  Selects a status message based on the `new_status`.
    2.  Renders the email body using a Jinja2 template (`email/application_status_update.html`).
    3.  Creates an `EmailModel` instance with the subject, recipient, and HTML body.
    4.  Sends the email using the `send_mail` service.

## Input Validation

-   The controller relies on the underlying services and Pydantic models to handle input validation.

## Error Handling

-   The `@error_handler` decorator is used to wrap methods, providing a consistent way to catch exceptions, log errors, and return structured error responses.

## Notes

-   The controller relies on properly configured email templates.
-   The `send_mail` service must be available for the controller to function correctly.
-   This controller uses base controller for database session management and error handling.
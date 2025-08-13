# JobApplicationsController Documentation

## Overview
The `JobApplicationsController` manages job applications, including creation and status updates, and integrates with a referral tracking service.

## Purpose
-   To handle the creation of new job applications.
-   To update the status of existing job applications.
-   To link referrals to applications and track referral progress.

## Dependencies

-   `ReferralTrackingService`: For managing referrals and tracking their status.
-   SQLAlchemy ORM models: `JobApplicationORM`.
-   Flask: Used for application context.
-   `Controllers`: Base class for all controllers, provides `get_session` and `init_app`.
-   `error_handler`: Decorator for handling exceptions.

## Methods

### `__init__(self, factory)`

-   **Description:** Initializes the controller with a session factory and sets up the `ReferralTrackingService`.
    -   Calls the superclass constructor (`Controllers.__init__(factory)`).
    -   Initializes the `ReferralTrackingService`.
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

### `create_application(self, user_id: str, job_id: str, application_data: Dict, referral_code: Optional[str] = None) -> Dict[str, Any]`

-   **Description:** Creates a new job application with optional referral tracking.
-   **Parameters:**
    -   `user_id` (str): The applicant's user ID.
    -   `job_id` (str): The ID of the job being applied to.
    -   `application_data` (Dict): The application form data.
    -   `referral_code` (Optional[str]): An optional referral code if the application came from a referral.
-   **Returns:** A dictionary containing the success status and the application ID.
-   **Details:**
    1.  Creates a new `JobApplicationORM` record in the database.
    2.  If a referral code is provided, links the referral to the application using `_link_referral_to_application`.

### `_link_referral_to_application(self, referral_code: str, application_id: str) -> None`

-   **Description:** Links a referral to an application if the referral code is valid.
-   **Parameters:**
    -   `referral_code` (str): The referral code from the share link.
    -   `application_id` (str): The ID of the new application.
-   **Raises:** `ValueError` if the referral code is invalid.
-   **Details:**
    1.  Retrieves the referral using the `ReferralTrackingService`.
    2.  Updates the referral with the application ID.

### `update_application_status(self, application_id: str, status: str, notes: Optional[str] = None) -> Dict[str, Any]`

-   **Description:** Updates the status of an existing job application and tracks referral progress if applicable.
-   **Parameters:**
    -   `application_id` (str): The ID of the application to update.
    -   `status` (str): The new status of the application.
    -   `notes` (Optional[str]): Optional notes for the status update.
-   **Returns:** A dictionary containing the success status of the update.
-   **Details:**
    1.  Retrieves the `JobApplicationORM` record from the database.
    2.  Updates the status and notes.
    3.  If the application has a referral, updates the referral status using `_map_application_status_to_referral_status` and `ReferralTrackingService`.

### `_map_application_status_to_referral_status(self, app_status: str) -> Optional[str]`

-   **Description:** Maps an application status to a corresponding referral status.
-   **Parameters:**
    -   `app_status` (str): The application status.
-   **Returns:** The corresponding referral status or `None` if no mapping exists.
-   **Details:**
    -   Uses a dictionary to map application statuses to referral statuses.

## Input Validation

-   The controller performs basic input validation, such as checking for valid UUIDs.

## Error Handling

-   The `@error_handler` decorator is used to wrap methods, providing a consistent way to catch exceptions, log errors, and return structured error responses.

## Notes
-   This controller uses `ReferralTrackingService` which needs to be initialized first.
-   This controller uses base controller for database session management and error handling.
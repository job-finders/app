# BillingController Documentation

## Overview
The `BillingController` manages billing-related operations, including creating subscriptions, processing payments, generating invoices, and handling trial periods. It integrates with various services such as PayFast for payment processing and Celery for asynchronous email sending.

## Purpose
- To manage company subscriptions and billing profiles.
- To process payments and generate invoices.
- To handle trial periods and subscription renewals.
- To provide a billing dashboard for administrators.

## Dependencies

-   `BillingService`: Manages billing profiles, subscriptions, and plan lookups.
-   `InvoiceService`: Manages invoice creation and retrieval.
-   `PaymentService`: Handles payment processing through PayFast.
-   `BillingCronService`: Manages scheduled billing tasks.
-   `BillingEventService`: Records billing-related events.
-   `BillingEmailerService`: Sends billing-related emails.
-   `PayFastClient`: Client for interacting with the PayFast payment gateway.
-   `CompanyController`: Used to fetch company information.
-   `config_instance`: Provides access to configuration settings.
-   `enqueue_email`: Celery task for sending emails asynchronously.
-   Database Models: `CompanyBillingProfile`, `BillingPlan`

## Methods

### `__init__(self, factory)`

-   **Description:** Initializes the controller with a session factory and sets up the required services.
    -   Calls the superclass constructor (`Controllers.__init__(factory)`).
    -   Initializes various services, including `BillingService`, `InvoiceService`, `PaymentService`, and `BillingCronService`.
-   **Parameters:**
    -   `factory`: The session factory used to create database sessions.
-   **Returns:** None

### `init_app(self, app: Flask)`

-   **Description:** Initializes the controller with a Flask application and starts the billing cron service.
-   **Parameters:**
    -   `app`: The Flask application instance.
-   **Returns:** None
-   **Details:**
    -   Calls the superclass's `init_app` method.
    -   Safely executes an asynchronous initialization task (`_safe_execute`).

### `create_subscription(self, company_id: str, plan_id: str)`

-   **Description:** Creates a subscription for a company with a specified billing plan.
-   **Parameters:**
    -   `company_id` (str): The ID of the company.
    -   `plan_id` (str): The ID of the billing plan.
-   **Returns:** A PayFast form for payment if the plan is not a trial, or a redirect to the company dashboard if it is.
-   **Details:**
    1.  Looks up the billing plan and billing profile.
    2.  If no billing profile exists, creates one (either as a trial or a regular subscription).
    3.  If the plan is not a trial, generates an invoice and returns a PayFast form for payment.
    4.  If the plan is a trial, flashes a success message and redirects to the company dashboard.

### `get_trial_billing_plan(self) -> BillingPlan | None`

-   **Description:** Retrieves the trial billing plan.
-   **Parameters:** None
-   **Returns:** The trial `BillingPlan` or `None` if no trial plan exists.
-   **Details:**
    1.  Lists all billing plans.
    2.  Returns the first plan that is marked as a trial.

### `itn_callback(self, data: dict)`

-   **Description:** Processes the Instant Transaction Notification (ITN) callback from PayFast.
-   **Parameters:**
    -   `data` (dict): The data received from PayFast.
-   **Returns:** A dictionary containing the result of the processing.
-   **Details:**
    1.  Processes the ITN data using the `PaymentService`.
    2.  If the payment is valid and complete, marks the invoice as paid and applies the subscription to the company.
    3.  Records billing events for payment success or failure.

### `get_billing_dashboard(self, company_id: str)`

-   **Description:** Retrieves data for the billing dashboard.
-   **Parameters:**
    -   `company_id` (str): The ID of the company.
-   **Returns:** A dictionary containing billing profile, billing plans, invoices, and recent events.
-   **Details:**
    1.  Retrieves the billing profile, list of invoices, and billing events for the company.
    2.  Looks up the current billing plan.

### `has_billing_profile(self, company_id: str) -> bool`

-   **Description:** Checks if a company has an active billing profile.
-   **Parameters:**
    -   `company_id` (str): The ID of the company.
-   **Returns:** A boolean indicating whether the company has an active billing profile.

### `handle_trial_expiry(self, company_id: str)`

-   **Description:** Handles the expiry of a company's trial period.
-   **Parameters:**
    -   `company_id` (str): The ID of the company.
-   **Returns:** The result of the `expire_trial` action.

### `generate_invoice(self, company_id: str)`

-   **Description:** Generates an invoice for a company.
-   **Parameters:**
    -   `company_id` (str): The ID of the company.
-   **Returns:** The result of the `create_invoice` action.

### `process_payment(self, invoice_id: str)`

-   **Description:** Processes a payment for an invoice.
-   **Parameters:**
    -   `invoice_id` (str): The ID of the invoice.
-   **Returns:** The result of the `process_payment` action.

### `sync_subscription_status(self, company_id: str)`

-   **Description:** Synchronizes the subscription status for a company.
-   **Parameters:**
    -   `company_id` (str): The ID of the company.
-   **Returns:** The result of the `update_subscription_state` action.

### `cron_update_subscription_states(self)`

-   **Description:** Updates the subscription states for all companies.
-   **Parameters:** None
-   **Returns:** The result of the `update_all_subscription_states` action.

### `cron_billing(self)`

-   **Description:** Runs the billing cron service.
-   **Parameters:** None
-   **Returns:** The result of the `run` action of the `BillingCronService`.

### `get_billing_plan_from_slug(self, plan_slug: str)`

-   **Description:** Retrieves a billing plan from its slug.
-   **Parameters:**
    -   `plan_slug` (str): The slug of the billing plan.
-   **Returns:** The `BillingPlan` object or `None` if not found.

### `get_all_billing_plans(self)`

-   **Description:** Retrieves all billing plans.
-   **Parameters:** None
-   **Returns:** A list of `BillingPlan` objects.

### `get_create_billing_profile(self, company_id: str, plan_id: str)`

-   **Description:** Creates a billing profile for the company if it does not exist.
    -   :param company_id:
    -   :param plan_id:
    -   :return: BillingProfile
-   **Parameters:** None
-   **Returns:** A `BillingProfile` object.

### `get_billing_profile(self, company_id: str)`

-   **Description:** Get the billing profile for the company.
    -   :param company_id:
    -   :return: BillingProfile
-   **Parameters:** None
-   **Returns:** A `BillingProfile` object.

## Input Validation

-   The controller relies on the underlying services to handle input validation.

## Error Handling

-   The `@error_handler` decorator is used to wrap most methods, providing a consistent way to catch exceptions, log errors, and return structured error responses.

## Notes

-   The controller relies heavily on other services to perform its tasks, so ensure those dependencies are properly configured.
-   The controller makes extensive use of asynchronous operations to improve performance.
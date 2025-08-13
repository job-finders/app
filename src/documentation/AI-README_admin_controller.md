# AdminController Documentation

## Overview
The `AdminController` provides a unified interface for system administrators to perform job moderation, compliance checks, analytics, security monitoring, and data export. It orchestrates various service classes and exposes methods for both synchronous and asynchronous admin workflows.

## Purpose
- To centralize administrative operations related to job moderation, compliance, analytics, and security.
- To provide methods for managing jobs, analyzing data, and ensuring system integrity.
- To facilitate data export for GDPR compliance.

## Methods

### `__init__(self, factory)`
- **Description**: Initializes the controller with a session factory and service instances.
- **Parameters**:
  - `factory`: The session factory used to create database sessions.
- **Returns**: None
- **Details**:
  - Calls the superclass constructor (`Controllers.__init__(factory)`).
  - Obtains a system admin user.
  - Initializes the `JobModerationService`, `ComplianceService`, `AnalyticsService`, `SecurityService`, and `JobRecommendationService` with the session factory and system admin user.

### `init_app(self, app: Flask)`
- **Description**: Registers the controller with a Flask application.
- **Parameters**:
  - `app`: The Flask application instance.
- **Returns**: None
- **Details**:
  - Calls the superclass's `init_app` method.

### `cleanup_old_approvals(self) -> AdminActionResult`
- **Description**: Deletes job approval requests older than 30 days.
- **Parameters**: None
- **Returns**: `AdminActionResult` with success status, message, and the number of deleted approvals.
- **Details**:
  - Calculates a cutoff time 30 days in the past.
  - Deletes records from the `JobApprovalRequestORM` table where `requested_at` is older than the cutoff.
  - Commits the changes to the database.

### `send_job_alerts_to_users(self) -> AdminActionResult`
- **Description**: Sends job alerts to users based on their preferences.
- **Parameters**: None
- **Returns**: `AdminActionResult` with success status and a message indicating the number of alerts sent.
- **Details**:
  - Executes the `recommend_jobs` method of the `job_recommendation_service`.
  - Composes and sends email alerts to users based on job recommendations.

### `approve_jobs(self) -> AdminActionResult`
- **Description**: Approves jobs that have been posted by companies.
- **Parameters**: None
- **Returns**: `AdminActionResult` with the result of the approval process.
- **Details**:
  - Executes the `approve` method of the `job_moderation_service`.

### `reject_job(self, job_id: str, reviewer_id: str, reason: str) -> AdminActionResult`
- **Description**: Rejects a job posting with a specified reason.
- **Parameters**:
  - `job_id` (str): The ID of the job to reject.
  - `reviewer_id` (str): The ID of the admin user rejecting the job.
  - `reason` (str): The reason for rejecting the job.
- **Returns**: `AdminActionResult` with the result of the rejection.
- **Details**:
  - Executes the `reject` method of the `job_moderation_service`.

### `flag_job(self, job_id: str, reason: str, reporter_id: str) -> AdminActionResult`
- **Description**: Flags a job for admin review.
- **Parameters**:
  - `job_id` (str): The ID of the job to flag.
  - `reason` (str): The reason for flagging the job.
  - `reporter_id` (str): The ID of the user reporting the job.
- **Returns**: `AdminActionResult` with the result of the flagging.
- **Details**:
  - Executes the `flag` method of the `job_moderation_service`.

### `bulk_update_job_status(self, job_ids: List[str], new_status: str) -> AdminActionResult`
- **Description**: Updates the status of multiple jobs in bulk.
- **Parameters**:
  - `job_ids` (List[str]): A list of job IDs to update.
  - `new_status` (str): The new status to apply to the jobs.
- **Returns**: `AdminActionResult` with the result of the bulk update.
- **Details**:
  - Executes the `bulk_update` method of the `job_moderation_service`.

### `detect_anomalous_job_postings(self) -> AdminActionResult`
- **Description**: Identifies suspicious jobs using multi-factor analysis.
- **Parameters**: None
- **Returns**: `AdminActionResult` with a list of anomalous job postings.
- **Details**:
  - Executes the `detect_anomalies` method of the `job_moderation_service`.

### `check_bee_compliance(self, job_id: str) -> AdminActionResult`
- **Description**: Checks B-BBEE compliance for a job's company.
- **Parameters**:
  - `job_id` (str): The ID of the job to check.
- **Returns**: `AdminActionResult` with compliance data.
- **Details**:
  - Executes the `bee_compliance` method of the `compliance_service`.

### `generate_employment_equity_report(self) -> AdminActionResult`
- **Description**: Generates an employment equity report for regulatory compliance.
- **Parameters**: None
- **Returns**: `AdminActionResult` with gender and disability statistics.
- **Details**:
  - Executes the `employment_equity` method of the `compliance_service`.

### `generate_pay_equity_report(self, company_id: str) -> AdminActionResult`
- **Description**: Analyzes salary distributions for pay equity within a company.
- **Parameters**:
  - `company_id` (str): The ID of the company to analyze.
- **Returns**: `AdminActionResult` with salary distribution data.
- **Details**:
  - Executes the `pay_equity` method of the `compliance_service`.

### `analyze_application_biases(self, job_id: str) -> AdminActionResult`
- **Description**: Detects potential discrimination patterns in the hiring process for a specific job.
- **Parameters**:
  - `job_id` (str): The ID of the job to analyze.
- **Returns**: `AdminActionResult` with a demographic breakdown and rejection rates.
- **Details**:
  - Executes the `bias_analysis` method of the `compliance_service`.

### `generate_system_health_report(self) -> AdminActionResult`
- **Description**: Monitors platform health metrics.
- **Parameters**: None
- **Returns**: `AdminActionResult` with job, user, and performance statistics.
- **Details**:
  - Executes the `system_health` method of the `analytics_service`.

### `analyze_platform_engagement(self) -> AdminActionResult`
- **Description**: Tracks key engagement metrics on the platform.
- **Parameters**: None
- **Returns**: `AdminActionResult` with user activity and feature usage data.
- **Details**:
  - Executes the `engagement` method of the `analytics_service`.

### `flag_unusual_user_activity(self) -> AdminActionResult`
- **Description**: Detects suspicious user behavior patterns.
- **Parameters**: None
- **Returns**: `AdminActionResult` with a risk analysis.
- **Details**:
  - Executes the `flag_unusual_user_activity` method of the `security_service`.

### `evaluate_user_risks(self) -> AdminActionResult`
- **Description**: Run risk evaluations on flagged users and log admin recommendations.
- **Parameters**: None
- **Returns**: `AdminActionResult` with the recommendations applied.
- **Details**:
  - Executes the `apply_user_risk_recommendations` method of the `security_service`.

### `get_job_audit_log(self, job_id: str) -> AdminActionResult`
- **Description**: Retrieves the complete modification history for a job.
- **Parameters**:
  - `job_id` (str): The ID of the job to audit.
- **Returns**: `AdminActionResult` with a list of job version changes.
- **Details**:
  - Executes the `audit_log` method of the `analytics_service`.

### `export_user_data(self, user_id: str) -> AdminActionResult`
- **Description**: Exports user data for GDPR compliance.
- **Parameters**:
  - `user_id` (str): The ID of the user to export data for.
- **Returns**: `AdminActionResult` with user profile, search, and application data.
- **Details**:
  - Retrieves user profile, search activities, and applications from the database.

### `export_company_data(self, company_id: str) -> AdminActionResult`
- **Description**: Exports company data for GDPR compliance.
- **Parameters**:
  - `company_id` (str): The ID of the company to export data for.
- **Returns**: `AdminActionResult` with company data and relationships.
- **Details**:
  - Retrieves company data and related information.

### `review_company_verifications(self) -> AdminActionResult`
- **Description**: Identifies companies needing verification checks.
- **Parameters**: None
- **Returns**: `AdminActionResult` with a list of unverified or flagged companies.
- **Details**:
  - Queries the database for companies that are either unverified or have a high number of flagged jobs.

### `get_admin_dashboard_data(self) -> AdminActionResult`
- **Description**: Gathers and returns comprehensive dashboard data for system administrators.
- **Parameters**: None
- **Returns**: `AdminActionResult` with aggregated statistics for dashboard display.
- **Details**:
  - Retrieves user, resume, job, company, and application statistics.
  - Gathers system health and engagement data.

## Input Validation
- The controller relies on the underlying services (`JobModerationService`, `ComplianceService`, `AnalyticsService`, `SecurityService`) to handle input validation.
- It also uses the `AdminActionResult` to provide feedback on the success or failure of operations, including error messages.

## Error Handling
- The `@error_handler` decorator is used to wrap most methods, providing a consistent way to catch exceptions, log errors, and return structured error responses.
- The `AdminActionResult` class is used to standardize responses, including success status and error messages.

## Dependencies
- **Models**: `CompanyORM`, `JobsORM`, `JobApprovalRequestORM`, `JobApplicationORM`, `JobSeekerProfileORM`, `UserORM`, `UserSearchActivityORM`, `FlaggedUserORM`
- **Services**: `JobModerationService`, `ComplianceService`, `AnalyticsService`, `SecurityService`, `JobRecommendationService`
- **Flask**: Used for application context.
- **SQLAlchemy**: Used for database interactions.
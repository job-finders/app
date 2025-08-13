# CandidateBenchMarkController Documentation

## Overview
The `CandidateBenchMarkController` is responsible for benchmarking candidates against job requirements from two perspectives:
- **Employers**: Evaluate candidate suitability for hiring decisions.
- **Employees**: Assess job fit and career development opportunities.

## Purpose
- Provides comprehensive candidate-job matching analysis.
- Offers dual-perspective insights (employer/employee).
- Suggests career development paths for employees.
- Assesses hiring risks for employers.
- Recommends CV optimizations.

## Dependencies
-   `users_controller`: User profile data
-   `resume_controller`: CV/Resume handling
-   `jobs_search_controller`: Job details
-   `job_application_controller`: Application context
-   `CandidateBenchmarkAgent`: Core benchmarking agent

## Methods

### `__init__(self, factory)`
-   **Description:** Initializes the controller with a session factory.
    -   Calls the superclass constructor (`Controllers.__init__(factory)`).
-   **Parameters:**
    -   `factory`: The session factory used to create database sessions.
-   **Returns:** None

### `init_app(self, app: Flask)`
-   **Description:** Registers the controller with a Flask application.
-   **Parameters:**
    -   `app`: The Flask application instance.
-   **Returns:** None
-   **Details:** Calls the superclass's `init_app` method.

### `benchmark_for_employer(self, job_application_id: str, employer_id: str) -> CandidateBenchmarkReport | None`
-   **Description:** Benchmarks a candidate from an employer's perspective to inform hiring decisions.
-   **Parameters:**
    -   `job_application_id` (str): The ID of the job application to evaluate.
    -   `employer_id` (str): The ID of the employer performing the evaluation.
-   **Returns:** `CandidateBenchmarkReport` with hiring insights and risk assessment, or `None` if data is missing.
-   **Details:**
    1.  Fetches necessary controllers (`jobs_workflow`, `jobs_search`, `resume`, `company`, `job_seeker_profile`).
    2.  Retrieves application, job, candidate CV, and candidate profile data.
    3.  Validates that all required data exists.
    4.  Combines candidate profile and CV data into a single text.
    5.  Prepares input for the `CandidateBenchmarkAgent`.
    6.  Executes the `CandidateBenchmarkAgent` to generate the report.
-   **Dependencies:**
    -   `JobsWorkflowController`
    -   `JobsSearchController`
    -   `ResumeController`
    -   `CompanyController`
    -   `JobSeekerProfilesController`

### `benchmark_for_employee(self, user_id: str, job_id: str, cv_id: Optional[str] = None) -> CandidateBenchmarkReport | None`
-   **Description:** Benchmarks a job fit from an employee's perspective for career development.
-   **Parameters:**
    -   `user_id` (str): The ID of the job seeker.
    -   `job_id` (str): The ID of the target job.
    -   `cv_id` (Optional[str]): An optional specific CV ID to use (defaults to the primary CV).
-   **Returns:** `CandidateBenchmarkReport` with career development insights, or `None` if data is missing.
-   **Details:**
    1.  Fetches necessary controllers (`jobs_search`, `resume`, `job_seeker_profile`).
    2.  Retrieves job, candidate profile, and candidate CV data.
    3.  Validates that all required data exists.
    4.  Combines candidate profile and CV data into a single text.
    5.  Prepares input for the `CandidateBenchmarkAgent`.
    6.  Executes the `CandidateBenchmarkAgent` to generate the report.
-   **Dependencies:**
    -   `JobsSearchController`
    -   `ResumeController`
    -   `JobSeekerProfilesController`

## Data Handling

-   The controller aggregates data from multiple sources (user profiles, job postings, CVs) into a single input format for the `CandidateBenchmarkAgent`.
-   It validates the presence of required data and logs errors if data is missing.
-   It uses helper methods to combine candidate information for the agent.

## Error Handling

-   The `@error_handler` decorator is used to wrap methods, providing a consistent way to catch exceptions, log errors, and return structured error responses.
-   The controller logs benchmarking requests and results, as well as any errors encountered.

## Notes

- The controller relies heavily on other controllers and services to gather data, so ensure those dependencies are properly configured.
- The `CandidateBenchmarkAgent` performs the core benchmarking logic and must be implemented separately.
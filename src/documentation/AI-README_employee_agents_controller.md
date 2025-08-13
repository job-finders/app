# EmployeeAgentsController Documentation

## Overview
The `EmployeeAgentsController` is responsible for AI-assisted job matching, CV optimization, and cover letter generation for job seekers. It leverages AI agents to provide intelligent features that help job seekers find suitable jobs and improve their application materials.

## Purpose
- To provide job seekers with AI-powered tools for job matching, CV optimization, and cover letter generation.
- To facilitate intelligent agent-based features by interacting with user, resume, and job services.

## Dependencies
-   `users_controller`: For fetching user information.
-   `resume_controller`: For fetching and managing CVs.
-   `job_search_controller`: For retrieving job details.
-   `ApplicationCoachAgent`: AI agent for job match analysis.
-   `CoverLetterAgent`: AI agent for generating tailored cover letters.

## Methods

### `__init__(self, factory)`
-   **Description:** Initializes the controller with a session factory.
    -   Calls the superclass constructor (`Controllers.__init__(factory)`).
-   **Parameters:**
    -   `factory`: The session factory used to create database sessions.
-   **Returns:** None

### `init_app(app: Flask)`
-   **Description:** Registers the controller with a Flask application.
-   **Parameters:**
    -   `app`: The Flask application instance.
-   **Returns:** None
-   **Details:** Calls the superclass's `init_app` method.

### `analyze_job_match(self, user_id: str, job_id: str, cv_id: Optional[str] = None, cover_letter: Optional[str] = None) -> JobMatchInsights | None`
-   **Description:** Analyzes how well a candidate matches a specific job.
-   **Parameters:**
    -   `user_id` (str): The ID of the job seeker.
    -   `job_id` (str): The ID of the job to match against.
    -   `cv_id` (Optional[str]): If a CV is selected, runs the match for the selected CV.
    -   `cover_letter` (Optional[str]): Optional cover letter text.
-   **Returns:** `JobMatchInsights` with analysis and recommendations, or `None` if data is missing.
-   **Details:**
    1.  Fetches necessary controllers (`users`, `jobs_search`, `resume`).
    2.  Retrieves user, job, and resume data.
    3.  Prepares input for the `ApplicationCoachAgent`.
    4.  Executes the `ApplicationCoachAgent` to generate the report.
-   **Dependencies:**
    -   `UsersController`
    -   `JobsSearchController`
    -   `ResumeController`

### `generate_cover_letter(self, user_id: str, job_id: str, cv_id: str, tone: Optional[str] = "professional") -> CoverLetterOutput | None`
-   **Description:** Generates a tailored cover letter for a specific job application.
-   **Parameters:**
    -   `user_id` (str): The ID of the user.
    -   `job_id` (str): The ID of the job.
    -   `cv_id` (str): The CV id.
    -   `tone` (Optional[str]): The tone of the cover letter (defaults to "professional").
-   **Returns:** `CoverLetterOutput` with generated cover letter sections, or `None` if data is missing.
-   **Details:**
    1.  Fetches necessary controllers (`users`, `jobs_search`, `resume`).
    2.  Retrieves user, job, and resume data.
    3.  Prepares input for the `CoverLetterAgent`.
    4.  Executes the `CoverLetterAgent` to generate the cover letter.
-   **Dependencies:**
    -   `UsersController`
    -   `JobsSearchController`
    -   `ResumeController`

### `optimize_primary_cv(self, primary_resume: JobSeekerCV)`
-   **Description:** Optimizes the CV to rank higher based on ATS (Applicant Tracking System) ranking.
-   **Parameters:**
    -   `primary_resume` (JobSeekerCV): The primary resume to optimize.
-   **Returns:** None
-   **Details:** This method is a placeholder and needs further implementation with an Agent.

## Input Validation
-   The controller performs input validation to ensure that the required data (user, job, CV) exists before proceeding with the analysis or generation.
-   It uses explicit checks to validate the presence of data.

## Error Handling
-   The `@error_handler` decorator is used to wrap methods, providing a consistent way to catch exceptions, log errors, and return structured error responses.
-   The controller logs important events and errors to provide insights into the system's behavior.

## Notes
-   The controller relies heavily on other controllers and services to gather data, so ensure those dependencies are properly configured.
-   The `ApplicationCoachAgent` and `CoverLetterAgent` perform the core logic for job matching and cover letter generation, respectively, and must be implemented separately.
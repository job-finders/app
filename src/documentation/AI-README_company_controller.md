# CompanyController Documentation

## Overview
The `CompanyController` handles all business logic related to company and employer management within the platform. It encompasses company CRUD operations, employer management, job postings, candidate handling, and verification workflows.

## Purpose
-   Manage company and employer profiles.
-   Handle job postings and candidate management for companies.
-   Implement verification processes for companies and employers.
-   Provide data and functionality for company-related features.

## Dependencies

-   SQLAlchemy ORM models: `CompanyORM`, `EmployerORM`, `JobsORM`, `UserORM`, etc.
-   Pydantic models: `Company`, `Employer`, `Job`, etc.
-   Flask: Request context, URL generation, and template rendering.
-   Email service: For sending notifications.
-   Logger: For activity and error tracking.
-   AI/ML service: For document analysis (future enhancement).
-   `JobsWorkflowController`: For job-related workflows.
-   `ResumeController`: For resume/CV handling.
-    `EmployerAiAgentsController`: For document verification.

## Methods

### `__init__(self, factory)`
-   **Description:** Initializes the controller with a session factory and sets up the required services and controllers.
    -   Calls the superclass constructor (`Controllers.__init__(factory)`).
    -   Initializes the logger, jobs workflow controller, resume controller, and employer AI agents controller.
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

### `get_all_companies(self) -> list[Company]`
-   **Description:** Retrieves all companies from the database.
-   **Parameters:** None
-   **Returns:** A list of `Company` objects.
-   **Details:**
    -   Queries the `CompanyORM` table for all records.
    -   Converts the ORM objects to Pydantic `Company` models.

### `create_company(self, company_data: Company) -> Company`
-   **Description:** Creates a new company in the database.
-   **Parameters:**
    -   `company_data` (Company): The company data to create.
-   **Returns:** The created `Company` object.
-   **Details:**
    -   Checks if a company with the same name already exists (case-insensitive).
    -   Sets the IP address for the company.
    -   Adds the new company to the database.

### `get_employer_created_company(self, uid: str) -> Optional[Company]`
-   **Description:** Retrieves the company created by a specific employer (user).
-   **Parameters:**
    -   `uid` (str): The user ID of the employer.
-   **Returns:** The `Company` object created by the employer, or `None` if not found.
-   **Details:**
    -   Queries the `EmployerORM` table to find the employer with the given user ID.
    -   Retrieves the company associated with the employer.

### `register_employer(self, employer_data: Employer) -> Optional[Employer]`
-   **Description:** Registers a new employer profile and associates it with a company.
-   **Parameters:**
    -   `employer_data` (Employer): The employer data to register.
-   **Returns:** The registered `Employer` object, or `None` if registration fails.
-   **Details:**
    -   Checks if an employer profile already exists for the given user ID.
    -   Sets the IP address for the employer.
    -   Creates a new `EmployerORM` record in the database.

### `get_company_by_id(self, company_id: str) -> Optional[Company]`
-   **Description:** Retrieves a company by its ID.
-   **Parameters:**
    -   `company_id` (str): The ID of the company to retrieve.
-   **Returns:** The `Company` object, or `None` if not found.
-   **Details:**
    -   Queries the `CompanyORM` table for the company with the given ID.
    -   Eagerly loads the associated jobs.
    -   Converts the ORM object to a Pydantic `Company` model.

### `get_employees_by_company_id(self, company_id: str) -> list[Employer]`
-   **Description:** Retrieves all employers associated with a specific company.
-   **Parameters:**
    -   `company_id` (str): The ID of the company.
-   **Returns:** A list of `Employer` objects.
-   **Details:**
    -   Queries the `EmployerORM` table for all employers with the given company ID.
    -   Converts the ORM objects to Pydantic `Employer` models.

### `get_company_by_name(self, name: str) -> Company | None`
-   **Description:** Retrieves a company by its exact name (case-insensitive).
-   **Parameters:**
    -   `name` (str): The exact name of the company to retrieve.
-   **Returns:** The `Company` object, or `None` if not found.
-   **Details:**
    -   Performs a case-insensitive exact match query on the `CompanyORM` table.
    -   Eagerly loads the associated jobs.
    -   Converts the ORM object to a Pydantic `Company` model.

### `search_companies_by_name(self, name: str) -> list[Company]`
-   **Description:** Searches for companies containing the given name substring.
-   **Parameters:**
    -   `name` (str): The substring to search for in company names.
-   **Returns:** A list of matching `Company` objects.
-   **Details:**
    -   Performs a case-insensitive substring search on the `CompanyORM` table.
    -   Eagerly loads the associated jobs.
    -   Converts the ORM objects to Pydantic `Company` models.

### `get_employer_by_uid(self, user_id: str) -> Employer | None`
-   **Description:** Retrieves an employer by their user ID.
-   **Parameters:**
    -   `user_id` (str): The user ID of the employer.
-   **Returns:** The `Employer` object, or `None` if not found.
-   **Details:**
    -   Queries the `EmployerORM` table for the employer with the given user ID.
    -   Converts the ORM object to a Pydantic `Employer` model.

### `get_employer_by_employer_id(self, employer_id: str) -> Employer| None`
-   **Description:** Retrieves an employer by their employer ID.
-   **Parameters:**
    -   `employer_id` (str): The employer ID.
-   **Returns:** The `Employer` object, or `None` if not found.
-   **Details:**
    -   Queries the `EmployerORM` table for the employer with the given employer ID.
    -   Converts the ORM object to a Pydantic `Employer` model.

### `get_company_jobs(self, company_id: str, status: Optional[JobStatusEnum] = None) -> List[Job]`
-   **Description:** Retrieves all jobs associated with a given company.
-   **Parameters:**
    -   `company_id` (str): The ID of the company.
    -   `status` (Optional[JobStatusEnum]): Optional job status to filter by.
-   **Returns:** A list of `Job` objects associated with the company.
-   **Details:**
    -   Retrieves company by id, eager loads the Jobs
    -   Filters the jobs by the provided status, if any.

### `get_company_jobs_with_job_applications(self, company_id: str) -> List[Job]`
-   **Description:** Retrieves all jobs for a company, including nested applications and candidates.
-   **Parameters:**
    -   `company_id` (str): The ID of the company.
-   **Returns:** A list of `Job` objects associated with the company, with loaded applications.

### `get_all_company_employers(self, company_id: str) -> List[Employer]`
-   **Description:** Retrieves all employers associated with a specific company
-   **Parameters:**
    -   `company_id` (str): UUID of the company
-   **Returns:** List of Employer objects

### `get_application_analytics(self, company_id: str) -> JobApplicationDashboard | None`
-   **Description:** Get hiring metrics using JobsController's analytics engine
-   Combines company-specific filtering with core analytics logic

### `generate_talent_pool_report(self, company_id: str) -> TalentPoolReport | None`
-   **Description:** Generates a talent pool report for a company.
-   **Parameters:**
    -   `company_id` (str): The ID of the company.
-   **Returns:** The `TalentPoolReport` object, or `None` if an error occurs.

### `update_employer_profile(self, employer_profile: Employer) -> Employer | None`
-   **Description:** Updates an existing employer profile.
-   **Parameters:**
    -   `employer_profile` (Employer): The employer profile data to update.
-   **Returns:** The updated `Employer` object, or `None` if the update fails.
-   **Details:**
    -   Retrieves the existing employer ORM from the database.
    -   Updates the scalar fields of the ORM with the values from the Pydantic model.
    -   Handles the company relationship separately, if needed.

### `update_company(self, company_id: str, update_data: CompanyUpdate) -> Company | None`
-   **Description:** Updates an existing company.
-   **Parameters:**
    -   `company_id` (str): The ID of the company to update.
    -   `update_data` (CompanyUpdate): The data to update the company with.
-   **Returns:** The updated `Company` object, or `None` if the update fails.
-   **Details:**
    -   Retrieves the existing company ORM from the database.
    -   Updates the scalar fields of the ORM with the values from the Pydantic model.

### `post_job(self, user_uid: str, job_data: Job) -> Optional[Job]`
-   **Description:** Posts a new job, ensuring the employer and company are verified.
-   **Parameters:**
    -   `user_uid` (str): The user ID of the employer posting the job.
    -   `job_data` (Job): The job data to post.
-   **Returns:** The created `Job` object, or `None` if the posting fails due to verification issues.
-   **Details:**
    -   Checks the verification status of the employer and company.
    -   Creates the job using the `jobs_workflow_controller`.

### `get_saved_candidates(self, user_uid: str) -> list[JobSeekerCV]`
-   **Description:** Retrieves a list of saved candidates (CVs) for a given employer.
-   **Parameters:**
    -   `user_uid` (str): The user ID of the employer.
-   **Returns:** A list of `JobSeekerCV` objects.
-   **Details:**
    -   Checks if the employer is valid and verified.
    -   Retrieves the saved CVs using the `resume_controller`.

### `save_candidate(self, user_uid: str, save_cv_model:SavedCV) -> SavedCV| None`
-   **Description:** Saves a candidate (CV) for an employer.
-   **Parameters:**
    -   `user_uid` (str): The user ID of the employer.
    -   `save_cv_model` (SavedCV): The data for the saved CV.
-   **Returns:** The saved `SavedCV` object, or `None` if saving fails.
-   **Details:**
    -   Checks if the employer is valid and verified.
    -   Saves the CV using the `resume_controller`.

### `initiate_employer_profile_verification(self, employer_id: str) -> None`
-   **Description:** Initiates the employer profile verification process by sending a verification email.
-   **Parameters:**
    -   `employer_id` (str): The ID of the employer.
-   **Returns:** None
-   **Details:**
    -   Generates a unique verification token and sets its expiration time.
    -   Sends a verification email to the employer with a link containing the token.

### `mark_employer_as_verified(self, employer_id: str) -> bool`
-   **Description:** Marks the employer as verified in the database.
-   **Parameters:**
    -   `employer_id` (str): The ID of the employer.
-   **Returns:** True if the employer was successfully marked as verified, otherwise False

### `initiate_company_verification_process(self, company_id: str, document_paths: list, user_id: str)`
-   **Description:**  Handle verification workflow
-   **Parameters:**
    -   `company_id` (str): The ID of the company.
    -    `document_paths` (list): The list of documnet paths
    -   `user_id` (str): The ID of the User
-   **Returns:** A dict with the status of the process.
-   **Details:**
    -   Store documents in database
    -   Run initial AI screening
    -   if AI screening is valid marks the company as verified
    -   if it needs a human review, it will flag it for human review and notifiy admins.

### `get_company_verification_status(self, company_id: str)`
-   **Description:** Get the verification status of a company from the database
        This function will return the verification status of a company from the database
    -   :param company_id:
    -   :return:

### `get_industries()`
-   **Description:** Get a list of industries
        This function will return a List of Industries
    -   :param company_id:
    -   :return:
### `get_countries()`
-   **Description:** Get a list of countries
        This function will return a List of countries
    -   :param company_id:
    -   :return:
### `get_tech_options()`
-   **Description:** Get a list of tech stack options
        This function will return a List of tech stack options
    -   :param company_id:
    -   :return:
### `auto_verify_company_documents(self)`
-   **Description:** THIS IS A CRON ENTRY POINT FOR VERIFYING COMPANY DOCUMENTS
        This task may run in celery or task scheduler.
        fetch documents that have not been reviewed or without recommendations -
        check if company profiles have been properly completed and verified.
        send the documents to a company agent document verifier.
    -   :param company_id:
    -   :return:

## Input Validation

-   The controller relies on the underlying services and Pydantic models to handle input validation.
-   Many methods perform checks for valid UUIDs and data types.

## Error Handling

-   The `@error_handler` decorator is used to wrap most methods, providing a consistent way to catch exceptions, log errors, and return structured error responses.

## Notes

-   The controller relies heavily on other controllers and services to perform its tasks, so ensure those dependencies are properly configured.
-   Some methods contain placeholders for future implementation, such as AI/ML document analysis and admin notifications.
-   Relationships between models are handled via ORM and Pydantic serialization.
# company_models.py Documentation

## Overview

This module defines Pydantic models for representing company data, verification status, and related entities. It includes models for company profiles, verification documents, CIPC data, and tracking user interest in companies.

## Models

### CompanyVerificationStatus

An enumeration of possible company verification statuses:

*   `NOT_VERIFIED`: Company is not verified.
*   `PENDING`: Verification is pending.
*   `HUMAN_REVIEW`: Verification requires human review.
*   `DOCUMENTS_UPLOADED`: Documents have been uploaded.
*   `DOCUMENTS_REJECTED`: Documents have been rejected.
*   `DOCUMENTS_APPROVED`: Documents have been approved.
*   `CIPC_PENDING`: CIPC verification is pending.
*   `CIPC_VERIFIED`: CIPC verification is successful.
*   `CIPC_FAILED`: CIPC verification failed.
*   `VERIFIED`: Company is fully verified.

### Company

Represents a company profile.

*   `company_id`: Unique identifier for the company (UUID).
*   `name`: Name of the company.
*   `description`: Optional description of the company.
*   `industry`: Optional industry of the company.
*   `website`: Optional website URL of the company.
*   `logo_url`: Optional logo URL of the company.
*   `city`: Optional city of the company.
*   `province`: Optional province of the company.
*   `country`: Optional country of the company.
*   `contact_email`: Optional contact email of the company.
*   `phone_number`: Optional phone number of the company.
*   `employee_count`: Optional number of employees in the company.
*   `founded_year`: Optional year the company was founded.
*   `tech_stack`: Optional list of technologies used by the company.
*   `linkedin_url`: Optional LinkedIn URL of the company.
*   `twitter_handle`: Optional Twitter handle of the company.
*   `is_verified`: Optional boolean indicating if the company is verified
*   `time_verification_process_started`: Optional timestamp for when verification started
*    `verification_status`: Optional status of company verification
*   `created_at`: Optional timestamp for when the company was created
*   `updated_at`: Optional timestamp for when the company was updated
*   `jobs`: Optional list of `Job` objects associated with the company.
*   `saved_candidates`: Optional list of `SavedCandidates` objects associated with the company.
*   `employers`: Optional list of `Employer` objects associated with the company.
*   `ip_address`: Optional ip address of the device used to create the company

### AIBasedDocumentReviewResult

Represents the result of an AI-based document review.

*   `review_id`: Unique ID of the review process (UUID).
*   `document_id`: ID of the document reviewed.
*   `is_document_valid`: Indicates if the document is valid.
*   `reason`: Reason for invalidity, if any.
*   `match_director_name`: Whether director name matches expected.
*   `match_id_number`: Whether ID number matches expected.
*   `match_cipc_data`: Whether document data matches CIPC records.
*   `match_company_profile_data`: Whether document matches internal company profile.
*   `cipc_number_verified_online`: Whether CIPC number was verified online.
*   `cipc_number_verification_notes`: Notes on CIPC number verification.
*   `is_suspicious`: Whether the document appears suspicious.
*   `suspicious_notes`: Details of suspicious elements, if any.
*   `requires_human_review`: Whether the document needs human review.
*   `document_type`: Type of the document reviewed.
*   `score`: AI confidence score or overall score of review.
*   `reviewer_notes`: Notes or comments from the AI reviewer.
*   `created_at`: Timestamp when the review was completed.

### CompanyVerificationDocument

Represents a document uploaded for company verification.

*   `document_id`: Unique identifier for the document (UUID).
*   `company_id`: Reference to the company the document belongs to.
*   `ai_review_id`: reference to the AI review if any
*   `document_type`: Type of document (e.g., "CIPC_CERT").
*   `file_url`: URL of the uploaded document file.
*   `uploaded_at`: Timestamp when the document was uploaded.

### DirectorDetails

Represents details of a company director.

*   `director_id`: Unique identifier for the director (UUID).
*   `cipc_id`: CIPC ID of the director.
*   `full_names`: Full names of the director.
*   `id_number`: ID number of the director.

### CompanyCIPC

Represents company registration details from CIPC (Companies and Intellectual Property Commission).

*   `cipc_id`: Unique identifier for the CIPC record (UUID).
*   `company_id`: Reference to the company the record belongs to.
*   `company_name`: Name of the company as registered with CIPC.
*   `registration_number`: Registration number of the company.
*   `registration_date`: Registration date of the company.
*   `registered_address`: Registered address of the company.
*   `company_type`: Type of company (e.g., "Private Company").
*   `director_details`: List of `DirectorDetails` objects associated with the company.
*   `tax_pin`: Tax Pin of the company
*    `bee_status`: BEE status of the company
*   `status`: Status of the CIPC Verification
*   `verified_at`: time the CIPC record was verified

### InterestLevel

Enum for the level of intered a jobseeker has in a company

*    LOW
*   INTERESTED
*   HIGHLY_INTERESTED
*    TOP_PRIORITY
*    ON_HOLD

### CompanyFollowing

Represents a job seeker following a company.

*   `follow_id`: Unique identifier for the follow (UUID).
*   `followed_at`: Date and time the company was followed.
*   `user_id`: Reference to the user following the company.
*   `company_id`: Reference to the company being followed.
*   `last_notified_at`: Last time the user was notified about updates from this company.
*   `interest_level`: The level of interest the use has in the company

### CandidateStatus

Enum for the status a company has marked a candidate as

*    SAVED
*   REVIEWED
*   CONTACTED
*    SCREENING
*    INTERVIEWING
*   OFFER_EXTENDED
*   HIRED
*    REJECTED
*    WITHDRAWN

### SavedCandidates

Represents a company saving a candidate for future consideration.

*   `saved_id`: Unique identifier for the saved candidate record (UUID).
*   `candidate_uid`: Reference to the job seeker profile.
*   `company_id`: Reference to the company saving the candidate.
*   `saved_by`: Reference to the employer who saved the candidate.
*    `interest_level`: level of interest that the company has in the candidate
*   `notes`: Notes about the candidate
*   `internal_notes`: Notes about the candidate that only internal employees can see
*   `tags`: Tags to categorize the candidate
*   `last_contacted_at`: time the candidate was last contacted
*   `contact_count`: number of times the candidate has been contacted
*   `saved_at`: time the candidate was saved
*  `status`: the status the candidate is in, in the job application process

### CompanySettings

Represents settings for a company.

*   `company_id`: Id of the company the settings belong to
*  `default_job_duration_days`: default number of days each job should last for
*   `auto_publish_jobs`: whether to automatically publish a job
*   `job_visibility`: string saying if a job is visible or not
*   `allow_featured_jobs`: whether to allow featured jobs
*   `max_open_jobs`: maximum number of open jobs to allow
*  `auto_response_enabled`: whether to allow automatic response
*   `default_response_message`: default response message to send
*   `require_cover_letter`: whether to require a cover letter
*  `required_documents`: list of required documents
*  `questionnaire_enabled`: whether to enable questionnaires
*   `allow_withdrawals`: whether to allow withdrawals
*   `email_sender_name`: name of the email sender
*   `email_signature`: signature for emails
*   `custom_email_template_enabled`: whether custom email templates are enabled
*  `custom_application_success_page_url`: url for a custom application success page
*   `team_invites_enabled`: whether team invites are enabled
*   `max_recruiters`: maximum number of recruiters
*  `recruiter_roles`: roles of the recruiters
*   `weekly_digest_enabled`: whether weekly digests are enabled
*   `slack_notifications_enabled`: whether slack notifications are enabled
*   `slack_webhook_url`: webhook url for slack
*   `notify_on_new_application`: whether to get notified on a new application

## Relationships to SQL Models

This model corresponds to the following SQL models:

*   [`CompanyORM`](src/database/sql/company.py:12)
*   [`CompanyVerificationDocumentORM`](src/database/sql/company.py:143)
*   [`DirectorDetailsORM`](src/database/sql/company.py:189)
*   [`CompanyCIPCORM`](src/database/sql/company.py:223)
*   [`CompanyFollowingORM`](src/database/sql/company.py:283)
*   [`SavedCandidatesORM`](src/database/sql/company.py:339)

The Pydantic models map directly to their corresponding ORM models in `src/database/sql/company.py`.
# jobs_model.py Documentation

## Overview

This module defines Pydantic models for representing job postings and related entities, such as job likes, shares, and categories. It includes models for job creation, updating, and display, as well as models for tracking user engagement and managing job approval workflows.

## Models

### JobApprovalStatusEnum

An enumeration of possible job approval statuses:

*   `PENDING`: Job is pending approval.
*   `APPROVED`: Job has been approved.
*   `REJECTED`: Job has been rejected.

### JobApprovalRequest

Represents a request for job approval.

*   `request_id`: Unique identifier for the request (UUID).
*   `job_id`: ID of the job being requested for approval.
*   `token`: Unique token for verifying the request.
*   `token_expires`: Expiration timestamp for the token.
*   `requested_at`: Timestamp when the request was created.
*   `requested_by`: ID of the user who requested the approval.
*   `approvers`: List of IDs of users who can approve the request.
*   `status`: Current status of the approval request (from `JobApprovalStatusEnum`).
*   `decision_at`: Timestamp when the request was approved or rejected.
*   `decision_by`: ID of the user who approved or rejected the request.
*   `feedback`: Feedback provided during approval or rejection.

### JobVersionHistory

Represents history of job changes

*   `id`: Unique identifier
*   `job_id`: job id to track
*   `version`: version number
*   `changes`: the changes made to the job
*   `modified_by`: who made the changes
*   `modified_at`: when the changes were made

### JobStatusEnum

An enumeration of possible job statuses:

*   `DRAFT`: Job is in draft state.
*   `ACTIVE`: Job is active and publicly visible.
*   `PENDING_APPROVAL`: Job is pending approval.
*   `NEEDS_ATTENTION`: Job requires attention.
*   `ARCHIVED`: Job is archived.
*   `CLOSED`: Job is closed.

### JobLike

Represents a user liking a job posting.

*   `like_id`: Unique identifier for the like (UUID).
*   `user_id`: ID of the user who liked the job.
*   `job_id`: ID of the job that was liked.
*   `created_at`: Timestamp when the job was liked.

### ShareMethodEnum

An enumeration of possible share methods:

*   `EMAIL`: Shared via email.
*   `LINKEDIN`: Shared via LinkedIn.
*   `TWITTER`: Shared via Twitter.
*   `FACEBOOK`: Shared via Facebook.
*   `WHATSAPP`: Shared via WhatsApp.
*   `COPY_LINK`: Shared via copied link.

### JobShare

Represents a job being shared across different platforms.

*   `share_id`: Unique identifier for the share (UUID).
*   `user_id`: ID of the user who shared the job (optional for anonymous sharing).
*   `job_id`: ID of the job being shared.
*   `share_method`: Method used to share the job (from `ShareMethodEnum`).
*   `shared_at`: Timestamp when the job was shared.
*   `referral_code`: Referral code for tracking.

### JobActionsState

Represents the current state of job actions for a user and job combination.

*   `job_id`: ID of the job.
*   `user_has_liked`: Indicates whether the current user has liked this job.
*   `user_has_saved`: Indicates whether the current user has saved this job.
*   `like_count`: Total number of likes for this job.
*   `share_count`: Total number of shares for this job.

### JobActionRequest

Base model for job action requests.

*   `job_id`: ID of the job.
*   `user_id`: ID of the user performing the action.

### JobLikeRequest

Model for job like/unlike requests.

*   `job_id`: ID of the job.
*   `user_id`: ID of the user performing the action.

### JobSaveRequest

Model for job save/unsave requests.

*   `job_id`: ID of the job.
*   `user_id`: ID of the user performing the action.

### JobShareRequest

Model for job share requests.

*   `job_id`: ID of the job.
*   `user_id`: ID of the user performing the action.
*   `share_method`: Method used to share the job (from `ShareMethodEnum`).

### JobActionsResponse

Standard response model for job actions.

*   `success`: Whether the action was successful.
*   `message`: Response message.
*   `data`: Additional response data.

### JobCategory

Represents a category of jobs.

*   `category_id`: Unique identifier for the category (UUID).
*   `name`: Name of the category.
*   `slug`: Slug for the category.
*   `description`: Description of the category.
*   `seo_description`: Seo description of the category
*   `created_at`: Timestamp when the category was created.
*   `updated_at`: Timestamp when the category was updated.

### Job

Represents a job posting.

*   `job_id`: Unique identifier for the job (UUID).
*   `job_ref`: Unique job reference
*   `category_id`: ID of the job category.
*   `title`: Job title.
*   `description`: Job description.
*   `position_type`: Type of position (e.g., "FULL_TIME").
*   `remote_policy`: Remote work policy (e.g., "ONSITE").
*   `salary_min`: Minimum salary.
*   `salary_max`: Maximum salary.
*   `salary_currency`: Salary currency.
*   `city`: Job location city.
*   `province`: Job location province.
*   `country`: Job location country.
*   `posted_at`: Timestamp when the job was posted.
*   `expires_at`: Timestamp when the job expires.
*   `application_deadline`: Timestamp for the application deadline.
*   `experience_level`: Required experience level.
*   `education_requirements`: Required education qualifications.
*   `required_skills`: List of required skills.
*   `preferred_skills`: List of preferred skills.
*   `application_url`: URL for external applications.
*   `application_instructions`: Instructions for applying.
*   `view_count`: Number of views.
*   `application_count`: Number of applications.
*   `status`: Current status of the job (from `JobStatusEnum`).
*   `is_featured`: Whether the job is featured.
*   `created_at`: Timestamp when the job was created.
*   `updated_at`: Timestamp when the job was updated.

### SavedJob

Represents a job that has been saved by a user.

*   `saved_job_id`: Unique identifier for the saved job (UUID).
*   `user_id`: ID of the user who saved the job.
*   `job_id`: ID of the job that was saved.
*   `created_at`: Timestamp when the job was saved.

### ATSReport

This represents a report generated after analysing the applications
*   `ats_report_id` : String, unique ID
*   `job_id` : String, job id that the report belongs to
*   `cv_id` : String, the cv id of the job application
*   `score` : Integer, the score the cv got for the application
*   `matched_keywords`: List[String], the key words that matched
*   `missing_keywords` : List[String], the key words that the application was missing
*   `feedback` : String, a detailed feedback for the report
*   `created_at` : Time, the time the report was generated

## Relationships to SQL Models

This model corresponds to the following SQL models:

*   [`JobsORM`](src/database/sql/jobs_sql.py:99)
*   [`JobCategoryORM`](src/database/sql/jobs_sql.py:17)
*   [`SavedJobORM`](src/database/sql/jobs_sql.py:300)
*   [`ATSReportORM`](src/database/sql/jobs_sql.py:421)

The Pydantic models map directly to their corresponding ORM models in `src/database/sql/jobs_sql.py`.
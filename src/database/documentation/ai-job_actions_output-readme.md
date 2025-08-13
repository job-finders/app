# job_actions_output.py Documentation

## Overview

This module defines Pydantic models for representing the output of job actions operations. These models convert ORM results to validated business objects, ensuring consistent response formats and proper error handling.

## Models

### JobSeekerProfileOutput

Output model for JobSeeker profile data from the database.

*   `user_uid`: User unique identifier.
*   `first_name`: User's first name.
*   `last_name`: User's last name.
*   `email`: User's email address.
*   `phone`: User's phone number.
*   `is_active`: Whether profile is active.
*   `created_at`: Profile creation timestamp.
*   `updated_at`: Last update timestamp.

### JobOutput

Output model for Job data from the database.

*   `job_id`: Job unique identifier.
*   `title`: Job title.
*   `description`: Job description.
*   `company_id`: Associated company ID.
*   `position_type`: Position type (full-time, part-time, etc.).
*   `remote_policy`: Remote work policy.
*   `city`: Job location city.
*   `province`: Job location province.
*   `country`: Job location country.
*   `salary_min`: Minimum salary.
*   `salary_max`: Maximum salary.
*   `salary_currency`: Salary currency.
*   `status`: Job status.
*   `posted_at`: Job posting timestamp.
*   `expires_at`: Job expiration timestamp.
*   `is_featured`: Whether job is featured.
*   `view_count`: Number of views.
*   `application_count`: Number of applications.

### JobLikeOutput

Output model for JobLike data from the database.

*   `like_id`: Like unique identifier.
*   `user_id`: User who liked the job.
*   `job_id`: Job that was liked.
*   `created_at`: Like creation timestamp.

### JobShareOutput

Output model for JobShare data from the database.

*   `share_id`: Share unique identifier.
*   `user_id`: User who shared the job (optional for anonymous).
*   `job_id`: Job that was shared.
*   `share_method`: Method used to share.
*   `shared_at`: Share timestamp.
*   `referral_code`: Referral tracking code.

### SavedJobOutput

Output model for SavedJob data from the database.

*   `saved_job_id`: Saved job unique identifier.
*   `user_id`: User who saved the job.
*   `job_id`: Job that was saved.
*   `saved_at`: Save timestamp.

### JobEngagementStatsOutput

Output model for job engagement statistics.

*   `job_id`: Job unique identifier.
*   `like_count`: Total number of likes.
*   `share_count`: Total number of shares.
*   `share_by_method`: Shares broken down by method.
*   `recent_likes`: Likes in last 7 days.
*   `recent_shares`: Shares in last 7 days.
*   `total_engagement`: Total engagement actions.

### PaginatedJobsOutput

Output model for paginated job lists.

*   `jobs`: List of jobs.
*   `total_count`: Total number of jobs available.
*   `limit`: Number of jobs per page.
*   `offset`: Starting offset.

## Relationships to SQL Models

These models are used to represent data retrieved from the database and do not directly map to any specific SQL models. They are used to structure the data returned by the API.
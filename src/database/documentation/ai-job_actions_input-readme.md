# job_actions_input.py Documentation

## Overview

This module defines Pydantic models for validating input parameters to job actions operations. These models ensure all external data passes through proper validation before reaching the business logic layer.

## Models

### JobActionInputBase

Base input model for job actions with common validation. Provides common validation patterns for job actions including UUID validation and string sanitization.

*   `strip_strings(cls, v)`: Strips whitespace from string inputs.

### LikeJobInput

Input validation model for job like operations.

*   `user_id`: JobSeeker profile user\_uid (must be valid UUID format).
*   `job_id`: Job ID to like (must be valid UUID format).

### UnlikeJobInput

Input validation model for job unlike operations.

*   `user_id`: JobSeeker profile user\_uid (must be valid UUID format).
*   `job_id`: Job ID to unlike (must be valid UUID format).

### SaveJobInput

Input validation model for job save operations.

*   `user_id`: JobSeeker profile user\_uid (must be valid UUID format).
*   `job_id`: Job ID to save (must be valid UUID format).

### UnsaveJobInput

Input validation model for job unsave operations.

*   `user_id`: JobSeeker profile user\_uid (must be valid UUID format).
*   `job_id`: Job ID to unsave (must be valid UUID format).

### ShareJobInput

Input validation model for job share operations.

*   `user_id`: JobSeeker profile user\_uid (optional for anonymous sharing).
*   `job_id`: Job ID to share (must be valid UUID format).
*   `share_method`: Method used to share the job.

### GetActionsStateInput

Input validation model for getting job actions state.

*   `user_id`: JobSeeker profile user\_uid (must be valid UUID format).
*   `job_id`: Job ID to get state for (must be valid UUID format).

### GetUserJobsInput

Input validation model for getting user's liked or saved jobs.

*   `user_id`: JobSeeker profile user\_uid (must be valid UUID format).
*   `limit`: Number of jobs to return (1-100).
*   `offset`: Starting offset for pagination.

### GetJobEngagementInput

Input validation model for getting job engagement statistics.

*   `job_id`: Job ID to get engagement stats for (must be valid UUID format).

## Relationships to SQL Models

These models are used for input validation and do not directly map to any specific SQL models. They are used in the controllers to validate the data received from the API requests before interacting with the database.
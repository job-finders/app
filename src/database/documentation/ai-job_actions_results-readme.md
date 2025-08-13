# job_actions_results.py Documentation

## Overview

This module defines Pydantic models for representing standardized result objects for job actions operations. These models provide consistent response formats across all job actions and ensure proper error handling and data serialization.

## Models

### JobActionErrorCode

An enumeration of error codes for job actions.

*   `VALIDATION_ERROR`: Input validation failed.
*   `USER_NOT_FOUND`: User not found.
*   `JOB_NOT_FOUND`: Job not found.
*   `ALREADY_LIKED`: Job already liked.
*   `ALREADY_SAVED`: Job already saved.
*   `LIKE_NOT_FOUND`: Like not found.
*   `SAVED_JOB_NOT_FOUND`: Saved job not found.
*   `INVALID_SHARE_METHOD`: Invalid share method.
*   `DATABASE_ERROR`: Database error.
*   `CACHE_ERROR`: Cache error.
*   `ANALYTICS_ERROR`: Analytics error.
*   `INTERNAL_ERROR`: Internal error.
* `RATE_LIMIT_EXCEEDED`: Rate limit exceeded
* `UNAUTHORIZED`: Unauthorized

### JobActionResult

Standardized result object for job actions operations.

*   `success`: Indicates whether the operation succeeded.
*   `message`: Human-readable result message.
*   `data`: Optional dictionary containing operation-specific data.
*   `error_code`: Optional error code for programmatic handling.
*   `timestamp`: UTC timestamp of result creation.

#### Methods

*   `success_result(message: str, data: Optional[Dict[str, Any]] = None) -> 'JobActionResult'`: Creates a successful result object.
*   `error_result(message: str, error_code: JobActionErrorCode, data: Optional[Dict[str, Any]] = None) -> 'JobActionResult'`: Creates an error result object.

### JobActionsStateResult

Result object for job actions state queries.

*   `success`: Indicates whether the state query succeeded.
*   `message`: Human-readable result message.
*   `actions_state`: Optional `JobActionsState` object with current state.
*   `error_code`: Optional error code if query failed.
*   `timestamp`: UTC timestamp of result creation.

#### Methods

*   `success_result(message: str, actions_state: JobActionsState) -> 'JobActionsStateResult'`: Creates a successful state result.
*   `error_result(message: str, error_code: JobActionErrorCode) -> 'JobActionsStateResult'`: Creates an error state result.

### JobEngagementResult

Result object for job engagement statistics.

*   `success`: Indicates whether the engagement query succeeded.
*   `message`: Human-readable result message.
*   `engagement_data`: Optional dictionary containing engagement metrics.
*   `error_code`: Optional error code if query failed.
*   `timestamp`: UTC timestamp of result creation.

#### Methods

*   `success_result(message: str, engagement_data: Dict[str, Any]) -> 'JobEngagementResult'`: Creates a successful engagement result.
*   `error_result(message: str, error_code: JobActionErrorCode) -> 'JobEngagementResult'`: Creates an error engagement result.

### JobListResult

Result object for job list queries (liked jobs, saved jobs, etc.).

*   `success`: Indicates whether the job list query succeeded.
*   `message`: Human-readable result message.
*   `jobs`: Optional list of job data dictionaries.
*   `total_count`: Total number of jobs available.
*   `limit`: Number of jobs per page.
*   `offset`: Starting offset.
*   `error_code`: Optional error code if query failed.
*   `timestamp`: UTC timestamp of result creation.

#### Methods

*   `success_result(message: str, jobs: List[Dict[str, Any]], total_count: int, limit: int, offset: int) -> 'JobListResult'`: Creates a successful job list result.
*   `error_result(message: str, error_code: JobActionErrorCode) -> 'JobListResult'`: Creates an error job list result.

## Relationships to SQL Models

These models are used as output models and do not directly map to any specific SQL models. They encapsulate the results of database queries and operations.
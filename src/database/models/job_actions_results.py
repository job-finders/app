"""
Job Actions Result Models

Standardized result objects for job actions operations.
These models provide consistent response formats across all job actions
and ensure proper error handling and data serialization.
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from src.database.constants import utc_time
from src.database.models.jobs_model import JobActionsState


class JobActionErrorCode(str, Enum):
    """Enumeration of error codes for job actions"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    ALREADY_LIKED = "ALREADY_LIKED"
    ALREADY_SAVED = "ALREADY_SAVED"
    LIKE_NOT_FOUND = "LIKE_NOT_FOUND"
    SAVED_JOB_NOT_FOUND = "SAVED_JOB_NOT_FOUND"
    INVALID_SHARE_METHOD = "INVALID_SHARE_METHOD"
    DATABASE_ERROR = "DATABASE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    ANALYTICS_ERROR = "ANALYTICS_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    UNAUTHORIZED = "UNAUTHORIZED"


class JobActionResult(BaseModel):
    """
    Standardized result object for job actions operations.
    
    This model provides a consistent response format for all job actions
    including success/failure status, human-readable messages, optional
    data payload, and error codes for client-side handling.
    
    Attributes:
        success: Boolean indicating whether the operation succeeded
        message: Human-readable message describing the result
        data: Optional dictionary containing operation-specific data
        error_code: Optional error code for programmatic error handling
        timestamp: UTC timestamp when the result was created
        
    Usage:
        # Success case
        result = JobActionResult(
            success=True,
            message="Job liked successfully",
            data={"like_id": "123", "like_count": 5}
        )
        
        # Error case
        result = JobActionResult(
            success=False,
            message="Job not found",
            error_code=JobActionErrorCode.JOB_NOT_FOUND
        )
    """
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Human-readable result message")
    data: Optional[Dict[str, Any]] = Field(None, description="Optional operation-specific data")
    error_code: Optional[JobActionErrorCode] = Field(None, description="Error code for programmatic handling")
    timestamp: datetime = Field(default_factory=utc_time, description="UTC timestamp of result creation")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    @classmethod
    def success_result(cls, message: str, data: Optional[Dict[str, Any]] = None) -> 'JobActionResult':
        """
        Create a successful result object.
        
        Args:
            message: Success message
            data: Optional data payload
            
        Returns:
            JobActionResult with success=True
        """
        return cls(success=True, message=message, data=data)

    @classmethod
    def error_result(cls, message: str, error_code: JobActionErrorCode,
                     data: Optional[Dict[str, Any]] = None) -> 'JobActionResult':
        """
        Create an error result object.
        
        Args:
            message: Error message
            error_code: Specific error code
            data: Optional error context data
            
        Returns:
            JobActionResult with success=False
        """
        return cls(success=False, message=message, error_code=error_code, data=data)


class JobActionsStateResult(BaseModel):
    """
    Result object for job actions state queries.
    
    This model encapsulates the result of querying the current state
    of job actions for a specific user and job combination.
    
    Attributes:
        success: Boolean indicating whether the query succeeded
        message: Human-readable message describing the result
        actions_state: Optional JobActionsState object with current state
        error_code: Optional error code for error cases
        timestamp: UTC timestamp when the result was created
    """
    success: bool = Field(..., description="Whether the state query succeeded")
    message: str = Field(..., description="Human-readable result message")
    actions_state: Optional[JobActionsState] = Field(None, description="Current job actions state")
    error_code: Optional[JobActionErrorCode] = Field(None, description="Error code if query failed")
    timestamp: datetime = Field(default_factory=utc_time, description="UTC timestamp of result creation")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    @classmethod
    def success_result(cls, message: str, actions_state: JobActionsState) -> 'JobActionsStateResult':
        """
        Create a successful state result.
        
        Args:
            message: Success message
            actions_state: Current job actions state
            
        Returns:
            JobActionsStateResult with success=True
        """
        return cls(success=True, message=message, actions_state=actions_state)

    @classmethod
    def error_result(cls, message: str, error_code: JobActionErrorCode) -> 'JobActionsStateResult':
        """
        Create an error state result.
        
        Args:
            message: Error message
            error_code: Specific error code
            
        Returns:
            JobActionsStateResult with success=False
        """
        return cls(success=False, message=message, error_code=error_code)


class JobEngagementResult(BaseModel):
    """
    Result object for job engagement statistics.
    
    This model encapsulates engagement metrics for a job including
    likes, shares, and recent activity statistics.
    
    Attributes:
        success: Boolean indicating whether the query succeeded
        message: Human-readable message describing the result
        engagement_data: Optional dictionary containing engagement metrics
        error_code: Optional error code for error cases
        timestamp: UTC timestamp when the result was created
    """
    success: bool = Field(..., description="Whether the engagement query succeeded")
    message: str = Field(..., description="Human-readable result message")
    engagement_data: Optional[Dict[str, Any]] = Field(None, description="Job engagement statistics")
    error_code: Optional[JobActionErrorCode] = Field(None, description="Error code if query failed")
    timestamp: datetime = Field(default_factory=utc_time, description="UTC timestamp of result creation")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    @classmethod
    def success_result(cls, message: str, engagement_data: Dict[str, Any]) -> 'JobEngagementResult':
        """
        Create a successful engagement result.
        
        Args:
            message: Success message
            engagement_data: Engagement statistics
            
        Returns:
            JobEngagementResult with success=True
        """
        return cls(success=True, message=message, engagement_data=engagement_data)

    @classmethod
    def error_result(cls, message: str, error_code: JobActionErrorCode) -> 'JobEngagementResult':
        """
        Create an error engagement result.
        
        Args:
            message: Error message
            error_code: Specific error code
            
        Returns:
            JobEngagementResult with success=False
        """
        return cls(success=False, message=message, error_code=error_code)


class JobListResult(BaseModel):
    """
    Result object for job list queries (liked jobs, saved jobs, etc.).
    
    This model encapsulates paginated job lists with metadata
    for proper pagination handling.
    
    Attributes:
        success: Boolean indicating whether the query succeeded
        message: Human-readable message describing the result
        jobs: Optional list of job data dictionaries
        total_count: Total number of jobs available
        limit: Number of jobs requested per page
        offset: Starting offset for pagination
        error_code: Optional error code for error cases
        timestamp: UTC timestamp when the result was created
    """
    success: bool = Field(..., description="Whether the job list query succeeded")
    message: str = Field(..., description="Human-readable result message")
    jobs: Optional[List[Dict[str, Any]]] = Field(None, description="List of job data")
    total_count: Optional[int] = Field(None, description="Total number of jobs available")
    limit: Optional[int] = Field(None, description="Number of jobs per page")
    offset: Optional[int] = Field(None, description="Starting offset for pagination")
    error_code: Optional[JobActionErrorCode] = Field(None, description="Error code if query failed")
    timestamp: datetime = Field(default_factory=utc_time, description="UTC timestamp of result creation")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    @classmethod
    def success_result(cls, message: str, jobs: List[Dict[str, Any]],
                       total_count: int, limit: int, offset: int) -> 'JobListResult':
        """
        Create a successful job list result.
        
        Args:
            message: Success message
            jobs: List of job data
            total_count: Total number of jobs
            limit: Jobs per page
            offset: Starting offset
            
        Returns:
            JobListResult with success=True
        """
        return cls(
            success=True,
            message=message,
            jobs=jobs,
            total_count=total_count,
            limit=limit,
            offset=offset
        )

    @classmethod
    def error_result(cls, message: str, error_code: JobActionErrorCode) -> 'JobListResult':
        """
        Create an error job list result.
        
        Args:
            message: Error message
            error_code: Specific error code
            
        Returns:
            JobListResult with success=False
        """
        return cls(success=False, message=message, error_code=error_code)

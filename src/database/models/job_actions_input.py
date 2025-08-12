"""
Job Actions Input Validation Models

Pydantic models for validating input parameters to job actions operations.
These models ensure all external data passes through proper validation
before reaching the business logic layer.

This module follows the established data flow pattern:
External Data → Pydantic Input Models → Business Logic → ORM Models → Database
"""

from typing import Optional
from pydantic import BaseModel, Field, validator
import uuid


class JobActionInputBase(BaseModel):
    """
    Base input model for job actions with common validation.
    
    This base class provides common validation patterns for job actions
    including UUID validation and string sanitization.
    """

    @validator('*', pre=True)
    def strip_strings(cls, v):
        """Strip whitespace from string inputs"""
        if isinstance(v, str):
            return v.strip()
        return v


class LikeJobInput(JobActionInputBase):
    """
    Input validation model for job like operations.
    
    Validates that user_id and job_id are properly formatted UUID strings
    and performs input sanitization to prevent injection attacks.
    
    Attributes:
        user_id: JobSeeker profile user_uid (must be valid UUID format)
        job_id: Job ID to like (must be valid UUID format)
    """
    user_id: str = Field(..., min_length=1, max_length=36, description="JobSeeker profile user_uid")
    job_id: str = Field(..., min_length=1, max_length=36, description="Job ID to like")

    @validator('user_id', 'job_id')
    def validate_uuid_format(cls, v):
        """Validate that IDs are properly formatted UUIDs"""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid UUID format: {v}")

    class Config:
        str_strip_whitespace = True
        validate_assignment = True


class UnlikeJobInput(JobActionInputBase):
    """
    Input validation model for job unlike operations.
    
    Validates input parameters for removing a job like with proper
    UUID format validation and input sanitization.
    """
    user_id: str = Field(..., min_length=1, max_length=36, description="JobSeeker profile user_uid")
    job_id: str = Field(..., min_length=1, max_length=36, description="Job ID to unlike")

    @validator('user_id', 'job_id')
    def validate_uuid_format(cls, v):
        """Validate that IDs are properly formatted UUIDs"""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid UUID format: {v}")

    class Config:
        str_strip_whitespace = True
        validate_assignment = True


class SaveJobInput(JobActionInputBase):
    """
    Input validation model for job save operations.
    
    Validates input parameters for saving a job with proper UUID
    format validation and input sanitization.
    """
    user_id: str = Field(..., min_length=1, max_length=36, description="JobSeeker profile user_uid")
    job_id: str = Field(..., min_length=1, max_length=36, description="Job ID to save")

    @validator('user_id', 'job_id')
    def validate_uuid_format(cls, v):
        """Validate that IDs are properly formatted UUIDs"""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid UUID format: {v}")

    class Config:
        str_strip_whitespace = True
        validate_assignment = True


class UnsaveJobInput(JobActionInputBase):
    """
    Input validation model for job unsave operations.
    
    Validates input parameters for removing a saved job with proper
    UUID format validation and input sanitization.
    """
    user_id: str = Field(..., min_length=1, max_length=36, description="JobSeeker profile user_uid")
    job_id: str = Field(..., min_length=1, max_length=36, description="Job ID to unsave")

    @validator('user_id', 'job_id')
    def validate_uuid_format(cls, v):
        """Validate that IDs are properly formatted UUIDs"""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid UUID format: {v}")

    class Config:
        str_strip_whitespace = True
        validate_assignment = True


class ShareJobInput(JobActionInputBase):
    """
    Input validation model for job share operations.
    
    Validates input parameters for sharing a job including optional
    user authentication and share method validation.
    """
    user_id: Optional[str] = Field(None, min_length=1, max_length=36,
                                   description="JobSeeker profile user_uid (optional for anonymous sharing)")
    job_id: str = Field(..., min_length=1, max_length=36, description="Job ID to share")
    share_method: str = Field(..., min_length=1, max_length=20, description="Method used to share the job")

    @validator('user_id', 'job_id')
    def validate_uuid_format(cls, v):
        """Validate that IDs are properly formatted UUIDs"""
        if v is None:  # user_id is optional
            return v
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid UUID format: {v}")

    @validator('share_method')
    def validate_share_method(cls, v):
        """Validate that share method is one of the allowed values"""
        from src.database.models.jobs_model import ShareMethodEnum
        try:
            ShareMethodEnum(v)
            return v
        except ValueError:
            valid_methods = [method.value for method in ShareMethodEnum]
            raise ValueError(f"Invalid share method. Must be one of: {', '.join(valid_methods)}")

    class Config:
        str_strip_whitespace = True
        validate_assignment = True


class GetActionsStateInput(JobActionInputBase):
    """
    Input validation model for getting job actions state.
    
    Validates input parameters for retrieving the current state
    of job actions for a specific user and job combination.
    """
    user_id: str = Field(..., min_length=1, max_length=36, description="JobSeeker profile user_uid")
    job_id: str = Field(..., min_length=1, max_length=36, description="Job ID to get state for")

    @validator('user_id', 'job_id')
    def validate_uuid_format(cls, v):
        """Validate that IDs are properly formatted UUIDs"""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid UUID format: {v}")

    class Config:
        str_strip_whitespace = True
        validate_assignment = True


class GetUserJobsInput(JobActionInputBase):
    """
    Input validation model for getting user's liked or saved jobs.
    
    Validates input parameters for retrieving paginated lists of
    jobs that a user has liked or saved.
    """
    user_id: str = Field(..., min_length=1, max_length=36, description="JobSeeker profile user_uid")
    limit: int = Field(20, ge=1, le=100, description="Number of jobs to return (1-100)")
    offset: int = Field(0, ge=0, description="Starting offset for pagination")

    @validator('user_id')
    def validate_uuid_format(cls, v):
        """Validate that user_id is properly formatted UUID"""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid UUID format: {v}")

    class Config:
        str_strip_whitespace = True
        validate_assignment = True


class GetJobEngagementInput(JobActionInputBase):
    """
    Input validation model for getting job engagement statistics.
    
    Validates input parameters for retrieving comprehensive
    engagement statistics for a specific job.
    """
    job_id: str = Field(..., min_length=1, max_length=36, description="Job ID to get engagement stats for")

    @validator('job_id')
    def validate_uuid_format(cls, v):
        """Validate that job_id is properly formatted UUID"""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid UUID format: {v}")

    class Config:
        str_strip_whitespace = True
        validate_assignment = True

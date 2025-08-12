"""
Job Actions Output Models

Pydantic models for converting ORM results to validated business objects.
These models ensure all database reads are converted to Pydantic models
before business logic processing.

This module follows the established data flow pattern:
Database → ORM Models → Pydantic Output Models → Business Logic
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, computed_field
from src.database.constants import utc_time


class JobSeekerProfileOutput(BaseModel):
    """
    Output model for JobSeeker profile data from database.
    
    Converts JobSeekerProfileORM to validated Pydantic model for
    business logic processing with proper type validation and
    computed properties.
    """
    user_uid: str = Field(..., description="User unique identifier")
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    email: Optional[str] = Field(None, description="User's email address")
    phone: Optional[str] = Field(None, description="User's phone number")
    is_active: bool = Field(default=True, description="Whether profile is active")
    created_at: datetime = Field(..., description="Profile creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    @computed_field
    @property
    def full_name(self) -> str:
        """Computed full name from first and last name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or "Unknown User"

    @computed_field
    @property
    def is_profile_complete(self) -> bool:
        """Check if profile has minimum required information"""
        return bool(self.first_name and self.last_name and self.email)


class JobOutput(BaseModel):
    """
    Output model for Job data from database.
    
    Converts JobsORM to validated Pydantic model for business logic
    processing with computed properties and proper validation.
    """
    job_id: str = Field(..., description="Job unique identifier")
    title: str = Field(..., description="Job title")
    description: Optional[str] = Field(None, description="Job description")
    company_id: Optional[str] = Field(None, description="Associated company ID")
    position_type: Optional[str] = Field(None, description="Position type (full-time, part-time, etc.)")
    remote_policy: Optional[str] = Field(None, description="Remote work policy")
    city: Optional[str] = Field(None, description="Job location city")
    province: Optional[str] = Field(None, description="Job location province")
    country: Optional[str] = Field(None, description="Job location country")
    salary_min: Optional[float] = Field(None, description="Minimum salary")
    salary_max: Optional[float] = Field(None, description="Maximum salary")
    salary_currency: str = Field(default="ZAR", description="Salary currency")
    status: str = Field(default="active", description="Job status")
    posted_at: datetime = Field(..., description="Job posting timestamp")
    expires_at: Optional[datetime] = Field(None, description="Job expiration timestamp")
    is_featured: bool = Field(default=False, description="Whether job is featured")
    view_count: int = Field(default=0, description="Number of views")
    application_count: int = Field(default=0, description="Number of applications")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    @computed_field
    @property
    def location(self) -> str:
        """Computed location string"""
        parts = [self.city, self.province, self.country]
        return ", ".join(part for part in parts if part)

    @computed_field
    @property
    def salary_display(self) -> str:
        """Computed salary display string"""
        if self.salary_min and self.salary_max:
            return f"{self.salary_currency} {self.salary_min:,.0f} - {self.salary_max:,.0f}"
        elif self.salary_min:
            return f"{self.salary_currency} {self.salary_min:,.0f}+"
        elif self.salary_max:
            return f"{self.salary_currency} up to {self.salary_max:,.0f}"
        return "Salary not disclosed"

    @computed_field
    @property
    def is_active(self) -> bool:
        """Check if job is currently active"""
        if self.status != "active":
            return False
        if self.expires_at:
            return self.expires_at > utc_time()
        return True

    @computed_field
    @property
    def days_since_posted(self) -> int:
        """Calculate days since job was posted"""
        return (utc_time() - self.posted_at).days


class JobLikeOutput(BaseModel):
    """
    Output model for JobLike data from database.
    
    Converts JobLikeORM to validated Pydantic model with
    proper type validation and computed properties.
    """
    like_id: str = Field(..., description="Like unique identifier")
    user_id: str = Field(..., description="User who liked the job")
    job_id: str = Field(..., description="Job that was liked")
    created_at: datetime = Field(..., description="Like creation timestamp")

    # Optional related data
    job: Optional[JobOutput] = Field(None, description="Related job data")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    @computed_field
    @property
    def is_recent(self) -> bool:
        """Check if like was created within last 24 hours"""
        return (utc_time() - self.created_at).total_seconds() < 86400


class JobShareOutput(BaseModel):
    """
    Output model for JobShare data from database.
    
    Converts JobShareORM to validated Pydantic model with
    proper validation and computed properties.
    """
    share_id: str = Field(..., description="Share unique identifier")
    user_id: Optional[str] = Field(None, description="User who shared the job (optional for anonymous)")
    job_id: str = Field(..., description="Job that was shared")
    share_method: str = Field(..., description="Method used to share")
    shared_at: datetime = Field(..., description="Share timestamp")
    referral_code: Optional[str] = Field(None, description="Referral tracking code")

    # Optional related data
    job: Optional[JobOutput] = Field(None, description="Related job data")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    @computed_field
    @property
    def is_anonymous(self) -> bool:
        """Check if share was anonymous"""
        return self.user_id is None

    @computed_field
    @property
    def is_social_media(self) -> bool:
        """Check if share was via social media"""
        social_methods = {"linkedin", "twitter", "facebook"}
        return self.share_method.lower() in social_methods


class SavedJobOutput(BaseModel):
    """
    Output model for SavedJob data from database.
    
    Converts SavedJobORM to validated Pydantic model with
    proper validation and computed properties.
    """
    saved_job_id: str = Field(..., description="Saved job unique identifier")
    user_id: str = Field(..., description="User who saved the job")
    job_id: str = Field(..., description="Job that was saved")
    saved_at: datetime = Field(..., description="Save timestamp")

    # Optional related data
    job: Optional[JobOutput] = Field(None, description="Related job data")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    @computed_field
    @property
    def days_since_saved(self) -> int:
        """Calculate days since job was saved"""
        return (utc_time() - self.saved_at).days


class JobEngagementStatsOutput(BaseModel):
    """
    Output model for job engagement statistics.
    
    Aggregates engagement data from multiple sources into
    a comprehensive statistics object.
    """
    job_id: str = Field(..., description="Job unique identifier")
    like_count: int = Field(default=0, description="Total number of likes")
    share_count: int = Field(default=0, description="Total number of shares")
    share_by_method: Dict[str, int] = Field(default_factory=dict, description="Shares broken down by method")
    recent_likes: int = Field(default=0, description="Likes in last 7 days")
    recent_shares: int = Field(default=0, description="Shares in last 7 days")
    total_engagement: int = Field(default=0, description="Total engagement actions")

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def engagement_score(self) -> float:
        """Calculate weighted engagement score (likes weighted more than shares)"""
        return (self.like_count * 2.0) + self.share_count

    @computed_field
    @property
    def recent_activity_score(self) -> float:
        """Calculate recent activity score"""
        return (self.recent_likes * 2.0) + self.recent_shares

    @computed_field
    @property
    def most_popular_share_method(self) -> Optional[str]:
        """Get the most popular share method"""
        if not self.share_by_method:
            return None
        return max(self.share_by_method.items(), key=lambda x: x[1])[0]


class PaginatedJobsOutput(BaseModel):
    """
    Output model for paginated job lists.
    
    Provides structured pagination metadata along with
    job data for consistent API responses.
    """
    jobs: List[JobOutput] = Field(default_factory=list, description="List of jobs")
    total_count: int = Field(default=0, description="Total number of jobs available")
    limit: int = Field(..., description="Number of jobs per page")
    offset: int = Field(..., description="Starting offset")
    has_more: bool = Field(default=False, description="Whether more jobs are available")

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def current_page(self) -> int:
        """Calculate current page number (1-based)"""
        return (self.offset // self.limit) + 1

    @computed_field
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages"""
        if self.limit == 0:
            return 0
        return (self.total_count + self.limit - 1) // self.limit

    @computed_field
    @property
    def next_offset(self) -> Optional[int]:
        """Calculate next offset for pagination"""
        next_offset = self.offset + self.limit
        return next_offset if next_offset < self.total_count else None

    @computed_field
    @property
    def prev_offset(self) -> Optional[int]:
        """Calculate previous offset for pagination"""
        prev_offset = self.offset - self.limit
        return prev_offset if prev_offset >= 0 else None

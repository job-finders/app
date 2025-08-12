"""
Job Actions Service

Service layer implementation for job actions business logic following the
established service interface pattern. This service encapsulates all business
logic for job interactions including validation, persistence, and business
rule enforcement.

This service follows the established architecture patterns:
- Inherits from ServiceInterface for consistent API
- Uses execute() method pattern for dynamic method dispatch
- Implements comprehensive error handling and logging
- Returns standardized result objects
- Integrates with caching and analytics layers
"""

import inspect
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone

from sqlalchemy import func, and_
from sqlalchemy.exc import IntegrityError, DatabaseError
from sqlalchemy.orm import joinedload
from pydantic import ValidationError

from src.services.billing.schemas_interfaces import BillingServiceInterface
from src.database.models import (
    JobLike, JobShare, JobActionsState, SavedJob, ShareMethodEnum
)
from src.database.models.job_actions_results import (
    JobActionResult, JobActionsStateResult, JobEngagementResult,
    JobListResult, JobActionErrorCode
)
from src.database.models.job_actions_input import (
    LikeJobInput, UnlikeJobInput, SaveJobInput, UnsaveJobInput,
    ShareJobInput, GetActionsStateInput, GetUserJobsInput, GetJobEngagementInput
)
from src.database.models.job_actions_output import (
    JobSeekerProfileOutput, JobOutput, JobLikeOutput, JobShareOutput,
    SavedJobOutput, JobEngagementStatsOutput, PaginatedJobsOutput
)
from src.database import (
    JobLikeORM, JobShareORM, JobsORM, JobSeekerProfileORM, SavedJobORM
)
from src.database.constants import utc_time
from src.cache.job_actions_cache import job_actions_cache
from src.cache.job_actions_cache_manager import job_actions_cache_manager
from src.utils.route_helpers import get_service


class JobActionsService(BillingServiceInterface):
    """
    Service for job actions business logic implementation.
    
    This service encapsulates all business logic for job interactions including
    validation, persistence, and business rule enforcement. It follows the
    established service interface pattern for consistency and provides a
    unified API for job actions operations.
    
    Architecture Integration:
        - Inherits from BillingServiceInterface for consistent service patterns
        - Uses execute() method for dynamic method dispatch
        - Implements comprehensive error handling and logging
        - Returns standardized result objects for consistent API responses
        - Integrates with caching layer for performance optimization
        - Provides analytics tracking for business intelligence
    
    Dependencies:
        - Database session factory for data persistence
        - Cache manager for performance optimization
        - Analytics service for event tracking
        - Logging system for audit trail and debugging
    
    Business Rules:
        - All job actions require valid job and user validation
        - Duplicate actions are prevented with appropriate error responses
        - Anonymous sharing is supported for better user experience
        - All operations are transactional with proper rollback handling
        - Cache invalidation is performed for data consistency
    """

    def __init__(self, session_factory):
        """
        Initialize JobActionsService with dependencies.
        
        Args:
            session_factory: Callable that returns database session instances
        """
        super().__init__()
        self.session_factory = session_factory
        self.cache_manager = job_actions_cache_manager
        self.analytics_service = None  # Will be initialized when needed

        # Define the interface map for dynamic method execution
        self.__interface_map: Dict[str, Callable] = {
            'like_job': self._like_job,
            'unlike_job': self._unlike_job,
            'save_job': self._save_job,
            'unsave_job': self._unsave_job,
            'share_job': self._share_job,
            'get_actions_state': self._get_actions_state,
            'get_user_liked_jobs': self._get_user_liked_jobs,
            'get_user_saved_jobs': self._get_user_saved_jobs,
            'get_job_engagement_stats': self._get_job_engagement_stats,
            'interface_schema': self._interface_schema,
            'describe_actions': self._describe_actions
        }

        self.logger = get_service('logger')()(self.__class__.__name__)

    def _get_analytics_service(self):
        """Lazy initialization of analytics service to avoid circular imports"""
        if not self.analytics_service:
            try:
                self.analytics_service = get_service('job_actions_analytics')()
            except Exception as e:
                self.logger.warning(f"Failed to initialize analytics service: {e}")
        return self.analytics_service

    async def _like_job(self, user_id: str, job_id: str) -> JobActionResult:
        """
        Like a job for a user with comprehensive validation, tracking, and monitoring.
        
        This method follows the proper data flow pattern with comprehensive error handling,
        security logging, performance monitoring, and audit trail capabilities:
        1. External data → Pydantic Input Model validation with security logging
        2. Database queries → ORM Models → Pydantic Output Models with performance tracking
        3. Business logic processing with validated models and audit logging
        4. Standardized result object return with comprehensive error handling
        
        Args:
            user_id: JobSeeker profile user_uid (will be validated)
            job_id: Job ID to like (will be validated)
            
        Returns:
            JobActionResult: Standardized result object with success status,
                           message, and data containing like_id and like_count
                           
        Security & Monitoring:
            - Input validation failures logged as security events
            - Performance metrics tracked for optimization
            - Audit trail maintained for compliance
            - Error patterns monitored for threat detection
        """
        # Start performance tracking
        with job_actions_performance_logger.track_operation(
                'like_job',
                user_id=user_id,
                job_id=job_id,
                metadata={'operation_type': 'user_action'}
        ) as perf_context:

            try:
                # Step 1: Validate external input through Pydantic model with security logging
                try:
                    input_data = LikeJobInput(user_id=user_id, job_id=job_id)
                except ValidationError as e:
                    # Log input validation failure as security event
                    job_actions_security_logger.log_input_validation_failure(
                        user_id=user_id,
                        action='like_job',
                        validation_errors={'pydantic_errors': str(e)},
                        input_data={'user_id': user_id, 'job_id': job_id}
                    )

                    self.logger.warning(
                        f"Input validation failed in _like_job: {e}",
                        extra={
                            'user_id': user_id,
                            'job_id': job_id,
                            'validation_errors': str(e),
                            'security_event': True
                        }
                    )

                    return JobActionResult.error_result(
                        message=f"Invalid input parameters: {str(e)}",
                        error_code=JobActionErrorCode.VALIDATION_ERROR
                    )

                with self.session_factory() as session:
                    # Track database query performance
                    perf_context['increment_db_queries']()

                    # Step 2: Database reads → ORM → Pydantic Output Models with performance tracking

                    # Validate user exists and convert to Pydantic model
                    user_profile_orm = session.query(JobSeekerProfileORM).filter_by(user_uid=input_data.user_id).first()
                    perf_context['increment_db_queries']()

                    if not user_profile_orm:
                        # Log authorization violation (user not found)
                        job_actions_security_logger.log_authorization_violation(
                            user_id=input_data.user_id,
                            action='like_job',
                            resource=f'job:{input_data.job_id}',
                            required_permission='valid_jobseeker_profile'
                        )

                        self.logger.warning(
                            f"JobSeeker profile not found for like operation: {input_data.user_id}",
                            extra={
                                'user_id': input_data.user_id,
                                'job_id': input_data.job_id,
                                'security_event': True,
                                'event_type': 'user_not_found'
                            }
                        )

                        return JobActionResult.error_result(
                            message="JobSeeker profile not found",
                            error_code=JobActionErrorCode.USER_NOT_FOUND
                        )

                    # Convert ORM to Pydantic output model for business logic
                    user_profile = JobSeekerProfileOutput.model_validate(user_profile_orm)

                    # Validate job exists and convert to Pydantic model
                    job_orm = session.query(JobsORM).filter_by(job_id=input_data.job_id).first()
                    perf_context['increment_db_queries']()

                    if not job_orm:
                        self.logger.warning(
                            f"Job not found for like operation: {input_data.job_id}",
                            extra={
                                'user_id': input_data.user_id,
                                'job_id': input_data.job_id,
                                'user_name': user_profile.full_name,
                                'event_type': 'job_not_found'
                            }
                        )

                        return JobActionResult.error_result(
                            message="Job not found",
                            error_code=JobActionErrorCode.JOB_NOT_FOUND
                        )

                    # Convert ORM to Pydantic output model for business logic
                    job = JobOutput.model_validate(job_orm)

                    # Step 3: Business logic with validated Pydantic models and security checks

                    # Check if job is active using Pydantic computed property
                    if not job.is_active:
                        self.logger.warning(
                            f"Attempt to like inactive job: {job.job_id}",
                            extra={
                                'user_id': input_data.user_id,
                                'job_id': input_data.job_id,
                                'job_title': job.title,
                                'job_status': job.status,
                                'user_name': user_profile.full_name,
                                'event_type': 'inactive_job_access'
                            }
                        )

                        return JobActionResult.error_result(
                            message="Cannot like inactive or expired job",
                            error_code=JobActionErrorCode.JOB_NOT_FOUND
                        )

                    # Check for existing like to prevent duplicates
                    existing_like_orm = session.query(JobLikeORM).filter_by(
                        user_id=input_data.user_id, job_id=input_data.job_id
                    ).first()
                    perf_context['increment_db_queries']()

                    if existing_like_orm:
                        # Convert to Pydantic model for consistent response
                        existing_like = JobLikeOutput.model_validate(existing_like_orm)

                        # Log duplicate attempt (potential abuse)
                        job_actions_security_logger.log_security_event(
                            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                            severity=SecuritySeverity.LOW,
                            user_id=input_data.user_id,
                            job_id=input_data.job_id,
                            action='duplicate_like_attempt',
                            details={
                                'existing_like_id': existing_like.like_id,
                                'original_like_date': existing_like.created_at.isoformat(),
                                'user_name': user_profile.full_name,
                                'job_title': job.title
                            }
                        )

                        self.logger.info(
                            f"Duplicate like attempt: user {user_profile.full_name} ({input_data.user_id}) "
                            f"attempted to re-like job '{job.title}' ({input_data.job_id})",
                            extra={
                                'user_id': input_data.user_id,
                                'job_id': input_data.job_id,
                                'existing_like_id': existing_like.like_id,
                                'event_type': 'duplicate_like_attempt'
                            }
                        )

                        return JobActionResult.error_result(
                            message="Job already liked by user",
                            error_code=JobActionErrorCode.ALREADY_LIKED,
                            data={
                                "existing_like_id": existing_like.like_id,
                                "liked_at": existing_like.created_at.isoformat()
                            }
                        )

                    # Step 4: Create new like using Pydantic model for validation
                    job_like = JobLike(user_id=input_data.user_id, job_id=input_data.job_id)
                    like_orm = JobLikeORM(**job_like.model_dump())

                    session.add(like_orm)
                    session.commit()
                    perf_context['increment_db_queries']()

                    # Convert created like to Pydantic output model
                    session.refresh(like_orm)
                    created_like = JobLikeOutput.model_validate(like_orm)

                    # Get updated like count
                    like_count = session.query(func.count(JobLikeORM.like_id)).filter_by(
                        job_id=input_data.job_id).scalar()
                    perf_context['increment_db_queries']()

                    # Step 5: Cache invalidation and analytics (side effects)

                    # Invalidate related cache entries
                    try:
                        self.cache_manager.invalidate_user_action_cache(input_data.user_id, input_data.job_id)
                        self.cache_manager.invalidate_job_engagement_stats(input_data.job_id)
                        perf_context['set_cache_hit'](False)  # Cache invalidation
                    except Exception as cache_error:
                        self.logger.warning(f"Cache invalidation failed for like: {cache_error}")

                    # Track analytics event with validated data
                    analytics_service = self._get_analytics_service()
                    if analytics_service:
                        try:
                            await analytics_service.track_job_action(
                                event_type="job_like",
                                user_id=input_data.user_id,
                                job_id=input_data.job_id,
                                metadata={
                                    "like_id": created_like.like_id,
                                    "job_title": job.title,
                                    "user_name": user_profile.full_name,
                                    "job_location": job.location
                                }
                            )
                        except Exception as analytics_error:
                            # Analytics errors are non-blocking
                            self.logger.warning(f"Analytics tracking failed for like: {analytics_error}")

                    # Log audit trail for compliance
                    job_actions_security_logger.log_audit_trail(
                        user_id=input_data.user_id,
                        action='like_job',
                        resource=f'job:{input_data.job_id}',
                        result='success',
                        job_id=input_data.job_id,
                        details={
                            'like_id': created_like.like_id,
                            'job_title': job.title,
                            'user_name': user_profile.full_name,
                            'like_count': like_count
                        }
                    )

                    # Log successful operation with validated data
                    self.logger.info(
                        f"Job liked successfully: user {user_profile.full_name} ({input_data.user_id}) "
                        f"liked job '{job.title}' ({input_data.job_id})",
                        extra={
                            'user_id': input_data.user_id,
                            'job_id': input_data.job_id,
                            'like_id': created_like.like_id,
                            'job_title': job.title,
                            'user_name': user_profile.full_name,
                            'like_count': like_count,
                            'event_type': 'job_like_success'
                        }
                    )

                    # Return standardized success result with validated data
                    return JobActionResult.success_result(
                        message="Job liked successfully",
                        data={
                            "like_id": created_like.like_id,
                            "like_count": like_count,
                            "user_id": input_data.user_id,
                            "job_id": input_data.job_id,
                            "job_title": job.title,
                            "liked_at": created_like.created_at.isoformat()
                        }
                    )

            except ValidationError as e:
                # Pydantic validation errors (should be caught earlier but safety net)
                job_actions_security_logger.log_input_validation_failure(
                    user_id=user_id,
                    action='like_job',
                    validation_errors={'validation_error': str(e)},
                    input_data={'user_id': user_id, 'job_id': job_id}
                )

                self.logger.warning(
                    f"Validation error in _like_job: {e}",
                    extra={
                        'user_id': user_id,
                        'job_id': job_id,
                        'validation_error': str(e),
                        'security_event': True
                    }
                )

                return JobActionResult.error_result(
                    message="Data validation failed",
                    error_code=JobActionErrorCode.VALIDATION_ERROR
                )

            except IntegrityError as e:
                # Database constraint violations (e.g., duplicate key)
                job_actions_security_logger.log_security_event(
                    event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                    severity=SecuritySeverity.MEDIUM,
                    user_id=user_id,
                    job_id=job_id,
                    action='like_job_integrity_violation',
                    details={'integrity_error': str(e)}
                )

                self.logger.error(
                    f"Database integrity error in _like_job: {e}",
                    extra={
                        'user_id': user_id,
                        'job_id': job_id,
                        'integrity_error': str(e),
                        'security_event': True
                    }
                )

                return JobActionResult.error_result(
                    message="Database constraint violation - possible duplicate like",
                    error_code=JobActionErrorCode.ALREADY_LIKED
                )

            except DatabaseError as e:
                # Database connectivity or operation errors
                self.logger.error(
                    f"Database error in _like_job: {e}",
                    extra={
                        'user_id': user_id,
                        'job_id': job_id,
                        'database_error': str(e),
                        'error_type': 'database_connectivity'
                    }
                )

                return JobActionResult.error_result(
                    message="Database operation failed",
                    error_code=JobActionErrorCode.DATABASE_ERROR
                )

            except Exception as e:
                # Unexpected errors - log as critical security event
                job_actions_security_logger.log_security_event(
                    event_type=SecurityEventType.PERFORMANCE_ANOMALY,
                    severity=SecuritySeverity.HIGH,
                    user_id=user_id,
                    job_id=job_id,
                    action='like_job_unexpected_error',
                    details={'unexpected_error': str(e), 'error_type': type(e).__name__}
                )

                self.logger.error(
                    f"Unexpected error in _like_job: {e}",
                    extra={
                        'user_id': user_id,
                        'job_id': job_id,
                        'unexpected_error': str(e),
                        'error_type': type(e).__name__,
                        'security_event': True
                    },
                    exc_info=True
                )

                return JobActionResult.error_result(
                    message="Internal server error occurred",
                    error_code=JobActionErrorCode.INTERNAL_ERROR
                )

    async def _unlike_job(self, user_id: str, job_id: str) -> JobActionResult:
        """
        Remove a like from a job with comprehensive validation and tracking.
        
        This method follows the proper data flow pattern:
        1. External data → Pydantic Input Model validation
        2. Database queries → ORM Models → Pydantic Output Models
        3. Business logic processing with validated models
        4. Standardized result object return
        
        Args:
            user_id: JobSeeker profile user_uid (will be validated)
            job_id: Job ID to unlike (will be validated)
            
        Returns:
            JobActionResult: Standardized result with success status and updated like_count
        """
        try:
            # Step 1: Validate external input through Pydantic model
            try:
                input_data = UnlikeJobInput(user_id=user_id, job_id=job_id)
            except ValidationError as e:
                self.logger.warning(f"Input validation failed in _unlike_job: {e}")
                return JobActionResult.error_result(
                    message=f"Invalid input parameters: {str(e)}",
                    error_code=JobActionErrorCode.VALIDATION_ERROR
                )

            with self.session_factory() as session:
                # Step 2: Find existing like and convert to Pydantic model
                existing_like_orm = session.query(JobLikeORM).filter_by(
                    user_id=input_data.user_id, job_id=input_data.job_id
                ).first()

                if not existing_like_orm:
                    self.logger.info(f"Like not found for unlike: user {input_data.user_id}, job {input_data.job_id}")
                    return JobActionResult.error_result(
                        message="Like not found - cannot unlike job that wasn't liked",
                        error_code=JobActionErrorCode.LIKE_NOT_FOUND
                    )

                # Convert ORM to Pydantic output model for business logic
                existing_like = JobLikeOutput.model_validate(existing_like_orm)

                # Step 3: Business logic validation with Pydantic model

                # Verify the like belongs to the requesting user (additional security)
                if existing_like.user_id != input_data.user_id:
                    self.logger.warning(
                        f"User {input_data.user_id} attempted to unlike job {input_data.job_id} liked by {existing_like.user_id}")
                    return JobActionResult.error_result(
                        message="Cannot unlike job liked by another user",
                        error_code=JobActionErrorCode.UNAUTHORIZED
                    )

                # Step 4: Remove the like
                session.delete(existing_like_orm)
                session.commit()

                # Get updated like count
                like_count = session.query(func.count(JobLikeORM.like_id)).filter_by(job_id=input_data.job_id).scalar()

                # Step 5: Cache invalidation and analytics (side effects)

                # Invalidate related cache entries
                self.cache_manager.invalidate_user_action_cache(input_data.user_id, input_data.job_id)
                self.cache_manager.invalidate_job_engagement_stats(input_data.job_id)

                # Track analytics event with validated data
                analytics_service = self._get_analytics_service()
                if analytics_service:
                    try:
                        await analytics_service.track_job_action(
                            event_type="job_unlike",
                            user_id=input_data.user_id,
                            job_id=input_data.job_id,
                            metadata={
                                "like_count": like_count,
                                "original_like_id": existing_like.like_id,
                                "like_duration_days": existing_like.created_at and (
                                            utc_time() - existing_like.created_at).days
                            }
                        )
                    except Exception as analytics_error:
                        self.logger.warning(f"Analytics tracking failed for unlike: {analytics_error}")

                # Log successful operation with validated data
                self.logger.info(
                    f"Job unliked successfully: user {input_data.user_id} "
                    f"unliked job {input_data.job_id}, new like count: {like_count}"
                )

                # Return standardized success result with validated data
                return JobActionResult.success_result(
                    message="Job unliked successfully",
                    data={
                        "like_count": like_count,
                        "user_id": input_data.user_id,
                        "job_id": input_data.job_id,
                        "removed_like_id": existing_like.like_id,
                        "unliked_at": utc_time().isoformat()
                    }
                )

        except ValidationError as e:
            # Pydantic validation errors (should be caught earlier but safety net)
            self.logger.warning(f"Validation error in _unlike_job: {e}")
            return JobActionResult.error_result(
                message="Data validation failed",
                error_code=JobActionErrorCode.VALIDATION_ERROR
            )

        except DatabaseError as e:
            # Database connectivity or operation errors
            self.logger.error(f"Database error in _unlike_job: {e}")
            return JobActionResult.error_result(
                message="Database operation failed",
                error_code=JobActionErrorCode.DATABASE_ERROR
            )

        except Exception as e:
            # Unexpected errors
            self.logger.error(f"Unexpected error in _unlike_job: {e}", exc_info=True)
            return JobActionResult.error_result(
                message="Internal server error occurred",
                error_code=JobActionErrorCode.INTERNAL_ERROR
            )

    def _validate_user_and_job_ids(self, user_id: str, job_id: str) -> bool:
        """
        Validate that user_id and job_id are not empty strings.
        
        Args:
            user_id: User ID to validate
            job_id: Job ID to validate
            
        Returns:
            bool: True if both IDs are valid, False otherwise
        """
        return bool(user_id and user_id.strip() and job_id and job_id.strip())

    async def _save_job(self, user_id: str, job_id: str) -> JobActionResult:
        """
        Save a job for a user with comprehensive validation and tracking.
        
        Args:
            user_id: JobSeeker profile user_uid
            job_id: Job ID to save
            
        Returns:
            JobActionResult: Standardized result with success status and saved_job_id
        """
        try:
            if not self._validate_user_and_job_ids(user_id, job_id):
                return JobActionResult.error_result(
                    message="Invalid user or job ID parameters",
                    error_code=JobActionErrorCode.VALIDATION_ERROR
                )

            with self.session_factory() as session:
                # Validate user exists
                user_profile = session.query(JobSeekerProfileORM).filter_by(user_uid=user_id).first()
                if not user_profile:
                    self.logger.warning(f"JobSeeker profile not found for save operation: {user_id}")
                    return JobActionResult.error_result(
                        message="JobSeeker profile not found",
                        error_code=JobActionErrorCode.USER_NOT_FOUND
                    )

                # Validate job exists
                job = session.query(JobsORM).filter_by(job_id=job_id).first()
                if not job:
                    self.logger.warning(f"Job not found for save operation: {job_id}")
                    return JobActionResult.error_result(
                        message="Job not found",
                        error_code=JobActionErrorCode.JOB_NOT_FOUND
                    )

                # Check for existing save to prevent duplicates
                existing_save = session.query(SavedJobORM).filter_by(
                    user_id=user_id, job_id=job_id
                ).first()

                if existing_save:
                    self.logger.info(f"Duplicate save attempt: user {user_id}, job {job_id}")
                    return JobActionResult.error_result(
                        message="Job already saved by user",
                        error_code=JobActionErrorCode.ALREADY_SAVED,
                        data={"existing_saved_job_id": existing_save.saved_job_id}
                    )

                # Create new saved job using Pydantic model for validation
                saved_job = SavedJob(user_id=user_id, job_id=job_id)
                saved_job_orm = SavedJobORM(**saved_job.model_dump())

                session.add(saved_job_orm)
                session.commit()

                # Invalidate related cache entries
                self.cache_manager.invalidate_job_actions_state(user_id, job_id)
                self.cache_manager.invalidate_user_liked_jobs(user_id)

                # Track analytics event
                analytics_service = self._get_analytics_service()
                if analytics_service:
                    try:
                        await analytics_service.track_job_action(
                            event_type="job_save",
                            user_id=user_id,
                            job_id=job_id,
                            metadata={"saved_job_id": saved_job_orm.saved_job_id}
                        )
                    except Exception as analytics_error:
                        self.logger.warning(f"Analytics tracking failed for save: {analytics_error}")

                self.logger.info(f"Job saved successfully: user {user_id}, job {job_id}")

                return JobActionResult.success_result(
                    message="Job saved successfully",
                    data={
                        "saved_job_id": saved_job_orm.saved_job_id,
                        "user_id": user_id,
                        "job_id": job_id
                    }
                )

        except ValidationError as e:
            self.logger.warning(f"Validation error in _save_job: {e}")
            return JobActionResult.error_result(
                message="Invalid input parameters",
                error_code=JobActionErrorCode.VALIDATION_ERROR
            )

        except IntegrityError as e:
            self.logger.error(f"Database integrity error in _save_job: {e}")
            return JobActionResult.error_result(
                message="Database constraint violation - possible duplicate save",
                error_code=JobActionErrorCode.ALREADY_SAVED
            )

        except DatabaseError as e:
            self.logger.error(f"Database error in _save_job: {e}")
            return JobActionResult.error_result(
                message="Database operation failed",
                error_code=JobActionErrorCode.DATABASE_ERROR
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in _save_job: {e}", exc_info=True)
            return JobActionResult.error_result(
                message="Internal server error occurred",
                error_code=JobActionErrorCode.INTERNAL_ERROR
            )

    async def _unsave_job(self, user_id: str, job_id: str) -> JobActionResult:
        """
        Remove a saved job with comprehensive validation and tracking.
        
        Args:
            user_id: JobSeeker profile user_uid
            job_id: Job ID to unsave
            
        Returns:
            JobActionResult: Standardized result with success status
        """
        try:
            if not self._validate_user_and_job_ids(user_id, job_id):
                return JobActionResult.error_result(
                    message="Invalid user or job ID parameters",
                    error_code=JobActionErrorCode.VALIDATION_ERROR
                )

            with self.session_factory() as session:
                # Find existing saved job
                existing_save = session.query(SavedJobORM).filter_by(
                    user_id=user_id, job_id=job_id
                ).first()

                if not existing_save:
                    self.logger.info(f"Saved job not found for unsave: user {user_id}, job {job_id}")
                    return JobActionResult.error_result(
                        message="Saved job not found - cannot unsave job that wasn't saved",
                        error_code=JobActionErrorCode.SAVED_JOB_NOT_FOUND
                    )

                # Remove the saved job
                session.delete(existing_save)
                session.commit()

                # Invalidate related cache entries
                self.cache_manager.invalidate_job_actions_state(user_id, job_id)
                self.cache_manager.invalidate_user_liked_jobs(user_id)

                # Track analytics event
                analytics_service = self._get_analytics_service()
                if analytics_service:
                    try:
                        await analytics_service.track_job_action(
                            event_type="job_unsave",
                            user_id=user_id,
                            job_id=job_id,
                            metadata={}
                        )
                    except Exception as analytics_error:
                        self.logger.warning(f"Analytics tracking failed for unsave: {analytics_error}")

                self.logger.info(f"Job unsaved successfully: user {user_id}, job {job_id}")

                return JobActionResult.success_result(
                    message="Job unsaved successfully",
                    data={
                        "user_id": user_id,
                        "job_id": job_id
                    }
                )

        except DatabaseError as e:
            self.logger.error(f"Database error in _unsave_job: {e}")
            return JobActionResult.error_result(
                message="Database operation failed",
                error_code=JobActionErrorCode.DATABASE_ERROR
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in _unsave_job: {e}", exc_info=True)
            return JobActionResult.error_result(
                message="Internal server error occurred",
                error_code=JobActionErrorCode.INTERNAL_ERROR
            )

    async def _share_job(self, user_id: Optional[str], job_id: str, share_method: str) -> JobActionResult:
        """
        Share a job with comprehensive validation and tracking (allows anonymous sharing).
        
        Args:
            user_id: JobSeeker profile user_uid (optional for anonymous sharing)
            job_id: Job ID to share
            share_method: Method used to share (email, linkedin, etc.)
            
        Returns:
            JobActionResult: Standardized result with share_id, referral_code, and share_count
        """
        try:
            # Input validation
            if not job_id or not job_id.strip():
                return JobActionResult.error_result(
                    message="Invalid job ID parameter",
                    error_code=JobActionErrorCode.VALIDATION_ERROR
                )

            # Validate share method using Pydantic enum
            try:
                share_method_enum = ShareMethodEnum(share_method)
            except ValueError:
                self.logger.warning(f"Invalid share method provided: {share_method}")
                return JobActionResult.error_result(
                    message="Invalid share method - must be one of: email, linkedin, twitter, facebook, whatsapp, copy_link",
                    error_code=JobActionErrorCode.INVALID_SHARE_METHOD
                )

            with self.session_factory() as session:
                # Check if job exists and is accessible
                job = session.query(JobsORM).filter_by(job_id=job_id).first()
                if not job:
                    self.logger.warning(f"Job not found for share operation: {job_id}")
                    return JobActionResult.error_result(
                        message="Job not found",
                        error_code=JobActionErrorCode.JOB_NOT_FOUND
                    )

                # If user_id provided, validate user exists (optional for anonymous sharing)
                if user_id:
                    user_profile = session.query(JobSeekerProfileORM).filter_by(user_uid=user_id).first()
                    if not user_profile:
                        self.logger.warning(f"JobSeeker profile not found for share operation: {user_id}")
                        return JobActionResult.error_result(
                            message="JobSeeker profile not found",
                            error_code=JobActionErrorCode.USER_NOT_FOUND
                        )

                # Generate referral code if user is authenticated
                referral_code = None
                if user_id:
                    referral_code = JobShare.generate_referral_code(user_id, job_id)

                # Create job share using Pydantic model for validation
                job_share = JobShare(
                    user_id=user_id,
                    job_id=job_id,
                    share_method=share_method_enum,
                    referral_code=referral_code
                )

                # Convert to ORM for persistence
                share_orm = JobShareORM(**job_share.model_dump())
                session.add(share_orm)
                session.commit()

                # Get updated share count for this job
                share_count = session.query(func.count(JobShareORM.share_id)).filter_by(job_id=job_id).scalar()

                # Invalidate related cache entries
                self.cache_manager.invalidate_job_engagement_stats(job_id)
                if user_id:
                    self.cache_manager.invalidate_job_actions_state(user_id, job_id)

                # Track analytics event for business intelligence
                analytics_service = self._get_analytics_service()
                if analytics_service:
                    try:
                        await analytics_service.track_job_action(
                            event_type="job_share",
                            user_id=user_id,
                            job_id=job_id,
                            metadata={
                                "share_method": share_method,
                                "share_id": share_orm.share_id,
                                "referral_code": referral_code,
                                "is_anonymous": user_id is None
                            }
                        )
                    except Exception as analytics_error:
                        self.logger.warning(f"Analytics tracking failed for share: {analytics_error}")

                # Log successful share operation
                user_type = "authenticated" if user_id else "anonymous"
                self.logger.info(f"Job {job_id} shared via {share_method} by {user_type} user {user_id or 'N/A'}")

                return JobActionResult.success_result(
                    message="Job shared successfully",
                    data={
                        "share_id": share_orm.share_id,
                        "referral_code": referral_code,
                        "share_count": share_count,
                        "share_method": share_method,
                        "is_anonymous": user_id is None,
                        "job_id": job_id
                    }
                )

        except ValidationError as e:
            self.logger.warning(f"Validation error in _share_job: {e}")
            return JobActionResult.error_result(
                message="Invalid input parameters",
                error_code=JobActionErrorCode.VALIDATION_ERROR
            )

        except DatabaseError as e:
            self.logger.error(f"Database error in _share_job: {e}")
            return JobActionResult.error_result(
                message="Database operation failed",
                error_code=JobActionErrorCode.DATABASE_ERROR
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in _share_job: {e}", exc_info=True)
            return JobActionResult.error_result(
                message="Internal server error occurred",
                error_code=JobActionErrorCode.INTERNAL_ERROR
            )

    async def _get_actions_state(self, user_id: str, job_id: str) -> JobActionsStateResult:
        """
        Get the current state of job actions for a user and job with caching.
        
        Args:
            user_id: JobSeeker profile user_uid
            job_id: Job ID
            
        Returns:
            JobActionsStateResult: Standardized result with current job actions state
        """
        try:
            if not self._validate_user_and_job_ids(user_id, job_id):
                return JobActionsStateResult.error_result(
                    message="Invalid user or job ID parameters",
                    error_code=JobActionErrorCode.VALIDATION_ERROR
                )

            # Try to get from cache first
            try:
                cached_state = self.cache_manager.get_job_actions_state(user_id, job_id)
                if cached_state:
                    actions_state = JobActionsState(**cached_state)
                    return JobActionsStateResult.success_result(
                        message="Job actions state retrieved from cache",
                        actions_state=actions_state
                    )
            except Exception as cache_error:
                self.logger.warning(f"Cache read error for job actions state: {cache_error}")

            with self.session_factory() as session:
                # Check if user has liked the job
                user_has_liked = session.query(JobLikeORM).filter_by(
                    user_id=user_id, job_id=job_id
                ).first() is not None

                # Check if user has saved the job
                user_has_saved = session.query(SavedJobORM).filter_by(
                    user_id=user_id, job_id=job_id
                ).first() is not None

                # Get global engagement counts for the job
                like_count = session.query(func.count(JobLikeORM.like_id)).filter_by(job_id=job_id).scalar()
                share_count = session.query(func.count(JobShareORM.share_id)).filter_by(job_id=job_id).scalar()

                # Create JobActionsState object with validated data
                actions_state = JobActionsState(
                    job_id=job_id,
                    user_has_liked=user_has_liked,
                    user_has_saved=user_has_saved,
                    like_count=like_count or 0,
                    share_count=share_count or 0
                )

                # Cache the fresh data for future requests
                try:
                    state_dict = actions_state.to_dict()
                    self.cache_manager.set_job_actions_state(user_id, job_id, state_dict)
                    self.logger.debug(f"Cached fresh job actions state: user {user_id}, job {job_id}")
                except Exception as cache_error:
                    self.logger.warning(f"Failed to cache job actions state: {cache_error}")

                self.logger.debug(
                    f"Job actions state retrieved from database: user {user_id}, job {job_id}, "
                    f"liked={user_has_liked}, saved={user_has_saved}, "
                    f"likes={like_count}, shares={share_count}"
                )

                return JobActionsStateResult.success_result(
                    message="Job actions state retrieved successfully",
                    actions_state=actions_state
                )

        except ValidationError as e:
            self.logger.warning(f"Validation error in _get_actions_state: {e}")
            return JobActionsStateResult.error_result(
                message="Invalid input parameters",
                error_code=JobActionErrorCode.VALIDATION_ERROR
            )

        except DatabaseError as e:
            self.logger.error(f"Database error in _get_actions_state: {e}")
            return JobActionsStateResult.error_result(
                message="Database operation failed",
                error_code=JobActionErrorCode.DATABASE_ERROR
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in _get_actions_state: {e}", exc_info=True)
            return JobActionsStateResult.error_result(
                message="Internal server error occurred",
                error_code=JobActionErrorCode.INTERNAL_ERROR
            )

    async def _get_user_liked_jobs(self, user_id: str, limit: int = 20, offset: int = 0) -> JobListResult:
        """
        Get jobs liked by a user with comprehensive validation, caching, and optimization.
        
        This method implements optimized database queries to avoid N+1 problems,
        comprehensive caching strategies, and performance monitoring for efficient
        retrieval of user's liked jobs with proper pagination support.
        
        Args:
            user_id: JobSeeker profile user_uid
            limit: Number of jobs to return per page (max 100)
            offset: Starting offset for pagination
            
        Returns:
            JobListResult: Standardized result with liked jobs list and pagination metadata
            
        Performance Optimizations:
            - Uses joinedload to avoid N+1 query problems
            - Implements comprehensive caching with intelligent invalidation
            - Optimized pagination with proper indexing
            - Session pooling for efficient database connections
        """
        # Start performance tracking
        with job_actions_performance_logger.track_operation(
                'get_user_liked_jobs',
                user_id=user_id,
                metadata={'limit': limit, 'offset': offset}
        ) as perf_context:

            try:
                if not user_id or not user_id.strip():
                    return JobListResult.error_result(
                        message="Invalid user ID parameter",
                        error_code=JobActionErrorCode.VALIDATION_ERROR
                    )

                # Validate pagination parameters
                limit = max(1, min(limit, 100))  # Ensure reasonable limits (1-100)
                offset = max(0, offset)  # Ensure non-negative offset

                # Try to get from cache first for performance
                try:
                    cached_result = self.cache_manager.get_user_liked_jobs(user_id, limit, offset)
                    if cached_result:
                        perf_context['set_cache_hit'](True)
                        self.logger.debug(f"Returning cached liked jobs for user {user_id}")

                        return JobListResult.success_result(
                            message="Retrieved liked jobs from cache",
                            jobs=cached_result.get('jobs', []),
                            total_count=cached_result.get('total_count', 0),
                            limit=cached_result.get('limit', limit),
                            offset=cached_result.get('offset', offset)
                        )
                except Exception as cache_error:
                    self.logger.warning(f"Cache read error for liked jobs: {cache_error}")

                perf_context['set_cache_hit'](False)

                with self.session_factory() as session:
                    perf_context['increment_db_queries']()

                    # Optimized query with joins to avoid N+1 queries
                    # Use joinedload to fetch job data in a single query
                    liked_jobs_query = (
                        session.query(JobLikeORM)
                        .options(
                            joinedload(JobLikeORM.job).joinedload(JobsORM.company),  # Also load company data
                            joinedload(JobLikeORM.job).joinedload(JobsORM.posted_by_employer)  # Load employer data
                        )
                        .filter_by(user_id=user_id)
                        .order_by(JobLikeORM.created_at.desc())
                        .offset(offset)
                        .limit(limit)
                    )

                    liked_jobs = liked_jobs_query.all()
                    perf_context['increment_db_queries']()

                    # Get total count for pagination metadata (optimized with single query)
                    total_count = session.query(func.count(JobLikeORM.like_id)).filter_by(user_id=user_id).scalar()
                    perf_context['increment_db_queries']()

                    # Format job data with like timestamps and related data
                    jobs_data = []
                    for like in liked_jobs:
                        if like.job:
                            job_data = like.job.to_dict()
                            job_data['liked_at'] = like.created_at.replace(tzinfo=timezone.utc).isoformat()
                            job_data['like_id'] = like.like_id

                            # Add company information if available
                            if like.job.company:
                                job_data['company_name'] = like.job.company.company_name
                                job_data['company_logo'] = like.job.company.logo_path

                            jobs_data.append(job_data)

                    # Create result data for caching
                    result_data = {
                        'jobs': jobs_data,
                        'total_count': total_count or 0,
                        'limit': limit,
                        'offset': offset
                    }

                    # Cache the result for future requests (30 minutes TTL)
                    try:
                        self.cache_manager.set_user_liked_jobs(user_id, limit, offset, result_data, ttl=1800)
                        self.logger.debug(f"Cached liked jobs result for user {user_id}")
                    except Exception as cache_error:
                        self.logger.warning(f"Failed to cache liked jobs result: {cache_error}")

                    self.logger.info(
                        f"Retrieved {len(jobs_data)} liked jobs for user {user_id} "
                        f"(total: {total_count}, limit: {limit}, offset: {offset})",
                        extra={
                            'user_id': user_id,
                            'jobs_count': len(jobs_data),
                            'total_count': total_count,
                            'limit': limit,
                            'offset': offset,
                            'operation': 'get_user_liked_jobs'
                        }
                    )

                    return JobListResult.success_result(
                        message=f"Retrieved {len(jobs_data)} liked jobs successfully",
                        jobs=jobs_data,
                        total_count=total_count or 0,
                        limit=limit,
                        offset=offset
                    )

            except DatabaseError as e:
                self.logger.error(
                    f"Database error in _get_user_liked_jobs: {e}",
                    extra={
                        'user_id': user_id,
                        'limit': limit,
                        'offset': offset,
                        'database_error': str(e)
                    }
                )
                return JobListResult.error_result(
                    message="Database operation failed",
                    error_code=JobActionErrorCode.DATABASE_ERROR
                )

            except Exception as e:
                self.logger.error(
                    f"Unexpected error in _get_user_liked_jobs: {e}",
                    extra={
                        'user_id': user_id,
                        'limit': limit,
                        'offset': offset,
                        'error_type': type(e).__name__
                    },
                    exc_info=True
                )
                return JobListResult.error_result(
                    message="Internal server error occurred",
                    error_code=JobActionErrorCode.INTERNAL_ERROR
                )

    async def _get_user_saved_jobs(self, user_id: str, limit: int = 20, offset: int = 0) -> JobListResult:
        """
        Get jobs saved by a user with comprehensive caching and validation.
        
        Args:
            user_id: JobSeeker profile user_uid
            limit: Number of jobs to return per page (max 100)
            offset: Starting offset for pagination
            
        Returns:
            JobListResult: Standardized result with saved jobs list and pagination metadata
        """
        try:
            if not user_id or not user_id.strip():
                return JobListResult.error_result(
                    message="Invalid user ID parameter",
                    error_code=JobActionErrorCode.VALIDATION_ERROR
                )

            # Validate pagination parameters
            limit = max(1, min(limit, 100))  # Ensure reasonable limits (1-100)
            offset = max(0, offset)  # Ensure non-negative offset

            # Try to get from cache first for performance
            try:
                cached_result = self.cache_manager.get_user_saved_jobs(user_id, limit, offset)
                if cached_result:
                    self.logger.debug(f"Returning cached saved jobs for user {user_id}")
                    # Convert cached dict to JobListResult if it's in old format
                    if isinstance(cached_result, dict) and cached_result.get('success'):
                        data = cached_result.get('data', {})
                        return JobListResult.success_result(
                            message="Retrieved saved jobs from cache",
                            jobs=data.get('jobs', []),
                            total_count=data.get('total_count', 0),
                            limit=data.get('limit', limit),
                            offset=data.get('offset', offset)
                        )
            except Exception as cache_error:
                self.logger.warning(f"Cache read error for saved jobs: {cache_error}")

            with self.session_factory() as session:
                # Optimized query with joins to avoid N+1 queries
                saved_jobs_query = (
                    session.query(SavedJobORM)
                    .options(joinedload(SavedJobORM.job))
                    .filter_by(user_id=user_id)
                    .order_by(SavedJobORM.saved_at.desc())
                    .offset(offset)
                    .limit(limit)
                )

                saved_jobs = saved_jobs_query.all()

                # Get total count for pagination metadata
                total_count = session.query(func.count(SavedJobORM.saved_job_id)).filter_by(user_id=user_id).scalar()

                # Format job data with save timestamps
                jobs_data = []
                for saved in saved_jobs:
                    if saved.job:
                        job_data = saved.job.to_dict()
                        job_data['saved_at'] = saved.saved_at.replace(tzinfo=timezone.utc).isoformat()
                        job_data['saved_job_id'] = saved.saved_job_id
                        jobs_data.append(job_data)

                # Create standardized result
                result = JobListResult.success_result(
                    message=f"Retrieved {len(jobs_data)} saved jobs successfully",
                    jobs=jobs_data,
                    total_count=total_count or 0,
                    limit=limit,
                    offset=offset
                )

                # Cache the result for future requests
                try:
                    cache_data = {
                        "success": True,
                        "data": {
                            "jobs": jobs_data,
                            "total_count": total_count or 0,
                            "limit": limit,
                            "offset": offset
                        }
                    }
                    self.cache_manager.set_user_saved_jobs(user_id, cache_data, limit, offset)
                    self.logger.debug(f"Cached saved jobs result for user {user_id}")
                except Exception as cache_error:
                    self.logger.warning(f"Failed to cache saved jobs result: {cache_error}")

                self.logger.info(
                    f"Retrieved {len(jobs_data)} saved jobs for user {user_id} "
                    f"(total: {total_count}, limit: {limit}, offset: {offset})"
                )

                return result

        except DatabaseError as e:
            self.logger.error(f"Database error in _get_user_saved_jobs: {e}")
            return JobListResult.error_result(
                message="Database operation failed",
                error_code=JobActionErrorCode.DATABASE_ERROR
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in _get_user_saved_jobs: {e}", exc_info=True)
            return JobListResult.error_result(
                message="Internal server error occurred",
                error_code=JobActionErrorCode.INTERNAL_ERROR
            )

    async def _get_job_engagement_stats(self, job_id: str) -> JobEngagementResult:
        """
        Get comprehensive engagement statistics for a job with caching and optimization.
        
        This method implements expensive engagement statistics calculations with
        comprehensive caching, optimized database queries, and performance monitoring
        to provide detailed job engagement metrics efficiently.
        
        Args:
            job_id: Job ID to get engagement statistics for
            
        Returns:
            JobEngagementResult: Standardized result with engagement statistics
            
        Performance Optimizations:
            - Comprehensive caching for expensive calculations (1 hour TTL)
            - Optimized database queries with proper indexing
            - Batch processing for multiple statistics
            - Performance monitoring and alerting
        """
        # Start performance tracking
        with job_actions_performance_logger.track_operation(
                'get_job_engagement_stats',
                job_id=job_id,
                metadata={'operation_type': 'analytics'}
        ) as perf_context:

            try:
                if not job_id or not job_id.strip():
                    return JobEngagementResult.error_result(
                        message="Invalid job ID parameter",
                        error_code=JobActionErrorCode.VALIDATION_ERROR
                    )

                # Try to get from cache first (expensive calculation)
                try:
                    cached_stats = self.cache_manager.get_job_engagement_stats(job_id)
                    if cached_stats:
                        perf_context['set_cache_hit'](True)
                        self.logger.debug(f"Returning cached engagement stats for job {job_id}")

                        return JobEngagementResult.success_result(
                            message="Job engagement statistics retrieved from cache",
                            engagement_data=cached_stats
                        )
                except Exception as cache_error:
                    self.logger.warning(f"Cache read error for engagement stats: {cache_error}")

                perf_context['set_cache_hit'](False)

                with self.session_factory() as session:
                    # Optimized batch query to get all engagement metrics in fewer queries
                    from datetime import timedelta
                    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
                    month_ago = datetime.now(timezone.utc) - timedelta(days=30)

                    # Single query for like statistics
                    like_stats = session.query(
                        func.count(JobLikeORM.like_id).label('total_likes'),
                        func.count(func.case([(JobLikeORM.created_at >= week_ago, 1)])).label('recent_likes'),
                        func.count(func.case([(JobLikeORM.created_at >= month_ago, 1)])).label('monthly_likes')
                    ).filter_by(job_id=job_id).first()
                    perf_context['increment_db_queries']()

                    # Single query for share statistics with method breakdown
                    share_stats = session.query(
                        JobShareORM.share_method,
                        func.count(JobShareORM.share_id).label('total_shares'),
                        func.count(func.case([(JobShareORM.shared_at >= week_ago, 1)])).label('recent_shares'),
                        func.count(func.case([(JobShareORM.shared_at >= month_ago, 1)])).label('monthly_shares')
                    ).filter_by(job_id=job_id).group_by(JobShareORM.share_method).all()
                    perf_context['increment_db_queries']()

                    # Get saved job count (additional engagement metric)
                    saved_count = session.query(func.count(SavedJobORM.saved_job_id)).filter_by(job_id=job_id).scalar()
                    perf_context['increment_db_queries']()

                    # Process like statistics
                    total_likes = like_stats.total_likes or 0
                    recent_likes = like_stats.recent_likes or 0
                    monthly_likes = like_stats.monthly_likes or 0

                    # Process share statistics
                    share_by_method = {}
                    total_shares = 0
                    recent_shares_total = 0
                    monthly_shares_total = 0

                    for share_stat in share_stats:
                        method = share_stat.share_method
                        total_method_shares = share_stat.total_shares or 0
                        recent_method_shares = share_stat.recent_shares or 0
                        monthly_method_shares = share_stat.monthly_shares or 0

                        share_by_method[method] = {
                            'total': total_method_shares,
                            'recent': recent_method_shares,
                            'monthly': monthly_method_shares
                        }

                        total_shares += total_method_shares
                        recent_shares_total += recent_method_shares
                        monthly_shares_total += monthly_method_shares

                    # Calculate advanced engagement metrics
                    total_engagement = total_likes + total_shares + (saved_count or 0)
                    engagement_score = (total_likes * 2) + total_shares + ((saved_count or 0) * 1.5)  # Weighted scoring

                    # Calculate engagement rates and trends
                    recent_engagement_rate = 0.0
                    if total_engagement > 0:
                        recent_engagement_rate = ((recent_likes + recent_shares_total) / total_engagement) * 100

                    # Calculate viral coefficient (shares per like)
                    viral_coefficient = 0.0
                    if total_likes > 0:
                        viral_coefficient = total_shares / total_likes

                    # Build comprehensive engagement data
                    engagement_data = {
                        "job_id": job_id,
                        "timestamp": datetime.utcnow().isoformat(),

                        # Core metrics
                        "like_count": total_likes,
                        "share_count": total_shares,
                        "saved_count": saved_count or 0,
                        "total_engagement": total_engagement,

                        # Detailed breakdowns
                        "share_by_method": share_by_method,
                        "share_by_method_totals": {method: data['total'] for method, data in share_by_method.items()},

                        # Time-based analytics
                        "recent_activity": {
                            "likes_last_7_days": recent_likes,
                            "shares_last_7_days": recent_shares_total,
                            "likes_last_30_days": monthly_likes,
                            "shares_last_30_days": monthly_shares_total
                        },

                        # Advanced metrics
                        "engagement_score": round(engagement_score, 2),
                        "recent_engagement_rate": round(recent_engagement_rate, 2),
                        "viral_coefficient": round(viral_coefficient, 3),

                        # Performance indicators
                        "engagement_level": self._calculate_engagement_level(total_engagement),
                        "trending_status": self._calculate_trending_status(recent_likes, recent_shares_total,
                                                                           total_engagement),

                        # Platform performance
                        "platform_performance": self._analyze_platform_performance(share_by_method)
                    }

                    # Cache the expensive calculation (1 hour TTL)
                    try:
                        self.cache_manager.set_job_engagement_stats(job_id, engagement_data, ttl=3600)
                        self.logger.debug(f"Cached engagement stats for job {job_id}")
                    except Exception as cache_error:
                        self.logger.warning(f"Failed to cache engagement stats: {cache_error}")

                    self.logger.info(
                        f"Retrieved engagement stats for job {job_id}: "
                        f"likes={total_likes}, shares={total_shares}, saved={saved_count}, score={engagement_score:.2f}",
                        extra={
                            'job_id': job_id,
                            'total_likes': total_likes,
                            'total_shares': total_shares,
                            'saved_count': saved_count,
                            'engagement_score': engagement_score,
                            'operation': 'get_job_engagement_stats'
                        }
                    )

                    return JobEngagementResult.success_result(
                        message="Job engagement statistics retrieved successfully",
                        engagement_data=engagement_data
                    )

            except DatabaseError as e:
                self.logger.error(
                    f"Database error in _get_job_engagement_stats: {e}",
                    extra={
                        'job_id': job_id,
                        'database_error': str(e)
                    }
                )
                return JobEngagementResult.error_result(
                    message="Database operation failed",
                    error_code=JobActionErrorCode.DATABASE_ERROR
                )

            except Exception as e:
                self.logger.error(
                    f"Unexpected error in _get_job_engagement_stats: {e}",
                    extra={
                        'job_id': job_id,
                        'error_type': type(e).__name__
                    },
                    exc_info=True
                )
                return JobEngagementResult.error_result(
                    message="Internal server error occurred",
                    error_code=JobActionErrorCode.INTERNAL_ERROR
                )

    def _calculate_engagement_level(self, total_engagement: int) -> str:
        """Calculate engagement level based on total engagement"""
        if total_engagement >= 100:
            return "high"
        elif total_engagement >= 25:
            return "medium"
        elif total_engagement >= 5:
            return "low"
        else:
            return "minimal"

    def _calculate_trending_status(self, recent_likes: int, recent_shares: int, total_engagement: int) -> str:
        """Calculate trending status based on recent activity"""
        recent_activity = recent_likes + recent_shares

        if total_engagement == 0:
            return "new"

        recent_percentage = (recent_activity / total_engagement) * 100

        if recent_percentage >= 50:
            return "trending"
        elif recent_percentage >= 25:
            return "active"
        elif recent_percentage >= 10:
            return "moderate"
        else:
            return "stable"

    def _analyze_platform_performance(self, share_by_method: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        """Analyze performance across different sharing platforms"""
        if not share_by_method:
            return {"status": "no_shares", "recommendations": ["Encourage sharing to increase visibility"]}

        total_shares = sum(data['total'] for data in share_by_method.values())
        platform_performance = {}

        for method, data in share_by_method.items():
            percentage = (data['total'] / total_shares) * 100 if total_shares > 0 else 0
            platform_performance[method] = {
                "shares": data['total'],
                "percentage": round(percentage, 1),
                "recent_shares": data.get('recent', 0),
                "performance_rating": self._get_platform_rating(percentage)
            }

        # Find best performing platform
        best_platform = max(platform_performance.items(), key=lambda x: x[1]['shares'])

        return {
            "platforms": platform_performance,
            "best_platform": best_platform[0],
            "total_platforms_used": len(share_by_method),
            "recommendations": self._generate_sharing_recommendations(platform_performance)
        }

    def _get_platform_rating(self, percentage: float) -> str:
        """Get performance rating for a platform based on share percentage"""
        if percentage >= 40:
            return "excellent"
        elif percentage >= 25:
            return "good"
        elif percentage >= 15:
            return "fair"
        else:
            return "poor"

    def _generate_sharing_recommendations(self, platform_performance: Dict[str, Any]) -> list[str]:
        """Generate recommendations for improving sharing performance"""
        recommendations = []

        if len(platform_performance) < 3:
            recommendations.append("Consider enabling more sharing platforms to increase reach")

        # Find underperforming platforms
        poor_platforms = [platform for platform, data in platform_performance.items()
                          if data['performance_rating'] == 'poor']

        if poor_platforms:
            recommendations.append(f"Improve sharing experience for: {', '.join(poor_platforms)}")

        # Check for recent activity
        platforms_with_recent_activity = [platform for platform, data in platform_performance.items()
                                          if data.get('recent_shares', 0) > 0]

        if len(platforms_with_recent_activity) < len(platform_performance) / 2:
            recommendations.append("Recent sharing activity is low - consider promotional campaigns")

        if not recommendations:
            recommendations.append("Sharing performance is healthy across platforms")

        return recommendations

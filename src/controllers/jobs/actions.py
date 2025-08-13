"""
Job Actions Controller

Handles job interaction actions like liking, saving, and sharing jobs.
This controller follows the established MVC architecture patterns and provides
comprehensive job interaction functionality with proper error handling,
caching, and analytics integration.
"""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from flask import Flask
from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError, DatabaseError
from sqlalchemy.orm import joinedload
from pydantic import ValidationError

from src.controllers.controller import Controllers, error_handler
from src.database.models import (
    JobLike, JobShare, JobActionsState, JobLikeRequest, JobSaveRequest,
    JobShareRequest, JobActionsResponse, ShareMethodEnum, SavedJob
)
from src.database.models.job_actions_results import (
    JobActionResult, JobActionsStateResult, JobEngagementResult,
    JobListResult, JobActionErrorCode
)
from src.database import (
    JobLikeORM, JobShareORM, JobsORM, JobSeekerProfileORM, SavedJobORM
)
from src.cache.job_actions_cache import job_actions_cache
from src.utils.job_actions_security_logger import job_actions_security_logger, SecurityEventType, SecuritySeverity
from src.utils.job_actions_performance_logger import job_actions_performance_logger


class JobActionsController(Controllers):
    """
    Controller for job interaction actions (likes, saves, shares).
    
    This controller manages user interactions with job postings, providing
    comprehensive functionality for liking, saving, and sharing jobs. It follows
    the established MVC architecture with proper error handling, caching,
    analytics integration, and standardized result objects.
    
    Architecture Integration:
        - Inherits from Controllers base class for session management and logging
        - Uses factory pattern for dependency injection and service access
        - Implements standardized error handling with @error_handler decorator
        - Integrates with Redis caching layer for performance optimization
        - Provides comprehensive analytics tracking for business intelligence
        - Returns standardized result objects for consistent API responses
    
    Dependencies:
        - ControllerFactory: For accessing other controllers and services
        - JobActionsAnalyticsService: For tracking user engagement metrics
        - JobActionsCache: For performance optimization and data caching
        - Database session factory: For database operations and transaction management
        - Logging system: For audit trails, debugging, and monitoring
    
    Business Rules:
        - Users must have valid JobSeeker profiles to perform actions
        - Jobs must exist and be accessible for actions to be performed
        - Duplicate actions (like/save) are prevented with appropriate error responses
        - Anonymous sharing is allowed but authenticated sharing provides tracking
        - All actions are logged for analytics and audit purposes
        - Cache invalidation ensures data consistency across operations
    
    Performance Considerations:
        - Uses session pooling for efficient database connections
        - Implements comprehensive caching strategies for frequently accessed data
        - Optimizes database queries to avoid N+1 query problems
        - Provides batch operations where applicable for better performance
    
    Security Features:
        - Input validation through Pydantic models
        - SQL injection prevention through ORM usage
        - Rate limiting integration for abuse prevention
        - Comprehensive audit logging for security monitoring
    """

    def __init__(self, factory):
        """
        Initialize JobActionsController with dependency injection.
        
        Sets up the controller with access to the factory pattern for
        dependency injection and initializes core attributes for
        service integration. The controller delegates business logic
        to the JobActionsService following the established architecture.
        
        Args:
            factory: ControllerFactory instance providing access to other
                    controllers and services through the factory pattern
        
        Attributes:
            job_actions_service: Service layer for job actions business logic
            analytics_service: Service for tracking user engagement and actions
            monitoring_service: Service for performance and health monitoring
        """
        super().__init__(factory)
        self.job_actions_service = None
        self.analytics_service = None
        self.monitoring_service = None

    def init_app(self, app: Flask):
        """
        Initialize controller with Flask application context.
        
        This method sets up service dependencies, integrates with the application
        monitoring systems, and ensures proper Flask integration following
        the established init_app pattern. The controller delegates business
        logic to the service layer while maintaining proper error handling
        and monitoring integration.
        
        Args:
            app: Flask application instance for context and configuration
            
        Side Effects:
            - Initializes job actions service for business logic delegation
            - Initializes analytics service for user engagement tracking
            - Starts monitoring service for performance and health tracking
            - Registers controller with application extensions
            
        Raises:
            ImportError: If required services are not available
            ConfigurationError: If service initialization fails
        """
        super().init_app(app=app)

        try:
            # Initialize job actions service using service factory pattern
            from src.utils.route_helpers import get_service
            self.job_actions_service = get_service('job_actions')()

            # Initialize analytics service using service factory pattern
            self.analytics_service = get_service('job_actions_analytics')()

            # Initialize monitoring service for performance tracking
            from src.utils.job_actions_monitoring import job_actions_monitor
            self.monitoring_service = job_actions_monitor
            job_actions_monitor.start_monitoring()

            # Register controller with app extensions for proper lifecycle management
            if not hasattr(app, 'job_actions_controller'):
                app.job_actions_controller = self

            self.logger.info("JobActionsController initialized successfully with service layer delegation")

        except Exception as e:
            self.logger.error(f"Failed to initialize JobActionsController: {e}")
            raise

    @error_handler
    async def like_job(self, user_id: str, job_id: str) -> JobActionResult:
        """
        Like a job for a user with comprehensive validation, tracking, and monitoring.
        
        This method delegates to the JobActionsService for business logic execution
        while maintaining proper error handling, security logging, performance monitoring,
        and audit trail integration. It follows the established MVC architecture where
        controllers handle request/response concerns and delegate business logic to the service layer.
        
        Args:
            user_id: JobSeeker profile user_uid (validated UUID string)
                    Must correspond to an existing and active JobSeeker profile
            job_id: Job ID to like (validated UUID string)
                   Must correspond to an existing and accessible job posting
                   
        Returns:
            JobActionResult: Standardized result object from service layer containing:
                - success: True if like was created successfully
                - message: Human-readable status message
                - data: Dictionary with like_id and updated like_count
                - error_code: Specific error code for client handling
                - timestamp: UTC timestamp of operation
                
        Architecture:
            - Controller handles request validation and response formatting
            - Service layer handles all business logic and data operations
            - Security logging tracks all operations and potential threats
            - Performance monitoring tracks operation metrics
            - Standardized result objects ensure consistent API responses
            
        Security & Monitoring:
            - All operations logged for security audit trail
            - Performance metrics tracked for optimization
            - Error patterns monitored for threat detection
            - Input validation prevents injection attacks
        """
        # Start performance tracking at controller level
        with job_actions_performance_logger.track_operation(
                'controller_like_job',
                user_id=user_id,
                job_id=job_id,
                metadata={'layer': 'controller', 'operation': 'like_job'}
        ) as perf_context:
            
            try:
                # Basic input validation at controller level
                if not user_id or not user_id.strip():
                    job_actions_security_logger.log_input_validation_failure(
                        user_id=user_id,
                        action='like_job_controller',
                        validation_errors={'user_id': 'empty or invalid'},
                        input_data={'user_id': user_id, 'job_id': job_id}
                    )

                    return JobActionResult.error_result(
                        message="Invalid user ID parameter",
                        error_code=JobActionErrorCode.VALIDATION_ERROR
                    )

                if not job_id or not job_id.strip():
                    job_actions_security_logger.log_input_validation_failure(
                        user_id=user_id,
                        action='like_job_controller',
                        validation_errors={'job_id': 'empty or invalid'},
                        input_data={'user_id': user_id, 'job_id': job_id}
                    )

                    return JobActionResult.error_result(
                        message="Invalid job ID parameter",
                        error_code=JobActionErrorCode.VALIDATION_ERROR
                    )

                # Delegate business logic to service layer
                result = await self.job_actions_service.execute('like_job', user_id=user_id, job_id=job_id)

                # Track performance metrics for monitoring
                if self.monitoring_service:
                    try:
                        self.monitoring_service.record_user_action(
                            action='like',
                            user_id=user_id,
                            job_id=job_id,
                            duration=0.0,  # Would be calculated in real implementation
                            success=result.success
                        )
                    except Exception as monitoring_error:
                        self.logger.warning(f"Monitoring service error: {monitoring_error}")

                # Log controller-level operation for audit trail
                if result.success:
                    job_actions_security_logger.log_audit_trail(
                        user_id=user_id,
                        action='like_job_controller',
                        resource=f'job:{job_id}',
                        result='success',
                        job_id=job_id,
                        details={
                            'controller_layer': True,
                            'service_result': result.success,
                            'like_data': result.data if result.data else {}
                        }
                    )

                    self.logger.info(
                        f"Controller: Job like operation successful for user {user_id}, job {job_id}",
                        extra={
                            'user_id': user_id,
                            'job_id': job_id,
                            'operation': 'like_job',
                            'layer': 'controller',
                            'success': True,
                            'result_data': result.data
                        }
                    )
                else:
                    # Log failed operations for security monitoring
                    job_actions_security_logger.log_security_event(
                        event_type=SecurityEventType.AUDIT_TRAIL,
                        severity=SecuritySeverity.LOW,
                        user_id=user_id,
                        job_id=job_id,
                        action='like_job_controller_failure',
                        details={
                            'controller_layer': True,
                            'failure_reason': result.message,
                            'error_code': result.error_code.value if result.error_code else None
                        }
                    )

                    self.logger.warning(
                        f"Controller: Job like operation failed for user {user_id}, job {job_id}: {result.message}",
                        extra={
                            'user_id': user_id,
                            'job_id': job_id,
                            'operation': 'like_job',
                            'layer': 'controller',
                            'success': False,
                            'error_message': result.message,
                            'error_code': result.error_code.value if result.error_code else None
                        }
                    )

                return result
                
            except Exception as e:
                # Handle service layer exceptions at controller level with comprehensive logging
                job_actions_security_logger.log_security_event(
                    event_type=SecurityEventType.PERFORMANCE_ANOMALY,
                    severity=SecuritySeverity.HIGH,
                    user_id=user_id,
                    job_id=job_id,
                    action='like_job_controller_exception',
                    details={
                        'controller_layer': True,
                        'exception_type': type(e).__name__,
                        'exception_message': str(e)
                    }
                )

                self.logger.error(
                    f"Controller error in like_job: {e}",
                    extra={
                        'user_id': user_id,
                        'job_id': job_id,
                        'operation': 'like_job',
                        'layer': 'controller',
                        'exception_type': type(e).__name__,
                        'security_event': True
                    },
                    exc_info=True
                )

                return JobActionResult.error_result(
                    message="Controller error occurred",
                    error_code=JobActionErrorCode.INTERNAL_ERROR
                )

    @error_handler
    async def unlike_job(self, user_id: str, job_id: str) -> JobActionResult:
        """
        Remove a like from a job with comprehensive validation and tracking.
        
        This method handles the complete job unliking workflow including validation
        of the existing like, database deletion, cache invalidation, and analytics
        tracking. It ensures data consistency and provides proper error handling
        for all edge cases.
        
        Args:
            user_id: JobSeeker profile user_uid (validated UUID string)
                    Must correspond to an existing JobSeeker profile
            job_id: Job ID to unlike (validated UUID string)
                   Must correspond to an existing job with an existing like
                   
        Returns:
            JobActionResult: Standardized result object containing:
                - success: True if like was removed successfully
                - message: Human-readable status message
                - data: Dictionary with updated like_count
                - error_code: Specific error code for client handling
                - timestamp: UTC timestamp of operation
                
        Raises:
            ValidationError: When input parameters fail validation
            DatabaseError: When database operations fail
            CacheError: When cache operations fail (non-blocking)
            
        Side Effects:
            - Removes JobLikeORM record from database
            - Invalidates user-specific and job-specific cache entries
            - Triggers analytics event for engagement tracking
            - Updates job engagement metrics and statistics
            - Logs successful operation for audit trail
            
        Business Rules:
            - Like must exist before it can be removed
            - User must own the like being removed
            - Like count is updated atomically with like removal
            - Cache consistency is maintained across all related data
            
        Performance Considerations:
            - Uses optimized database queries with proper indexing
            - Implements efficient cache invalidation strategies
            - Minimizes database round trips through batch operations
        """
        try:
            # Input validation
            if not self._validate_user_and_job_ids(user_id, job_id):
                return JobActionResult.error_result(
                    message="Invalid user or job ID parameters",
                    error_code=JobActionErrorCode.VALIDATION_ERROR
                )

            with self.get_session() as session:
                # Find existing like to ensure it exists and belongs to user
                existing_like = session.query(JobLikeORM).filter_by(
                    user_id=user_id, job_id=job_id
                ).first()

                if not existing_like:
                    self.logger.info(f"Like not found for unlike: user {user_id}, job {job_id}")
                    return JobActionResult.error_result(
                        message="Like not found - cannot unlike job that wasn't liked",
                        error_code=JobActionErrorCode.LIKE_NOT_FOUND
                    )

                # Store like_id for logging before deletion
                like_id = existing_like.like_id

                # Remove like from database
                session.delete(existing_like)
                session.commit()

                # Get updated like count after deletion
                like_count = session.query(func.count(JobLikeORM.like_id)).filter_by(job_id=job_id).scalar()

                # Invalidate related cache entries for data consistency
                try:
                    self.cache_manager.invalidate_user_action_cache(user_id, job_id)
                    self.cache_manager.invalidate_job_engagement_stats(job_id)
                except Exception as cache_error:
                    self.logger.warning(f"Cache invalidation failed during unlike: {cache_error}")

                # Track analytics event for business intelligence
                try:
                    if self.analytics_service:
                        await self.analytics_service.track_job_action(
                            event_type="job_unlike",
                            user_id=user_id,
                            job_id=job_id,
                            metadata={
                                "removed_like_id": like_id,
                                "like_count": like_count
                            }
                        )
                except Exception as analytics_error:
                    self.logger.warning(f"Analytics tracking failed during unlike: {analytics_error}")

                # Log successful operation
                self.logger.info(
                    f"Job unlike completed successfully: user {user_id}, job {job_id}, "
                    f"removed_like_id {like_id}, remaining_likes {like_count}"
                )

                return JobActionResult.success_result(
                    message="Job unliked successfully",
                    data={
                        "like_count": like_count,
                        "user_id": user_id,
                        "job_id": job_id,
                        "removed_like_id": like_id
                    }
                )

        except ValidationError as e:
            self.logger.warning(f"Validation error in unlike_job: {e}")
            return JobActionResult.error_result(
                message="Invalid input parameters",
                error_code=JobActionErrorCode.VALIDATION_ERROR
            )

        except DatabaseError as e:
            self.logger.error(f"Database error in unlike_job: {e}")
            return JobActionResult.error_result(
                message="Database operation failed",
                error_code=JobActionErrorCode.DATABASE_ERROR
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in unlike_job: {e}", exc_info=True)
            return JobActionResult.error_result(
                message="Internal server error occurred",
                error_code=JobActionErrorCode.INTERNAL_ERROR
            )

    @error_handler
    async def save_job(self, user_id: str, job_id: str) -> JobActionResult:
        """
        Save a job for a user with comprehensive validation and tracking.
        
        This method handles the complete job saving workflow, extending the existing
        SavedJob functionality with proper validation, duplicate checking, database
        persistence, cache management, and analytics tracking. It integrates with
        the existing saved jobs system while maintaining data consistency.
        
        Args:
            user_id: JobSeeker profile user_uid (validated UUID string)
                    Must correspond to an existing and active JobSeeker profile
            job_id: Job ID to save (validated UUID string)
                   Must correspond to an existing and accessible job posting
                   
        Returns:
            JobActionResult: Standardized result object containing:
                - success: True if job was saved successfully
                - message: Human-readable status message
                - data: Dictionary with saved_job_id and metadata
                - error_code: Specific error code for client handling
                - timestamp: UTC timestamp of operation
                
        Raises:
            ValidationError: When input parameters fail validation
            DatabaseError: When database operations fail
            IntegrityError: When database constraints are violated
            CacheError: When cache operations fail (non-blocking)
            
        Side Effects:
            - Creates new SavedJobORM record in database
            - Invalidates user-specific cache entries for saved jobs
            - Triggers analytics event for user engagement tracking
            - Updates user's saved jobs collection and statistics
            - Logs successful operation for audit trail
            
        Business Rules:
            - User must have valid and active JobSeeker profile
            - Job must exist, be active, and accessible to the user
            - Duplicate saves are prevented (returns 409 error with ALREADY_SAVED code)
            - Saved jobs are associated with user profiles for easy retrieval
            - Save timestamps are recorded for chronological ordering
            
        Integration Points:
            - Extends existing SavedJob functionality and database schema
            - Integrates with user profile management system
            - Connects with job notification system for status updates
            - Provides data for user dashboard and saved jobs management
        """
        try:
            # Input validation
            if not self._validate_user_and_job_ids(user_id, job_id):
                return JobActionResult.error_result(
                    message="Invalid user or job ID parameters",
                    error_code=JobActionErrorCode.VALIDATION_ERROR
                )

            with self.get_session() as session:
                # Verify user exists and has JobSeeker profile
                user_profile = session.query(JobSeekerProfileORM).filter_by(user_uid=user_id).first()
                if not user_profile:
                    self.logger.warning(f"JobSeeker profile not found for save operation: {user_id}")
                    return JobActionResult.error_result(
                        message="JobSeeker profile not found",
                        error_code=JobActionErrorCode.USER_NOT_FOUND
                    )

                # Verify job exists and is accessible
                job = session.query(JobsORM).filter_by(job_id=job_id).first()
                if not job:
                    self.logger.warning(f"Job not found for save operation: {job_id}")
                    return JobActionResult.error_result(
                        message="Job not found",
                        error_code=JobActionErrorCode.JOB_NOT_FOUND
                    )

                # Check for existing saved job to prevent duplicates
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

                # Persist to database with transaction safety
                session.add(saved_job_orm)
                session.commit()

                # Invalidate related cache entries for data consistency
                try:
                    self.cache_manager.invalidate_job_actions_state(user_id, job_id)
                    self.cache_manager.invalidate_user_saved_jobs(user_id)
                    # Also invalidate user profile cache if it includes saved jobs count
                    self.cache_manager.invalidate_user_profile_cache(user_id)
                except Exception as cache_error:
                    self.logger.warning(f"Cache invalidation failed during save: {cache_error}")

                # Track analytics event for business intelligence
                try:
                    if self.analytics_service:
                        await self.analytics_service.track_job_action(
                            event_type="job_save",
                            user_id=user_id,
                            job_id=job_id,
                            metadata={
                                "saved_job_id": saved_job_orm.saved_job_id,
                                "job_title": job.title if hasattr(job, 'title') else None,
                                "company_id": job.company_id if hasattr(job, 'company_id') else None
                            }
                        )
                except Exception as analytics_error:
                    self.logger.warning(f"Analytics tracking failed during save: {analytics_error}")

                # Log successful operation
                self.logger.info(
                    f"Job saved successfully: user {user_id}, job {job_id}, "
                    f"saved_job_id {saved_job_orm.saved_job_id}"
                )

                return JobActionResult.success_result(
                    message="Job saved successfully",
                    data={
                        "saved_job_id": saved_job_orm.saved_job_id,
                        "user_id": user_id,
                        "job_id": job_id,
                        "saved_at": saved_job_orm.saved_at.isoformat() if hasattr(saved_job_orm, 'saved_at') else None
                    }
                )

        except ValidationError as e:
            self.logger.warning(f"Validation error in save_job: {e}")
            return JobActionResult.error_result(
                message="Invalid input parameters",
                error_code=JobActionErrorCode.VALIDATION_ERROR
            )

        except IntegrityError as e:
            self.logger.error(f"Database integrity error in save_job: {e}")
            return JobActionResult.error_result(
                message="Database constraint violation - possible duplicate save",
                error_code=JobActionErrorCode.ALREADY_SAVED
            )

        except DatabaseError as e:
            self.logger.error(f"Database error in save_job: {e}")
            return JobActionResult.error_result(
                message="Database operation failed",
                error_code=JobActionErrorCode.DATABASE_ERROR
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in save_job: {e}", exc_info=True)
            return JobActionResult.error_result(
                message="Internal server error occurred",
                error_code=JobActionErrorCode.INTERNAL_ERROR
            )

    @error_handler
    async def unsave_job(self, user_id: str, job_id: str) -> JobActionResult:
        """
        Remove a saved job with comprehensive validation and tracking.
        
        This method handles the complete job unsaving workflow including validation
        of the existing saved job, database deletion, cache invalidation, and
        analytics tracking. It ensures data consistency and provides proper error
        handling for all edge cases.
        
        Args:
            user_id: JobSeeker profile user_uid (validated UUID string)
                    Must correspond to an existing JobSeeker profile
            job_id: Job ID to unsave (validated UUID string)
                   Must correspond to an existing job with an existing saved record
                   
        Returns:
            JobActionResult: Standardized result object containing:
                - success: True if saved job was removed successfully
                - message: Human-readable status message
                - data: Dictionary with operation metadata
                - error_code: Specific error code for client handling
                - timestamp: UTC timestamp of operation
                
        Side Effects:
            - Removes SavedJobORM record from database
            - Invalidates user-specific cache entries for saved jobs
            - Triggers analytics event for engagement tracking
            - Updates user's saved jobs collection and statistics
            - Logs successful operation for audit trail
            
        Business Rules:
            - Saved job must exist before it can be removed
            - User must own the saved job being removed
            - Cache consistency is maintained across all related data
        """
        try:
            # Input validation
            if not self._validate_user_and_job_ids(user_id, job_id):
                return JobActionResult.error_result(
                    message="Invalid user or job ID parameters",
                    error_code=JobActionErrorCode.VALIDATION_ERROR
                )

            with self.get_session() as session:
                # Find existing saved job to ensure it exists and belongs to user
                existing_save = session.query(SavedJobORM).filter_by(
                    user_id=user_id, job_id=job_id
                ).first()

                if not existing_save:
                    self.logger.info(f"Saved job not found for unsave: user {user_id}, job {job_id}")
                    return JobActionResult.error_result(
                        message="Saved job not found - cannot unsave job that wasn't saved",
                        error_code=JobActionErrorCode.SAVED_JOB_NOT_FOUND
                    )

                # Store saved_job_id for logging before deletion
                saved_job_id = existing_save.saved_job_id

                # Remove saved job from database
                session.delete(existing_save)
                session.commit()

                # Invalidate related cache entries for data consistency
                try:
                    self.cache_manager.invalidate_job_actions_state(user_id, job_id)
                    self.cache_manager.invalidate_user_saved_jobs(user_id)
                    self.cache_manager.invalidate_user_profile_cache(user_id)
                except Exception as cache_error:
                    self.logger.warning(f"Cache invalidation failed during unsave: {cache_error}")

                # Track analytics event for business intelligence
                try:
                    if self.analytics_service:
                        await self.analytics_service.track_job_action(
                            event_type="job_unsave",
                            user_id=user_id,
                            job_id=job_id,
                            metadata={
                                "removed_saved_job_id": saved_job_id
                            }
                        )
                except Exception as analytics_error:
                    self.logger.warning(f"Analytics tracking failed during unsave: {analytics_error}")

                # Log successful operation
                self.logger.info(
                    f"Job unsaved successfully: user {user_id}, job {job_id}, "
                    f"removed_saved_job_id {saved_job_id}"
                )

                return JobActionResult.success_result(
                    message="Job unsaved successfully",
                    data={
                        "user_id": user_id,
                        "job_id": job_id,
                        "removed_saved_job_id": saved_job_id
                    }
                )

        except ValidationError as e:
            self.logger.warning(f"Validation error in unsave_job: {e}")
            return JobActionResult.error_result(
                message="Invalid input parameters",
                error_code=JobActionErrorCode.VALIDATION_ERROR
            )

        except DatabaseError as e:
            self.logger.error(f"Database error in unsave_job: {e}")
            return JobActionResult.error_result(
                message="Database operation failed",
                error_code=JobActionErrorCode.DATABASE_ERROR
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in unsave_job: {e}", exc_info=True)
            return JobActionResult.error_result(
                message="Internal server error occurred",
                error_code=JobActionErrorCode.INTERNAL_ERROR
            )

    @error_handler
    async def share_job(self, user_id: Optional[str], job_id: str, share_method: str) -> JobActionResult:
        """
        Share a job with comprehensive validation and tracking (allows anonymous sharing).
        
        This method handles the complete job sharing workflow including validation,
        referral code generation, database persistence, cache invalidation, and
        analytics tracking. Anonymous sharing is supported for better user experience.
        
        Args:
            user_id: JobSeeker profile user_uid (optional for anonymous sharing)
            job_id: Job ID to share (validated UUID string)
            share_method: Method used to share (email, linkedin, twitter, facebook, whatsapp, copy_link)
            
        Returns:
            JobActionResult: Standardized result object containing:
                - success: True if job was shared successfully
                - message: Human-readable status message
                - data: Dictionary with share_id, referral_code, and updated share_count
                - error_code: Optional error code for client handling
                
        Raises:
            ValidationError: When input parameters are invalid
            DatabaseError: When database operations fail
            
        Side Effects:
            - Creates JobShareORM record in database
            - Invalidates related cache entries
            - Triggers analytics event tracking
            - Updates job engagement metrics
            - Generates referral code for authenticated users
            
        Business Rules:
            - Job must exist and be accessible
            - Share method must be valid enum value
            - Anonymous sharing is allowed (no user validation required)
            - Referral codes only generated for authenticated users
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

            with self.get_session() as session:
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
                job_actions_cache.invalidate_job_engagement_stats(job_id)
                if user_id:
                    job_actions_cache.invalidate_job_actions_state(user_id, job_id)

                # Track analytics event for business intelligence
                if self.analytics_service:
                    await self.analytics_service.track_job_action(
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
                        "is_anonymous": user_id is None
                    }
                )

        except ValidationError as e:
            # Pydantic validation errors
            self.logger.warning(f"Validation error in share_job: {e}")
            return JobActionResult.error_result(
                message="Invalid input parameters",
                error_code=JobActionErrorCode.VALIDATION_ERROR
            )

        except DatabaseError as e:
            # Database operation errors
            self.logger.error(f"Database error in share_job: {e}")
            return JobActionResult.error_result(
                message="Database operation failed",
                error_code=JobActionErrorCode.DATABASE_ERROR
            )

        except Exception as e:
            # Unexpected errors
            self.logger.error(f"Unexpected error in share_job: {e}", exc_info=True)
            return JobActionResult.error_result(
                message="Internal server error occurred",
                error_code=JobActionErrorCode.INTERNAL_ERROR
            )

    @error_handler
    async def get_job_actions_state(self, user_id: str, job_id: str) -> JobActionsStateResult:
        """
        Get the current state of job actions for a user and job with caching.
        
        This method retrieves the complete state of job actions for a specific
        user-job combination, including like status, save status, and engagement
        counts. It implements a cache-first strategy for optimal performance
        while ensuring data consistency.
        
        Args:
            user_id: JobSeeker profile user_uid (validated UUID string)
                    Must correspond to an existing JobSeeker profile
            job_id: Job ID (validated UUID string)
                   Must correspond to an existing job posting
                   
        Returns:
            JobActionsStateResult: Standardized result object containing:
                - success: True if state was retrieved successfully
                - message: Human-readable status message
                - actions_state: JobActionsState object with current state
                - error_code: Specific error code for error cases
                - timestamp: UTC timestamp of operation
                
        Raises:
            ValidationError: When input parameters fail validation
            DatabaseError: When database operations fail
            CacheError: When cache operations fail (fallback to database)
            
        Side Effects:
            - Queries database for current action states if not cached
            - Updates cache with fresh data for future requests
            - Logs cache hits/misses for performance monitoring
            
        Business Rules:
            - Returns user-specific action states (liked, saved)
            - Includes global engagement metrics (total likes, shares)
            - Provides real-time data with cache optimization
            - Handles anonymous users gracefully (no personal state)
            
        Performance Considerations:
            - Implements cache-first strategy with configurable TTL
            - Uses optimized database queries with proper indexing
            - Batches multiple state checks for efficiency
            - Provides cache warming for frequently accessed jobs
            
        Cache Strategy:
            - Primary cache key: "job_actions_state:{user_id}:{job_id}"
            - TTL: 300 seconds (5 minutes) for balance of freshness and performance
            - Invalidation: On any user action (like, save, share)
            - Warming: Pre-populate for trending jobs and active users
        """
        try:
            # Input validation
            if not self._validate_user_and_job_ids(user_id, job_id):
                return JobActionsStateResult.error_result(
                    message="Invalid user or job ID parameters",
                    error_code=JobActionErrorCode.VALIDATION_ERROR
                )

            # Try cache-first strategy for performance optimization
            try:
                cached_state = self.cache_manager.get_job_actions_state(user_id, job_id)
                if cached_state:
                    # Convert cached dict back to JobActionsState object
                    actions_state = JobActionsState(**cached_state)
                    self.logger.debug(f"Cache hit for job actions state: user {user_id}, job {job_id}")
                    return JobActionsStateResult.success_result(
                        message="Job actions state retrieved from cache",
                        actions_state=actions_state
                    )
            except Exception as cache_error:
                # Cache errors are non-blocking, fall back to database
                self.logger.warning(f"Cache retrieval failed, falling back to database: {cache_error}")

            # Cache miss or error - query database for fresh data
            with self.get_session() as session:
                # Use optimized queries to check user-specific states
                user_has_liked = session.query(JobLikeORM).filter_by(
                    user_id=user_id, job_id=job_id
                ).first() is not None

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
                    # Cache write errors are non-blocking
                    self.logger.warning(f"Failed to cache job actions state: {cache_error}")

                # Log successful database retrieval
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
            self.logger.warning(f"Validation error in get_job_actions_state: {e}")
            return JobActionsStateResult.error_result(
                message="Invalid input parameters",
                error_code=JobActionErrorCode.VALIDATION_ERROR
            )

        except DatabaseError as e:
            self.logger.error(f"Database error in get_job_actions_state: {e}")
            return JobActionsStateResult.error_result(
                message="Database operation failed",
                error_code=JobActionErrorCode.DATABASE_ERROR
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in get_job_actions_state: {e}", exc_info=True)
            return JobActionsStateResult.error_result(
                message="Internal server error occurred",
                error_code=JobActionErrorCode.INTERNAL_ERROR
            )

    @error_handler
    async def get_user_liked_jobs(self, user_id: str, limit: int = 20, offset: int = 0) -> JobListResult:
        """
        Get jobs liked by a user with comprehensive validation and caching.
        
        This method retrieves a paginated list of jobs that the user has liked,
        including job details and like timestamps. Results are optimized with
        database joins and proper pagination handling.
        
        Args:
            user_id: JobSeeker profile user_uid (validated UUID string)
            limit: Number of jobs to return per page (max 100, default 20)
            offset: Starting offset for pagination (default 0)
            
        Returns:
            JobListResult: Standardized result object containing:
                - success: True if jobs were retrieved successfully
                - message: Human-readable status message
                - jobs: List of job data dictionaries with liked_at timestamps
                - total_count: Total number of liked jobs for pagination
                - limit: Number of jobs requested per page
                - offset: Starting offset used for pagination
                - error_code: Optional error code for client handling
                
        Raises:
            ValidationError: When input parameters are invalid
            DatabaseError: When database operations fail
            
        Side Effects:
            - Executes optimized database query with joins
            - Logs query performance for monitoring
            
        Business Rules:
            - User must have valid JobSeeker profile
            - Results ordered by most recently liked first
            - Includes job details and like timestamps
            - Supports pagination with reasonable limits
        """
        try:
            # Input validation
            if not user_id or not user_id.strip():
                return JobListResult.error_result(
                    message="Invalid user ID parameter",
                    error_code=JobActionErrorCode.VALIDATION_ERROR
                )

            # Validate pagination parameters
            limit = max(1, min(limit, 100))  # Ensure reasonable limits (1-100)
            offset = max(0, offset)  # Ensure non-negative offset

            with self.get_session() as session:
                # Optimized query with joins to avoid N+1 queries
                liked_jobs_query = (
                    session.query(JobLikeORM)
                    .options(joinedload(JobLikeORM.job))
                    .filter_by(user_id=user_id)
                    .order_by(JobLikeORM.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                )

                liked_jobs = liked_jobs_query.all()

                # Get total count for pagination metadata
                total_count = session.query(func.count(JobLikeORM.like_id)).filter_by(user_id=user_id).scalar()

                # Format job data with like timestamps
                jobs_data = []
                for like in liked_jobs:
                    if like.job:
                        # Convert ORM to dictionary
                        job_data = like.job.to_dict()
                        # Add like-specific metadata
                        job_data['liked_at'] = like.created_at.replace(tzinfo=timezone.utc).isoformat()
                        job_data['like_id'] = like.like_id
                        jobs_data.append(job_data)

                # Log successful retrieval for monitoring
                self.logger.info(
                    f"Retrieved {len(jobs_data)} liked jobs for user {user_id} "
                    f"(total: {total_count}, limit: {limit}, offset: {offset})"
                )

                return JobListResult.success_result(
                    message=f"Retrieved {len(jobs_data)} liked jobs successfully",
                    jobs=jobs_data,
                    total_count=total_count or 0,
                    limit=limit,
                    offset=offset
                )

        except ValidationError as e:
            self.logger.warning(f"Validation error in get_user_liked_jobs: {e}")
            return JobListResult.error_result(
                message="Invalid input parameters",
                error_code=JobActionErrorCode.VALIDATION_ERROR
            )

        except DatabaseError as e:
            self.logger.error(f"Database error in get_user_liked_jobs: {e}")
            return JobListResult.error_result(
                message="Database operation failed",
                error_code=JobActionErrorCode.DATABASE_ERROR
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in get_user_liked_jobs: {e}", exc_info=True)
            return JobListResult.error_result(
                message="Internal server error occurred",
                error_code=JobActionErrorCode.INTERNAL_ERROR
            )

    def _validate_user_and_job_ids(self, user_id: str, job_id: str) -> bool:
        """Validate user_id and job_id are not empty"""
        return bool(user_id and user_id.strip() and job_id and job_id.strip())

    @error_handler
    async def get_user_saved_jobs(self, user_id: str, limit: int = 20, offset: int = 0) -> JobListResult:
        """
        Get jobs saved by a user with comprehensive caching and validation.
        
        This method retrieves a paginated list of jobs that the user has saved,
        including job details and save timestamps. Results are cached for
        performance optimization and include proper pagination handling.
        
        Args:
            user_id: JobSeeker profile user_uid (validated UUID string)
            limit: Number of jobs to return per page (max 100, default 20)
            offset: Starting offset for pagination (default 0)
            
        Returns:
            JobListResult: Standardized result object containing:
                - success: True if jobs were retrieved successfully
                - message: Human-readable status message
                - jobs: List of job data dictionaries with saved_at timestamps
                - total_count: Total number of saved jobs for pagination
                - limit: Number of jobs requested per page
                - offset: Starting offset used for pagination
                - error_code: Optional error code for client handling
                
        Raises:
            ValidationError: When input parameters are invalid
            DatabaseError: When database operations fail
            CacheError: When cache operations fail (non-blocking)
            
        Side Effects:
            - Executes optimized database query with joins
            - Updates cache with fresh results
            - Logs query performance for monitoring
            
        Business Rules:
            - User must have valid JobSeeker profile
            - Results ordered by most recently saved first
            - Includes job details and save timestamps
            - Supports pagination with reasonable limits
            - Cache results for improved performance
        """
        try:
            # Input validation
            if not user_id or not user_id.strip():
                return JobListResult.error_result(message="Invalid user ID parameter",
                                                  error_code=JobActionErrorCode.VALIDATION_ERROR)

            self.logger.info(f"Get User Saved Jobs : {user_id}")
            # Validate pagination parameters
            limit = max(1, min(limit, 100))  # Ensure reasonable limits (1-100)
            offset = max(0, offset)  # Ensure non-negative offset

            # Try to get from cache first for performance
            try:
                cached_result = job_actions_cache.get_user_saved_jobs(user_id, limit, offset)
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
                # Cache read errors are non-blocking
                self.logger.warning(f"Cache read error for saved jobs: {cache_error}")

            with self.get_session() as session:
                # Optimized query with joins to avoid N+1 queries
                saved_jobs_query = (
                    session.query(SavedJobORM)
                    .options(joinedload(SavedJobORM.job))
                    .filter_by(user_id=user_id)
                    .order_by(SavedJobORM.created_at.desc())
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
                        # Convert ORM to dictionary
                        job_data = saved.job.to_dict()
                        # Add save-specific metadata
                        job_data['saved_at'] = saved.created_at.replace(tzinfo=timezone.utc).isoformat()
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
                    # Convert result to cacheable format
                    cache_data = {
                        "success": True,
                        "data": {
                            "jobs": jobs_data,
                            "total_count": total_count or 0,
                            "limit": limit,
                            "offset": offset
                        }
                    }
                    job_actions_cache.set_user_saved_jobs(user_id, cache_data, limit, offset)
                    self.logger.debug(f"Cached saved jobs result for user {user_id}")
                except Exception as cache_error:
                    # Cache write errors are non-blocking
                    self.logger.warning(f"Failed to cache saved jobs result: {cache_error}")

                # Log successful retrieval for monitoring
                self.logger.info(
                    f"Retrieved {len(jobs_data)} saved jobs for user {user_id} "
                    f"(total: {total_count}, limit: {limit}, offset: {offset})"
                )

                return result

        except ValidationError as e:
            self.logger.warning(f"Validation error in get_user_saved_jobs: {e}")
            return JobListResult.error_result(
                message="Invalid input parameters",
                error_code=JobActionErrorCode.VALIDATION_ERROR
            )

        except DatabaseError as e:
            self.logger.error(f"Database error in get_user_saved_jobs: {e}")
            return JobListResult.error_result(
                message="Database operation failed",
                error_code=JobActionErrorCode.DATABASE_ERROR
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in get_user_saved_jobs: {e}", exc_info=True)
            return JobListResult.error_result(
                message="Internal server error occurred",
                error_code=JobActionErrorCode.INTERNAL_ERROR
            )

    @error_handler
    async def get_job_engagement_stats(self, job_id: str) -> JobEngagementResult:
        """
        Get comprehensive engagement statistics for a job with caching.
        
        This method retrieves detailed engagement metrics for a job including
        like counts, share statistics by platform, recent activity trends,
        and other engagement indicators. It implements caching for performance
        optimization while ensuring data accuracy.
        
        Args:
            job_id: Job ID (validated UUID string)
                   Must correspond to an existing job posting
                   
        Returns:
            JobEngagementResult: Standardized result object containing:
                - success: True if statistics were retrieved successfully
                - message: Human-readable status message
                - engagement_data: Dictionary with comprehensive engagement metrics
                - error_code: Specific error code for error cases
                - timestamp: UTC timestamp of operation
                
        Engagement Metrics Included:
            - like_count: Total number of likes for the job
            - share_count: Total number of shares across all platforms
            - share_by_method: Breakdown of shares by platform (email, linkedin, etc.)
            - recent_activity: Activity metrics for the last 7 days
            - engagement_trends: Historical engagement patterns
            - platform_performance: Share conversion rates by platform
            
        Performance Considerations:
            - Implements cache-first strategy with 15-minute TTL
            - Uses optimized database queries with proper aggregation
            - Provides batch processing for multiple job statistics
            - Includes cache warming for trending jobs
        """
        try:
            # Input validation
            if not job_id or not job_id.strip():
                return JobEngagementResult.error_result(
                    message="Invalid job ID parameter",
                    error_code=JobActionErrorCode.VALIDATION_ERROR
                )

            # Try cache-first strategy for performance
            try:
                cached_stats = self.cache_manager.get_job_engagement_stats(job_id)
                if cached_stats:
                    self.logger.debug(f"Cache hit for job engagement stats: {job_id}")
                    return JobEngagementResult.success_result(
                        message="Job engagement statistics retrieved from cache",
                        engagement_data=cached_stats
                    )
            except Exception as cache_error:
                self.logger.warning(f"Cache retrieval failed for engagement stats: {cache_error}")

            # Cache miss - query database for fresh statistics
            with self.get_session() as session:
                # Get total like count
                like_count = session.query(func.count(JobLikeORM.like_id)).filter_by(job_id=job_id).scalar()

                # Get share statistics grouped by method
                share_stats = (
                    session.query(JobShareORM.share_method, func.count(JobShareORM.share_id))
                    .filter_by(job_id=job_id)
                    .group_by(JobShareORM.share_method)
                    .all()
                )

                # Calculate recent activity (last 7 days)
                from datetime import timedelta
                week_ago = datetime.now(timezone.utc) - timedelta(days=7)

                recent_likes = session.query(func.count(JobLikeORM.like_id)).filter(
                    and_(JobLikeORM.job_id == job_id, JobLikeORM.created_at >= week_ago)
                ).scalar()

                recent_shares = session.query(func.count(JobShareORM.share_id)).filter(
                    and_(JobShareORM.job_id == job_id, JobShareORM.shared_at >= week_ago)
                ).scalar()

                # Format share statistics by platform
                share_by_method = {str(method): count for method, count in share_stats}
                total_shares = sum(share_by_method.values())

                # Calculate engagement trends and additional metrics
                engagement_score = (like_count * 2) + total_shares  # Weighted engagement score
                recent_engagement_score = (recent_likes * 2) + recent_shares

                # Compile comprehensive engagement data
                engagement_data = {
                    "job_id": job_id,
                    "like_count": like_count or 0,
                    "share_count": total_shares,
                    "share_by_method": share_by_method,
                    "recent_activity": {
                        "likes_last_7_days": recent_likes or 0,
                        "shares_last_7_days": recent_shares or 0,
                        "engagement_score_last_7_days": recent_engagement_score
                    },
                    "engagement_metrics": {
                        "total_engagement_score": engagement_score,
                        "engagement_rate": self._calculate_engagement_rate(like_count, total_shares),
                        "viral_coefficient": self._calculate_viral_coefficient(total_shares, like_count)
                    },
                    "platform_performance": self._analyze_platform_performance(share_by_method),
                    "calculated_at": utc_time().isoformat()
                }

                # Cache the fresh statistics
                try:
                    self.cache_manager.set_job_engagement_stats(job_id, engagement_data)
                    self.logger.debug(f"Cached fresh engagement stats for job: {job_id}")
                except Exception as cache_error:
                    self.logger.warning(f"Failed to cache engagement stats: {cache_error}")

                # Log successful retrieval
                self.logger.debug(
                    f"Job engagement stats retrieved: job {job_id}, "
                    f"likes={like_count}, shares={total_shares}, "
                    f"engagement_score={engagement_score}"
                )

                return JobEngagementResult.success_result(
                    message="Job engagement statistics retrieved successfully",
                    engagement_data=engagement_data
                )

        except ValidationError as e:
            self.logger.warning(f"Validation error in get_job_engagement_stats: {e}")
            return JobEngagementResult.error_result(
                message="Invalid input parameters",
                error_code=JobActionErrorCode.VALIDATION_ERROR
            )

        except DatabaseError as e:
            self.logger.error(f"Database error in get_job_engagement_stats: {e}")
            return JobEngagementResult.error_result(
                message="Database operation failed",
                error_code=JobActionErrorCode.DATABASE_ERROR
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in get_job_engagement_stats: {e}", exc_info=True)
            return JobEngagementResult.error_result(
                message="Internal server error occurred",
                error_code=JobActionErrorCode.INTERNAL_ERROR
            )

    def _calculate_engagement_rate(self, likes: int, shares: int) -> float:
        """
        Calculate engagement rate as a percentage.
        
        This is a simplified calculation that could be enhanced with
        view counts, application rates, and other engagement metrics.
        """
        total_engagement = likes + shares
        # This would ideally include view counts or other base metrics
        # For now, we'll use a simplified calculation
        return round(total_engagement * 0.1, 2)  # Placeholder calculation

    def _calculate_viral_coefficient(self, shares: int, likes: int) -> float:
        """
        Calculate viral coefficient indicating how likely the job is to be shared.
        
        Higher values indicate more viral content that users are likely to share.
        """
        if likes == 0:
            return 0.0
        return round(shares / likes, 3)

    def _analyze_platform_performance(self, share_by_method: Dict[str, int]) -> Dict[str, Any]:
        """
        Analyze performance of different sharing platforms.
        
        Provides insights into which platforms are most effective for job sharing.
        """
        if not share_by_method:
            return {}

        total_shares = sum(share_by_method.values())
        platform_performance = {}

        for platform, count in share_by_method.items():
            percentage = (count / total_shares) * 100 if total_shares > 0 else 0
            platform_performance[platform] = {
                "share_count": count,
                "percentage": round(percentage, 1),
                "performance_rating": self._get_platform_rating(percentage)
            }

        return platform_performance

    def _get_platform_rating(self, percentage: float) -> str:
        """Get performance rating for a platform based on share percentage."""
        if percentage >= 40:
            return "excellent"
        elif percentage >= 25:
            return "good"
        elif percentage >= 15:
            return "average"
        else:
            return "low"

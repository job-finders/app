"""
Job Actions Enhanced Error Handler

Comprehensive error handling and logging utilities for job actions operations.
This module provides enhanced error handling patterns, security event logging,
performance monitoring, and standardized error response formatting.

This module follows the established architecture patterns:
- Integrates with existing logging infrastructure
- Provides security event logging for suspicious activities
- Implements performance monitoring for slow operations
- Standardizes error response formats across all operations
"""

import time
import traceback
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime
from contextlib import contextmanager

from flask import request, g
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, DatabaseError, OperationalError

from src.database.models.job_actions_results import JobActionResult, JobActionErrorCode
from src.database.constants import utc_time
from src.utils.job_actions_logger import job_actions_logger
from src.utils.route_helpers import get_service


class JobActionsErrorContext:
    """
    Context manager for enhanced error handling with performance monitoring.
    
    Provides comprehensive error tracking, performance monitoring, and
    security event logging for job actions operations.
    """

    def __init__(self, operation_name: str, user_id: Optional[str] = None,
                 job_id: Optional[str] = None, additional_context: Optional[Dict] = None):
        """
        Initialize error context for operation monitoring.
        
        Args:
            operation_name: Name of the operation being performed
            user_id: Optional user ID for security logging
            job_id: Optional job ID for context
            additional_context: Additional context data for logging
        """
        self.operation_name = operation_name
        self.user_id = user_id
        self.job_id = job_id
        self.additional_context = additional_context or {}
        self.start_time = None
        self.logger = job_actions_logger

    def __enter__(self):
        """Start operation monitoring"""
        self.start_time = time.time()

        # Log operation start for audit trail
        self.logger.log_user_action(
            action=f"{self.operation_name}_start",
            user_id=self.user_id or "anonymous",
            job_id=self.job_id or "unknown",
            additional_data={
                "operation": self.operation_name,
                "context": self.additional_context,
                "request_id": getattr(g, 'request_id', None),
                "ip_address": getattr(request, 'remote_addr', None) if request else None
            }
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Handle operation completion and error logging"""
        duration = time.time() - self.start_time if self.start_time else 0

        if exc_type is None:
            # Successful operation
            self.logger.log_performance(
                operation=self.operation_name,
                duration=duration,
                additional_metrics={
                    "success": True,
                    "user_id": self.user_id,
                    "job_id": self.job_id
                }
            )

            self.logger.log_user_action(
                action=f"{self.operation_name}_success",
                user_id=self.user_id or "anonymous",
                job_id=self.job_id or "unknown",
                additional_data={
                    "duration_ms": round(duration * 1000, 2),
                    "context": self.additional_context
                }
            )
        else:
            # Error occurred
            self._handle_error(exc_type, exc_val, exc_tb, duration)

        return False  # Don't suppress exceptions

    def _handle_error(self, exc_type, exc_val, exc_tb, duration: float):
        """Handle error logging and security event detection"""
        error_context = {
            "operation": self.operation_name,
            "user_id": self.user_id,
            "job_id": self.job_id,
            "duration_ms": round(duration * 1000, 2),
            "error_type": exc_type.__name__,
            "error_message": str(exc_val),
            "traceback": traceback.format_exception(exc_type, exc_val, exc_tb),
            "context": self.additional_context,
            "request_id": getattr(g, 'request_id', None),
            "ip_address": getattr(request, 'remote_addr', None) if request else None
        }

        # Log error with full context
        self.logger.log_error(exc_val, error_context)

        # Log performance for failed operations
        self.logger.log_performance(
            operation=self.operation_name,
            duration=duration,
            additional_metrics={
                "success": False,
                "error_type": exc_type.__name__,
                "user_id": self.user_id,
                "job_id": self.job_id
            }
        )

        # Detect and log security events
        self._detect_security_events(exc_type, exc_val, error_context)

    def _detect_security_events(self, exc_type, exc_val, context: Dict):
        """Detect potential security events and log them"""
        security_indicators = []

        # Detect potential SQL injection attempts
        if isinstance(exc_val, DatabaseError):
            error_msg = str(exc_val).lower()
            if any(keyword in error_msg for keyword in ['union', 'select', 'drop', 'insert', 'update', 'delete']):
                security_indicators.append("potential_sql_injection")

        # Detect validation bypass attempts
        if isinstance(exc_val, ValidationError):
            validation_errors = str(exc_val).lower()
            if any(keyword in validation_errors for keyword in ['script', 'javascript', 'eval', 'exec']):
                security_indicators.append("potential_xss_attempt")

        # Detect rapid repeated failures (potential brute force)
        if self.user_id and hasattr(g, 'user_error_count'):
            g.user_error_count = getattr(g, 'user_error_count', 0) + 1
            if g.user_error_count > 10:  # More than 10 errors in a request
                security_indicators.append("rapid_repeated_failures")

        # Detect unusual job ID patterns (potential enumeration)
        if self.job_id and not self._is_valid_uuid_format(self.job_id):
            security_indicators.append("invalid_job_id_format")

        # Log security events if detected
        if security_indicators:
            self.logger.log_security_event(
                event_type="suspicious_activity_detected",
                user_id=self.user_id,
                ip_address=context.get("ip_address"),
                additional_data={
                    "indicators": security_indicators,
                    "operation": self.operation_name,
                    "error_type": exc_type.__name__,
                    "context": context
                }
            )

    def _is_valid_uuid_format(self, uuid_string: str) -> bool:
        """Check if string matches UUID format"""
        import uuid
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False


def enhanced_error_handler(operation_name: str):
    """
    Enhanced error handler decorator with comprehensive logging and monitoring.
    
    This decorator provides:
    - Performance monitoring with duration tracking
    - Security event detection and logging
    - Comprehensive error context logging
    - Standardized error response formatting
    - Integration with existing monitoring systems
    
    Args:
        operation_name: Name of the operation for logging and monitoring
        
    Returns:
        Decorated function with enhanced error handling
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract context information
            user_id = kwargs.get('user_id') or (args[1] if len(args) > 1 else None)
            job_id = kwargs.get('job_id') or (args[2] if len(args) > 2 else None)

            # Additional context from function arguments
            additional_context = {
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            }

            # Use enhanced error context manager
            with JobActionsErrorContext(
                    operation_name=operation_name,
                    user_id=user_id,
                    job_id=job_id,
                    additional_context=additional_context
            ):
                try:
                    # Execute the original function
                    result = await func(*args, **kwargs)

                    # Log successful operation details
                    if hasattr(result, 'success') and result.success:
                        job_actions_logger.log_analytics_event(
                            event_type=f"{operation_name}_completed",
                            data={
                                "user_id": user_id,
                                "job_id": job_id,
                                "result_data": getattr(result, 'data', None)
                            }
                        )

                    return result

                except ValidationError as e:
                    # Handle Pydantic validation errors
                    return JobActionResult.error_result(
                        message=f"Input validation failed: {str(e)}",
                        error_code=JobActionErrorCode.VALIDATION_ERROR,
                        data={"validation_details": str(e)}
                    )

                except IntegrityError as e:
                    # Handle database constraint violations
                    error_msg = "Database constraint violation"
                    error_code = JobActionErrorCode.DATABASE_ERROR

                    # Provide more specific error messages for common constraints
                    if "duplicate" in str(e).lower():
                        if "like" in operation_name.lower():
                            error_msg = "Job already liked by user"
                            error_code = JobActionErrorCode.ALREADY_LIKED
                        elif "save" in operation_name.lower():
                            error_msg = "Job already saved by user"
                            error_code = JobActionErrorCode.ALREADY_SAVED

                    return JobActionResult.error_result(
                        message=error_msg,
                        error_code=error_code
                    )

                except OperationalError as e:
                    # Handle database connectivity issues
                    return JobActionResult.error_result(
                        message="Database connection error - please try again",
                        error_code=JobActionErrorCode.DATABASE_ERROR
                    )

                except DatabaseError as e:
                    # Handle other database errors
                    return JobActionResult.error_result(
                        message="Database operation failed",
                        error_code=JobActionErrorCode.DATABASE_ERROR
                    )

                except Exception as e:
                    # Handle unexpected errors
                    return JobActionResult.error_result(
                        message="An unexpected error occurred",
                        error_code=JobActionErrorCode.INTERNAL_ERROR
                    )

        return wrapper

    return decorator


class SecurityEventDetector:
    """
    Detects and logs security-related events in job actions operations.
    
    This class provides methods for detecting various types of security
    threats and suspicious activities in job actions operations.
    """

    def __init__(self):
        self.logger = job_actions_logger
        self.suspicious_patterns = {
            'sql_injection': ['union', 'select', 'drop', 'insert', 'update', 'delete', '--', ';'],
            'xss_attempt': ['<script', 'javascript:', 'eval(', 'exec(', 'onload=', 'onerror='],
            'path_traversal': ['../', '..\\', '/etc/', '/proc/', 'c:\\'],
            'command_injection': ['|', '&&', '||', ';', '`', '$()']
        }

    def detect_suspicious_input(self, input_data: Dict[str, Any], user_id: Optional[str] = None) -> List[str]:
        """
        Detect suspicious patterns in input data.
        
        Args:
            input_data: Dictionary of input parameters to analyze
            user_id: Optional user ID for logging context
            
        Returns:
            List of detected security indicators
        """
        indicators = []

        for key, value in input_data.items():
            if isinstance(value, str):
                value_lower = value.lower()

                # Check for various attack patterns
                for attack_type, patterns in self.suspicious_patterns.items():
                    if any(pattern in value_lower for pattern in patterns):
                        indicators.append(f"{attack_type}_in_{key}")

                        # Log security event
                        self.logger.log_security_event(
                            event_type=f"suspicious_input_{attack_type}",
                            user_id=user_id,
                            additional_data={
                                "field": key,
                                "value": value[:100],  # Truncate for logging
                                "attack_type": attack_type,
                                "detected_patterns": [p for p in patterns if p in value_lower]
                            }
                        )

        return indicators

    def detect_rate_limit_violation(self, user_id: str, operation: str,
                                    time_window_minutes: int = 5, max_operations: int = 50) -> bool:
        """
        Detect potential rate limit violations.
        
        Args:
            user_id: User performing the operations
            operation: Type of operation being performed
            time_window_minutes: Time window for rate limiting
            max_operations: Maximum operations allowed in time window
            
        Returns:
            True if rate limit violation detected
        """
        # This would integrate with a rate limiting service
        # For now, we'll log the check
        self.logger.log_analytics_event(
            event_type="rate_limit_check",
            data={
                "user_id": user_id,
                "operation": operation,
                "time_window_minutes": time_window_minutes,
                "max_operations": max_operations
            }
        )

        # Return False for now - would implement actual rate limiting logic
        return False

    def log_access_pattern(self, user_id: str, job_id: str, operation: str):
        """
        Log user access patterns for anomaly detection.
        
        Args:
            user_id: User performing the operation
            job_id: Job being accessed
            operation: Type of operation
        """
        self.logger.log_analytics_event(
            event_type="access_pattern",
            data={
                "user_id": user_id,
                "job_id": job_id,
                "operation": operation,
                "timestamp": utc_time().isoformat(),
                "ip_address": getattr(request, 'remote_addr', None) if request else None
            }
        )


# Global security event detector instance
security_detector = SecurityEventDetector()


@contextmanager
def performance_monitoring(operation_name: str, threshold_ms: float = 1000.0):
    """
    Context manager for performance monitoring with alerting.
    
    Args:
        operation_name: Name of the operation being monitored
        threshold_ms: Performance threshold in milliseconds for alerting
    """
    start_time = time.time()

    try:
        yield
    finally:
        duration = time.time() - start_time
        duration_ms = duration * 1000

        # Log performance metrics
        job_actions_logger.log_performance(
            operation=operation_name,
            duration=duration,
            additional_metrics={
                "threshold_ms": threshold_ms,
                "exceeded_threshold": duration_ms > threshold_ms
            }
        )

        # Alert if performance threshold exceeded
        if duration_ms > threshold_ms:
            job_actions_logger.log_security_event(
                event_type="performance_threshold_exceeded",
                additional_data={
                    "operation": operation_name,
                    "duration_ms": duration_ms,
                    "threshold_ms": threshold_ms,
                    "severity": "high" if duration_ms > threshold_ms * 2 else "medium"
                }
            )

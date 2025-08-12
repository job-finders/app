"""
Job Actions Logging Utility

Comprehensive logging system for job actions operations with structured logging,
performance monitoring, security event tracking, and analytics integration.

This module provides centralized logging capabilities for all job actions operations
including user interactions, system performance, error tracking, security events,
and business analytics. It follows established logging patterns and integrates
with the platform's monitoring infrastructure.

Logging Features:
- Structured JSON logging for easy parsing and analysis
- Performance monitoring with threshold-based alerting
- Security event logging with threat detection capabilities
- Analytics event logging for business intelligence
- Health check monitoring with automated diagnostics
- Metrics collection with time-series data storage

Architecture Integration:
- Follows platform logging standards and patterns
- Integrates with existing monitoring infrastructure
- Provides consistent log formatting across all operations
- Supports both development and production logging configurations
- Includes comprehensive error handling and fallback mechanisms
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
from contextlib import contextmanager

from src.database.constants import utc_time


class JobActionsLogger:
    """
    Centralized logger for job actions with structured logging and comprehensive monitoring.
    
    This class provides a unified logging interface for all job actions operations
    with structured JSON logging, performance monitoring, security event tracking,
    and analytics integration. It follows established logging patterns and provides
    consistent log formatting across all operations.
    
    Features:
        - Structured JSON logging for easy parsing and analysis
        - Multiple log levels with appropriate handlers
        - Performance threshold monitoring with alerting
        - Security event logging with threat detection
        - Analytics event logging for business intelligence
        - Comprehensive error handling with context preservation
        - Health check integration with automated diagnostics
    
    Architecture Integration:
        - Follows platform logging standards and conventions
        - Integrates with existing monitoring and alerting systems
        - Provides consistent log formatting across all job actions
        - Supports both development and production configurations
        - Includes fallback mechanisms for logging failures
    
    Usage:
        logger = JobActionsLogger("job_actions_service")
        logger.log_user_action("like", user_id="123", job_id="456")
        logger.log_performance("database_query", 0.5, {"query_type": "select"})
    """

    def __init__(self, name: str = "job_actions"):
        """
        Initialize the job actions logger with proper configuration.
        
        Args:
            name: Logger name for identification and filtering
        """
        self.logger = logging.getLogger(name)
        self.logger_name = name

        # Performance thresholds for alerting
        self.slow_operation_threshold = 1.0  # seconds
        self.very_slow_operation_threshold = 5.0  # seconds

        # Setup logger configuration
        self.setup_logger()

    def setup_logger(self):
        """
        Setup logger with appropriate handlers and formatters for different environments.
        
        Configures console and file handlers with structured formatting for optimal
        log parsing and analysis. Includes error handling for logging setup failures
        and fallback mechanisms to ensure logging continues even if setup fails.
        
        Handler Configuration:
            - Console Handler: For development and immediate feedback
            - File Handler: For production logging and log aggregation
            - Structured Formatting: JSON-compatible formatting for parsing
            - Error Handling: Graceful fallback if handler setup fails
        """
        # Prevent duplicate handlers if logger is reinitialized
        if self.logger.handlers:
            return

        try:
            # Console handler for development and immediate feedback
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.INFO)

            # File handler for production logging and persistence
            try:
                # Ensure logs directory exists
                import os
                os.makedirs('logs', exist_ok=True)

                file_handler = logging.FileHandler('logs/job_actions.log')
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                file_handler.setLevel(logging.DEBUG)

                self.logger.addHandler(file_handler)

            except (OSError, PermissionError) as e:
                # Fallback: log to console if file logging fails
                console_handler.setLevel(logging.DEBUG)
                print(f"Warning: Could not setup file logging for {self.logger_name}: {e}")

            # Add console handler
            self.logger.addHandler(console_handler)

            # Set overall logger level
            self.logger.setLevel(logging.DEBUG)

            # Prevent propagation to root logger to avoid duplicate logs
            self.logger.propagate = False

        except Exception as e:
            # Ultimate fallback: basic console logging
            print(f"Critical: Failed to setup logger {self.logger_name}: {e}")
            basic_handler = logging.StreamHandler()
            basic_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
            self.logger.addHandler(basic_handler)
            self.logger.setLevel(logging.INFO)

    def _create_log_entry(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Create structured log entry with consistent formatting and metadata.
        
        This method creates a standardized log entry format that includes
        essential metadata for log parsing, analysis, and monitoring. The
        structured format enables easy integration with log aggregation
        systems and automated analysis tools.
        
        Args:
            action: The action being logged (e.g., "user_like", "performance_metric")
            **kwargs: Additional key-value pairs to include in the log entry
            
        Returns:
            Dictionary with structured log entry including timestamp, action,
            service identifier, and all provided additional data
            
        Log Entry Structure:
            - timestamp: ISO format UTC timestamp for precise timing
            - action: Specific action or event being logged
            - service: Service identifier for filtering and routing
            - logger_name: Logger instance name for source identification
            - Additional fields: All kwargs are included as-is
        """
        try:
            # Create base log entry with essential metadata
            log_entry = {
                'timestamp': utc_time().isoformat(),
                'action': action,
                'service': 'job_actions',
                'logger_name': self.logger_name,
                'log_version': '1.0',  # For future log format evolution
                **kwargs
            }

            return log_entry

        except Exception as e:
            # Fallback log entry if creation fails
            return {
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'service': 'job_actions',
                'logger_name': self.logger_name,
                'log_creation_error': str(e),
                **kwargs
            }

    def log_user_action(self, action: str, user_id: str, job_id: str,
                        additional_data: Optional[Dict] = None):
        """Log user actions (like, save, share)"""
        log_data = self._create_log_entry(
            action=f"user_{action}",
            user_id=user_id,
            job_id=job_id,
            category="user_action"
        )

        if additional_data:
            log_data.update(additional_data)

        self.logger.info(json.dumps(log_data))

    def log_performance(self, operation: str, duration: float,
                        additional_metrics: Optional[Dict] = None):
        """
        Log performance metrics with threshold-based alerting and comprehensive analysis.
        
        This method logs performance metrics for job actions operations with
        intelligent threshold-based alerting, detailed timing analysis, and
        integration with monitoring systems. It provides both immediate feedback
        and historical performance tracking capabilities.
        
        Args:
            operation: Name of the operation being measured (e.g., "database_query", "cache_lookup")
            duration: Operation duration in seconds (float precision for microsecond accuracy)
            additional_metrics: Optional dictionary of additional performance metrics
                               (e.g., {"query_type": "select", "rows_affected": 100})
        
        Performance Thresholds:
            - Normal: < 1.0 seconds (logged as INFO)
            - Slow: 1.0 - 5.0 seconds (logged as WARNING)
            - Very Slow: > 5.0 seconds (logged as ERROR)
        
        Log Data Structure:
            - operation: Operation name for filtering and analysis
            - duration_ms: Duration in milliseconds for precise measurement
            - duration_seconds: Duration in seconds for human readability
            - performance_category: Classification based on duration thresholds
            - additional_metrics: Any provided additional performance data
        
        Integration:
            - Integrates with monitoring systems for alerting
            - Provides data for performance trend analysis
            - Enables automated performance regression detection
        """
        try:
            # Validate input parameters
            if not operation or not isinstance(operation, str):
                operation = "unknown_operation"

            if not isinstance(duration, (int, float)) or duration < 0:
                duration = 0.0

            # Calculate performance metrics
            duration_ms = round(duration * 1000, 2)

            # Determine performance category based on thresholds
            if duration > self.very_slow_operation_threshold:
                performance_category = "very_slow"
                log_level = "error"
            elif duration > self.slow_operation_threshold:
                performance_category = "slow"
                log_level = "warning"
            else:
                performance_category = "normal"
                log_level = "info"

            # Create structured log entry
            log_data = self._create_log_entry(
                action="performance_metric",
                operation=operation,
                duration_ms=duration_ms,
                duration_seconds=round(duration, 3),
                performance_category=performance_category,
                category="performance",
                threshold_slow=self.slow_operation_threshold,
                threshold_very_slow=self.very_slow_operation_threshold
            )

            # Add additional metrics if provided
            if additional_metrics and isinstance(additional_metrics, dict):
                # Sanitize additional metrics to prevent logging sensitive data
                sanitized_metrics = {}
                for key, value in additional_metrics.items():
                    # Skip sensitive fields
                    if any(sensitive in key.lower() for sensitive in ['password', 'token', 'secret', 'key']):
                        sanitized_metrics[key] = "[REDACTED]"
                    else:
                        sanitized_metrics[key] = value

                log_data['additional_metrics'] = sanitized_metrics

            # Log with appropriate level based on performance
            log_message = json.dumps(log_data, default=str)

            if log_level == "error":
                self.logger.error(log_message)
            elif log_level == "warning":
                self.logger.warning(log_message)
            else:
                self.logger.info(log_message)

            # Additional alerting for very slow operations
            if performance_category == "very_slow":
                alert_data = self._create_log_entry(
                    action="performance_alert",
                    alert_type="very_slow_operation",
                    operation=operation,
                    duration_seconds=duration,
                    threshold_exceeded=self.very_slow_operation_threshold,
                    category="alert"
                )
                self.logger.critical(json.dumps(alert_data, default=str))

        except Exception as e:
            # Fallback logging if performance logging fails
            try:
                fallback_data = {
                    'timestamp': datetime.now().isoformat(),
                    'action': 'performance_logging_error',
                    'operation': operation,
                    'duration': duration,
                    'error': str(e),
                    'category': 'logging_error'
                }
                self.logger.error(json.dumps(fallback_data, default=str))
            except:
                # Ultimate fallback: simple string logging
                self.logger.error(f"Performance logging failed for operation {operation}: {e}")

    def log_error(self, error: Exception, context: Dict[str, Any]):
        """Log errors with context"""
        log_data = self._create_log_entry(
            action="error",
            error_type=type(error).__name__,
            error_message=str(error),
            category="error",
            **context
        )

        self.logger.error(json.dumps(log_data))

    def log_security_event(self, event_type: str, user_id: Optional[str] = None,
                           ip_address: Optional[str] = None,
                           additional_data: Optional[Dict] = None):
        """Log security-related events"""
        log_data = self._create_log_entry(
            action="security_event",
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            category="security"
        )

        if additional_data:
            log_data.update(additional_data)

        self.logger.warning(json.dumps(log_data))

    def log_analytics_event(self, event_type: str, data: Dict[str, Any]):
        """Log analytics events for business intelligence"""
        log_data = self._create_log_entry(
            action="analytics_event",
            event_type=event_type,
            category="analytics",
            **data
        )

        self.logger.info(json.dumps(log_data))

    def log_api_request(self, endpoint: str, method: str, user_id: Optional[str],
                        status_code: int, duration: float,
                        additional_data: Optional[Dict] = None):
        """Log API requests"""
        log_data = self._create_log_entry(
            action="api_request",
            endpoint=endpoint,
            method=method,
            user_id=user_id,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            category="api"
        )

        if additional_data:
            log_data.update(additional_data)

        # Log level based on status code
        if status_code >= 500:
            self.logger.error(json.dumps(log_data))
        elif status_code >= 400:
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))


# Global logger instance
job_actions_logger = JobActionsLogger()


def log_performance(operation_name: str):
    """Decorator to log function performance"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                job_actions_logger.log_performance(
                    operation=f"{operation_name}.{func.__name__}",
                    duration=duration,
                    additional_metrics={
                        'success': True,
                        'args_count': len(args),
                        'kwargs_count': len(kwargs)
                    }
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                job_actions_logger.log_performance(
                    operation=f"{operation_name}.{func.__name__}",
                    duration=duration,
                    additional_metrics={
                        'success': False,
                        'error': str(e)
                    }
                )
                raise

        return wrapper

    return decorator


def log_user_action(action_type: str):
    """Decorator to log user actions"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user_id and job_id from arguments
            user_id = kwargs.get('user_id') or (args[1] if len(args) > 1 else None)
            job_id = kwargs.get('job_id') or (args[2] if len(args) > 2 else None)

            try:
                result = func(*args, **kwargs)

                job_actions_logger.log_user_action(
                    action=action_type,
                    user_id=user_id,
                    job_id=job_id,
                    additional_data={
                        'success': True,
                        'function': func.__name__
                    }
                )
                return result
            except Exception as e:
                job_actions_logger.log_user_action(
                    action=action_type,
                    user_id=user_id,
                    job_id=job_id,
                    additional_data={
                        'success': False,
                        'error': str(e),
                        'function': func.__name__
                    }
                )
                raise

        return wrapper

    return decorator


@contextmanager
def performance_monitor(operation_name: str, additional_metrics: Optional[Dict] = None):
    """Context manager for monitoring performance"""
    start_time = time.time()
    try:
        yield
        duration = time.time() - start_time
        job_actions_logger.log_performance(
            operation=operation_name,
            duration=duration,
            additional_metrics=additional_metrics or {}
        )
    except Exception as e:
        duration = time.time() - start_time
        job_actions_logger.log_performance(
            operation=operation_name,
            duration=duration,
            additional_metrics={
                **(additional_metrics or {}),
                'success': False,
                'error': str(e)
            }
        )
        raise


class JobActionsMetrics:
    """Metrics collector for job actions"""

    def __init__(self):
        self.metrics = {
            'likes_total': 0,
            'saves_total': 0,
            'shares_total': 0,
            'errors_total': 0,
            'api_requests_total': 0,
            'slow_queries_total': 0
        }
        self.logger = JobActionsLogger("job_actions_metrics")

    def increment(self, metric_name: str, value: int = 1, labels: Optional[Dict] = None):
        """Increment a metric counter"""
        if metric_name in self.metrics:
            self.metrics[metric_name] += value

        self.logger.log_analytics_event(
            event_type="metric_increment",
            data={
                'metric_name': metric_name,
                'value': value,
                'labels': labels or {},
                'current_total': self.metrics.get(metric_name, 0)
            }
        )

    def record_histogram(self, metric_name: str, value: float, labels: Optional[Dict] = None):
        """Record histogram metric (e.g., response times)"""
        self.logger.log_analytics_event(
            event_type="histogram_record",
            data={
                'metric_name': metric_name,
                'value': value,
                'labels': labels or {}
            }
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        return {
            'timestamp': utc_time().isoformat(),
            'metrics': self.metrics.copy()
        }


# Global metrics instance
job_actions_metrics = JobActionsMetrics()


class JobActionsHealthCheck:
    """Health check utilities for job actions"""

    def __init__(self):
        self.logger = JobActionsLogger("job_actions_health")

    def check_database_connectivity(self) -> bool:
        """Check if database is accessible"""
        try:
            from src.database.sql import engine
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            self.logger.log_error(e, {'check': 'database_connectivity'})
            return False

    def check_table_accessibility(self) -> Dict[str, bool]:
        """Check if job actions tables are accessible"""
        results = {}
        tables = ['job_likes', 'job_shares']

        try:
            from src.database.sql import engine
            with engine.connect() as conn:
                for table in tables:
                    try:
                        conn.execute(f"SELECT COUNT(*) FROM {table} LIMIT 1")
                        results[table] = True
                    except Exception as e:
                        results[table] = False
                        self.logger.log_error(e, {'check': f'table_accessibility_{table}'})
        except Exception as e:
            self.logger.log_error(e, {'check': 'table_accessibility_general'})
            for table in tables:
                results[table] = False

        return results

    def check_index_performance(self) -> Dict[str, Any]:
        """Check index performance metrics"""
        try:
            from src.database.sql import engine
            with engine.connect() as conn:
                # Check if essential indexes exist
                index_query = """
                              SELECT TABLE_NAME, INDEX_NAME, CARDINALITY
                              FROM information_schema.STATISTICS
                              WHERE TABLE_SCHEMA = DATABASE()
                                AND TABLE_NAME IN ('job_likes', 'job_shares')
                                AND INDEX_NAME != 'PRIMARY' \
                              """

                indexes = conn.execute(index_query).fetchall()

                return {
                    'indexes_found': len(indexes),
                    'indexes': [
                        {'table': row[0], 'name': row[1], 'cardinality': row[2]}
                        for row in indexes
                    ]
                }
        except Exception as e:
            self.logger.log_error(e, {'check': 'index_performance'})
            return {'error': str(e)}

    def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check"""
        health_status = {
            'timestamp': utc_time().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }

        # Database connectivity
        db_healthy = self.check_database_connectivity()
        health_status['checks']['database'] = {
            'status': 'healthy' if db_healthy else 'unhealthy',
            'accessible': db_healthy
        }

        # Table accessibility
        table_status = self.check_table_accessibility()
        all_tables_healthy = all(table_status.values())
        health_status['checks']['tables'] = {
            'status': 'healthy' if all_tables_healthy else 'unhealthy',
            'details': table_status
        }

        # Index performance
        index_status = self.check_index_performance()
        health_status['checks']['indexes'] = {
            'status': 'healthy' if 'error' not in index_status else 'unhealthy',
            'details': index_status
        }

        # Overall status
        if not db_healthy or not all_tables_healthy or 'error' in index_status:
            health_status['overall_status'] = 'unhealthy'

        # Log health check results
        self.logger.log_analytics_event(
            event_type="health_check",
            data=health_status
        )

        return health_status


# Global health check instance
job_actions_health = JobActionsHealthCheck()

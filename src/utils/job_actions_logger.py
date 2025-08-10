"""
Job Actions Logging Utility

Provides comprehensive logging for job actions feature including:
- User action logging (likes, saves, shares)
- Performance monitoring
- Error tracking
- Security event logging
- Analytics event logging
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
    """Centralized logger for job actions with structured logging"""

    def __init__(self, name: str = "job_actions"):
        self.logger = logging.getLogger(name)
        self.setup_logger()

    def setup_logger(self):
        """Setup logger with appropriate handlers and formatters"""
        if not self.logger.handlers:
            # Console handler for development
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)

            # File handler for production
            file_handler = logging.FileHandler('logs/job_actions.log')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)

            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)

    def _create_log_entry(self, action: str, **kwargs) -> Dict[str, Any]:
        """Create structured log entry"""
        return {
            'timestamp': utc_time().isoformat(),
            'action': action,
            'service': 'job_actions',
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
        """Log performance metrics"""
        log_data = self._create_log_entry(
            action="performance_metric",
            operation=operation,
            duration_ms=round(duration * 1000, 2),
            category="performance"
        )

        if additional_metrics:
            log_data.update(additional_metrics)

        # Log as warning if operation is slow
        if duration > 1.0:  # More than 1 second
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))

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

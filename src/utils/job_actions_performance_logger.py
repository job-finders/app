"""
Job Actions Performance Logger

Comprehensive performance monitoring and logging for job actions operations.
This module provides detailed performance metrics, bottleneck detection,
and optimization insights for the job actions system.

Performance Metrics Tracked:
- Operation execution times and latency
- Database query performance and optimization opportunities
- Cache hit/miss ratios and effectiveness
- Memory usage and resource consumption
- Concurrent operation handling and throughput
- Error rates and failure patterns
"""

import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import contextmanager
from dataclasses import dataclass, field
from collections import defaultdict, deque

from src.logger import init_logger


@dataclass
class PerformanceMetric:
    """Data class for storing performance metrics"""
    operation: str
    duration: float
    timestamp: datetime
    user_id: Optional[str] = None
    job_id: Optional[str] = None
    success: bool = True
    error_type: Optional[str] = None
    memory_usage: Optional[float] = None
    cache_hit: Optional[bool] = None
    database_queries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class JobActionsPerformanceLogger:
    """
    Comprehensive performance monitoring for job actions operations.
    
    This class provides detailed performance tracking, bottleneck detection,
    and optimization insights for all job actions operations. It includes
    real-time monitoring, historical analysis, and alerting capabilities.
    
    Features:
        - Real-time performance metric collection
        - Aggregated statistics and trend analysis
        - Bottleneck detection and alerting
        - Cache performance monitoring
        - Database query optimization insights
        - Memory usage tracking
        - Concurrent operation monitoring
    """

    def __init__(self, max_metrics_history: int = 1000):
        """
        Initialize the performance logger.
        
        Args:
            max_metrics_history: Maximum number of metrics to keep in memory
        """
        self.logger = init_logger("JobActionsPerformanceLogger")
        self.metrics_logger = init_logger("JobActionsMetrics")

        # Thread-safe storage for metrics
        self._lock = threading.RLock()
        self._metrics_history: deque = deque(maxlen=max_metrics_history)
        self._active_operations: Dict[str, Dict[str, Any]] = {}

        # Performance thresholds for alerting
        self.slow_operation_threshold = 2.0  # seconds
        self.very_slow_operation_threshold = 5.0  # seconds

        self.logger.info("JobActionsPerformanceLogger initialized")

    @contextmanager
    def track_operation(
            self,
            operation: str,
            user_id: Optional[str] = None,
            job_id: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracking operation performance.
        
        Args:
            operation: Name of the operation being tracked
            user_id: User ID associated with the operation
            job_id: Job ID associated with the operation
            metadata: Additional metadata for the operation
            
        Usage:
            with performance_logger.track_operation('like_job', user_id='123', job_id='456'):
                # Perform operation
                result = await some_operation()
        """
        operation_id = f"{operation}_{threading.get_ident()}_{time.time()}"
        start_time = time.time()

        # Track active operation
        with self._lock:
            self._active_operations[operation_id] = {
                'operation': operation,
                'start_time': start_time,
                'user_id': user_id,
                'job_id': job_id,
                'metadata': metadata or {}
            }

        success = True
        error_type = None
        cache_hit = None
        database_queries = 0

        try:
            # Yield control to the operation
            operation_context = {
                'set_cache_hit': lambda hit: setattr(operation_context, 'cache_hit', hit),
                'increment_db_queries': lambda count=1: setattr(operation_context, 'db_queries',
                                                                getattr(operation_context, 'db_queries', 0) + count),
                'cache_hit': None,
                'db_queries': 0
            }

            yield operation_context

            # Extract context data
            cache_hit = operation_context.get('cache_hit')
            database_queries = operation_context.get('db_queries', 0)

        except Exception as e:
            success = False
            error_type = type(e).__name__
            self.logger.warning(f"Operation {operation} failed: {e}")
            raise

        finally:
            # Calculate performance metrics
            end_time = time.time()
            duration = end_time - start_time

            # Create performance metric
            metric = PerformanceMetric(
                operation=operation,
                duration=duration,
                timestamp=datetime.utcnow(),
                user_id=user_id,
                job_id=job_id,
                success=success,
                error_type=error_type,
                cache_hit=cache_hit,
                database_queries=database_queries,
                metadata=metadata or {}
            )

            # Record the metric
            self._record_metric(metric)

            # Clean up active operation tracking
            with self._lock:
                self._active_operations.pop(operation_id, None)

    def record_cache_operation(self, operation: str, hit: bool, duration: float = 0.0) -> None:
        """
        Record cache operation performance.
        
        Args:
            operation: Cache operation name
            hit: Whether the cache operation was a hit or miss
            duration: Operation duration in seconds
        """
        metric = PerformanceMetric(
            operation=f"cache_{operation}",
            duration=duration,
            timestamp=datetime.utcnow(),
            success=True,
            cache_hit=hit
        )

        self._record_metric(metric)

    def record_database_query(self, query_type: str, duration: float, success: bool = True) -> None:
        """
        Record database query performance.
        
        Args:
            query_type: Type of database query (select, insert, update, delete)
            duration: Query duration in seconds
            success: Whether the query was successful
        """
        metric = PerformanceMetric(
            operation=f"db_{query_type}",
            duration=duration,
            timestamp=datetime.utcnow(),
            success=success,
            database_queries=1
        )

        self._record_metric(metric)

    def get_recent_metrics(self, operation: Optional[str] = None, limit: int = 100) -> List[PerformanceMetric]:
        """
        Get recent performance metrics.
        
        Args:
            operation: Filter by operation name (optional)
            limit: Maximum number of metrics to return
            
        Returns:
            List of recent PerformanceMetric objects
        """
        with self._lock:
            metrics = list(self._metrics_history)

            if operation:
                metrics = [m for m in metrics if m.operation == operation]

            return metrics[-limit:]

    def _record_metric(self, metric: PerformanceMetric) -> None:
        """
        Record a performance metric and update statistics.
        
        Args:
            metric: PerformanceMetric to record
        """
        with self._lock:
            # Add to history
            self._metrics_history.append(metric)

        # Log the metric
        self._log_metric(metric)

        # Check for performance alerts
        self._check_performance_alerts(metric)

    def _log_metric(self, metric: PerformanceMetric) -> None:
        """
        Log performance metric with appropriate level.
        
        Args:
            metric: PerformanceMetric to log
        """
        log_data = {
            'operation': metric.operation,
            'duration': metric.duration,
            'success': metric.success,
            'user_id': metric.user_id,
            'job_id': metric.job_id,
            'cache_hit': metric.cache_hit,
            'database_queries': metric.database_queries,
            'timestamp': metric.timestamp.isoformat()
        }

        if metric.duration > self.very_slow_operation_threshold:
            self.metrics_logger.warning(f"Very slow operation: {metric.operation} took {metric.duration:.2f}s",
                                        extra=log_data)
        elif metric.duration > self.slow_operation_threshold:
            self.metrics_logger.info(f"Slow operation: {metric.operation} took {metric.duration:.2f}s", extra=log_data)
        else:
            self.metrics_logger.debug(f"Operation: {metric.operation} completed in {metric.duration:.2f}s",
                                      extra=log_data)

    def _check_performance_alerts(self, metric: PerformanceMetric) -> None:
        """
        Check if metric triggers any performance alerts.
        
        Args:
            metric: PerformanceMetric to check
        """
        alerts = []

        # Slow operation alert
        if metric.duration > self.very_slow_operation_threshold:
            alerts.append(f"Very slow operation: {metric.operation} took {metric.duration:.2f}s")

        # Log alerts
        for alert in alerts:
            self.logger.warning(f"Performance Alert: {alert}")


# Global performance logger instance
job_actions_performance_logger = JobActionsPerformanceLogger()

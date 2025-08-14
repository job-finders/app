"""
Monitoring and metrics collection for Candidate Fit Analysis feature
"""

import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading


@dataclass
class AnalysisMetrics:
    """Metrics for candidate analysis requests"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cache_hits: int = 0
    average_duration: float = 0.0
    slow_requests: int = 0  # > 30 seconds
    error_breakdown: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    hourly_requests: deque = field(default_factory=lambda: deque(maxlen=24))
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))


class CandidateAnalysisMonitor:
    """Monitor for candidate analysis performance and usage"""

    def __init__(self):
        self.metrics = AnalysisMetrics()
        self.logger = logging.getLogger('candidate_analysis_monitor')
        self._lock = threading.Lock()

    def record_request_start(self, user_id: str, job_id: str, cv_id: str) -> str:
        """Record the start of an analysis request"""
        request_id = f"{user_id}_{job_id}_{cv_id}_{int(time.time())}"

        with self._lock:
            self.metrics.total_requests += 1

        self.logger.info(f"Analysis request started - ID: {request_id}")
        return request_id

    def record_request_success(self, request_id: str, duration: float, percentile_rank: float):
        """Record successful completion of analysis request"""
        with self._lock:
            self.metrics.successful_requests += 1
            self.metrics.recent_durations.append(duration)

            # Update average duration
            if self.metrics.recent_durations:
                self.metrics.average_duration = sum(self.metrics.recent_durations) / len(self.metrics.recent_durations)

            # Track slow requests
            if duration > 30:
                self.metrics.slow_requests += 1

        self.logger.info(
            f"Analysis completed - ID: {request_id}, Duration: {duration:.2f}s, Percentile: {percentile_rank}")

    def record_request_failure(self, request_id: str, duration: float, error_type: str, error_message: str):
        """Record failed analysis request"""
        with self._lock:
            self.metrics.failed_requests += 1
            self.metrics.error_breakdown[error_type] += 1

        self.logger.error(f"Analysis failed - ID: {request_id}, Duration: {duration:.2f}s, "
                          f"Error: {error_type}, Message: {error_message}")

    def record_cache_hit(self, user_id: str, job_id: str, cv_id: str, cache_age: float):
        """Record cache hit for analysis request"""
        with self._lock:
            self.metrics.cache_hits += 1

        self.logger.info(f"Cache hit - User: {user_id}, Job: {job_id}, CV: {cv_id}, Age: {cache_age:.1f}s")

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        with self._lock:
            success_rate = (self.metrics.successful_requests / max(self.metrics.total_requests, 1)) * 100
            cache_hit_rate = (self.metrics.cache_hits / max(self.metrics.total_requests, 1)) * 100

            return {
                'total_requests': self.metrics.total_requests,
                'successful_requests': self.metrics.successful_requests,
                'failed_requests': self.metrics.failed_requests,
                'cache_hits': self.metrics.cache_hits,
                'success_rate': round(success_rate, 2),
                'cache_hit_rate': round(cache_hit_rate, 2),
                'average_duration': round(self.metrics.average_duration, 2),
                'slow_requests': self.metrics.slow_requests,
                'error_breakdown': dict(self.metrics.error_breakdown),
                'recent_durations': list(self.metrics.recent_durations)
            }

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for monitoring systems"""
        metrics = self.get_metrics_summary()

        # Determine health status
        health = 'healthy'
        issues = []

        if metrics['success_rate'] < 95:
            health = 'degraded'
            issues.append(f"Low success rate: {metrics['success_rate']}%")

        if metrics['average_duration'] > 20:
            health = 'degraded'
            issues.append(f"High average duration: {metrics['average_duration']}s")

        if metrics['slow_requests'] > metrics['total_requests'] * 0.1:
            health = 'degraded'
            issues.append(f"Too many slow requests: {metrics['slow_requests']}")

        if metrics['failed_requests'] > metrics['total_requests'] * 0.1:
            health = 'unhealthy'
            issues.append(f"High failure rate: {metrics['failed_requests']} failures")

        return {
            'status': health,
            'timestamp': datetime.utcnow().isoformat(),
            'issues': issues,
            'metrics': metrics
        }

    def reset_metrics(self):
        """Reset all metrics (for testing or periodic reset)"""
        with self._lock:
            self.metrics = AnalysisMetrics()

        self.logger.info("Metrics reset")


# Global monitor instance
candidate_analysis_monitor = CandidateAnalysisMonitor()


def log_analysis_event(event_type: str, **kwargs):
    """Convenience function for logging analysis events"""
    logger = logging.getLogger('candidate_analysis_events')

    event_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        **kwargs
    }

    logger.info(f"Analysis Event: {event_type}", extra=event_data)


# Monitoring decorators
def monitor_analysis_request(func):
    """Decorator to monitor analysis requests"""

    def wrapper(*args, **kwargs):
        start_time = time.time()
        request_id = None

        try:
            # Extract parameters for monitoring
            user_id = kwargs.get('user_id') or (args[1] if len(args) > 1 else 'unknown')
            job_id = kwargs.get('job_id') or (args[2] if len(args) > 2 else 'unknown')
            cv_id = kwargs.get('cv_id') or (args[3] if len(args) > 3 else 'unknown')

            request_id = candidate_analysis_monitor.record_request_start(user_id, job_id, cv_id)

            # Execute the function
            result = func(*args, **kwargs)

            # Record success
            duration = time.time() - start_time
            percentile_rank = getattr(result, 'percentile_rank', 0) if result else 0
            candidate_analysis_monitor.record_request_success(request_id, duration, percentile_rank)

            return result

        except Exception as e:
            # Record failure
            duration = time.time() - start_time
            error_type = type(e).__name__
            error_message = str(e)

            if request_id:
                candidate_analysis_monitor.record_request_failure(request_id, duration, error_type, error_message)

            raise

    return wrapper


# Health check endpoint data
def get_candidate_analysis_health():
    """Get health check data for candidate analysis"""
    return candidate_analysis_monitor.get_health_status()


# Metrics endpoint data
def get_candidate_analysis_metrics():
    """Get metrics data for candidate analysis"""
    return candidate_analysis_monitor.get_metrics_summary()

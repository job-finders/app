"""
Performance Monitoring for Job Match Scoring

This module provides monitoring and analytics for the job match scoring feature,
tracking performance metrics, usage patterns, and system health.
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from functools import wraps
from dataclasses import dataclass, asdict
import json

# Configure logging for metrics
metrics_logger = logging.getLogger('match_scoring_metrics')
metrics_logger.setLevel(logging.INFO)

# Create file handler for metrics
metrics_handler = logging.FileHandler('logs/match_scoring_metrics.log')
metrics_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
metrics_handler.setFormatter(metrics_formatter)
metrics_logger.addHandler(metrics_handler)


@dataclass
class MatchScoringMetrics:
    """Data class for match scoring performance metrics"""
    operation: str
    user_id: Optional[str]
    job_id: Optional[str]
    execution_time: float
    success: bool
    error_message: Optional[str]
    cache_hit: bool
    job_count: Optional[int]
    timestamp: datetime
    additional_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for logging"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class MatchScoringMonitor:
    """Monitor for job match scoring performance and usage"""
    
    def __init__(self):
        self.metrics_cache = []
        self.performance_thresholds = {
            'quick_match_scoring': 0.1,  # 100ms
            'detailed_match_analysis': 2.0,  # 2 seconds
            'batch_match_scoring': 5.0,  # 5 seconds for batch
            'api_response': 1.0  # 1 second for API
        }
    
    def record_metric(self, metrics: MatchScoringMetrics):
        """Record a performance metric"""
        # Log to file
        metrics_logger.info(json.dumps(metrics.to_dict()))
        
        # Cache for real-time monitoring
        self.metrics_cache.append(metrics)
        
        # Keep only recent metrics in memory (last 1000)
        if len(self.metrics_cache) > 1000:
            self.metrics_cache = self.metrics_cache[-1000:]
        
        # Check for performance issues
        self._check_performance_threshold(metrics)
    
    def _check_performance_threshold(self, metrics: MatchScoringMetrics):
        """Check if performance exceeds acceptable thresholds"""
        threshold = self.performance_thresholds.get(metrics.operation)
        if threshold and metrics.execution_time > threshold:
            warning_msg = (
                f"Performance warning: {metrics.operation} took "
                f"{metrics.execution_time:.3f}s (threshold: {threshold}s)"
            )
            metrics_logger.warning(warning_msg)
            
            # Could trigger alerts here (email, Slack, etc.)
            self._trigger_performance_alert(metrics, threshold)
    
    def _trigger_performance_alert(self, metrics: MatchScoringMetrics, threshold: float):
        """Trigger performance alert (implement based on your alerting system)"""
        # Example: Send to monitoring service
        alert_data = {
            'alert_type': 'performance_threshold_exceeded',
            'operation': metrics.operation,
            'execution_time': metrics.execution_time,
            'threshold': threshold,
            'timestamp': metrics.timestamp.isoformat(),
            'user_id': metrics.user_id,
            'job_id': metrics.job_id
        }
        
        # Log alert
        metrics_logger.error(f"PERFORMANCE ALERT: {json.dumps(alert_data)}")
        
        # TODO: Integrate with your monitoring service (e.g., DataDog, New Relic)
        # monitoring_service.send_alert(alert_data)
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        recent_metrics = [
            m for m in self.metrics_cache 
            if m.timestamp.timestamp() > cutoff_time
        ]
        
        if not recent_metrics:
            return {'message': 'No recent metrics available'}
        
        # Calculate statistics
        operations = {}
        for metric in recent_metrics:
            op = metric.operation
            if op not in operations:
                operations[op] = {
                    'count': 0,
                    'total_time': 0,
                    'success_count': 0,
                    'cache_hits': 0,
                    'errors': []
                }
            
            operations[op]['count'] += 1
            operations[op]['total_time'] += metric.execution_time
            if metric.success:
                operations[op]['success_count'] += 1
            if metric.cache_hit:
                operations[op]['cache_hits'] += 1
            if not metric.success and metric.error_message:
                operations[op]['errors'].append(metric.error_message)
        
        # Calculate averages and rates
        summary = {}
        for op, stats in operations.items():
            summary[op] = {
                'total_requests': stats['count'],
                'average_time': stats['total_time'] / stats['count'],
                'success_rate': stats['success_count'] / stats['count'],
                'cache_hit_rate': stats['cache_hits'] / stats['count'],
                'error_count': len(stats['errors']),
                'unique_errors': len(set(stats['errors']))
            }
        
        return summary


# Global monitor instance
monitor = MatchScoringMonitor()


def track_performance(operation: str, include_args: bool = False):
    """Decorator to track performance of match scoring operations"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            cache_hit = kwargs.get('_cache_hit', False)
            
            # Extract user_id and job_id from arguments if available
            user_id = None
            job_id = None
            job_count = None
            additional_data = {}
            
            try:
                # Try to extract common parameters
                if args:
                    if hasattr(args[0], 'uid'):  # User object
                        user_id = args[0].uid
                    elif hasattr(args[0], 'job_id'):  # Job object
                        job_id = args[0].job_id
                
                if 'user_id' in kwargs:
                    user_id = kwargs['user_id']
                if 'job_id' in kwargs:
                    job_id = kwargs['job_id']
                if 'jobs' in kwargs and hasattr(kwargs['jobs'], '__len__'):
                    job_count = len(kwargs['jobs'])
                
                if include_args:
                    additional_data = {
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys())
                    }
                
                # Execute the function
                result = await func(*args, **kwargs)
                
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Record metrics
                metrics = MatchScoringMetrics(
                    operation=operation,
                    user_id=user_id,
                    job_id=job_id,
                    execution_time=execution_time,
                    success=success,
                    error_message=error_message,
                    cache_hit=cache_hit,
                    job_count=job_count,
                    timestamp=datetime.now(timezone.utc),
                    additional_data=additional_data
                )
                
                monitor.record_metric(metrics)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                
                metrics = MatchScoringMetrics(
                    operation=operation,
                    user_id=None,
                    job_id=None,
                    execution_time=execution_time,
                    success=success,
                    error_message=error_message,
                    cache_hit=False,
                    job_count=None,
                    timestamp=datetime.now(timezone.utc)
                )
                
                monitor.record_metric(metrics)
            
            return result
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class UsageAnalytics:
    """Analytics for job match scoring usage patterns"""
    
    def __init__(self):
        self.analytics_logger = logging.getLogger('match_scoring_analytics')
        self.analytics_logger.setLevel(logging.INFO)
        
        # Create analytics log handler
        analytics_handler = logging.FileHandler('logs/match_scoring_analytics.log')
        analytics_formatter = logging.Formatter(
            '%(asctime)s - %(message)s'
        )
        analytics_handler.setFormatter(analytics_formatter)
        self.analytics_logger.addHandler(analytics_handler)
    
    def track_modal_interaction(self, user_id: str, job_id: str, action: str, 
                               additional_data: Optional[Dict] = None):
        """Track user interactions with match details modal"""
        event = {
            'event_type': 'modal_interaction',
            'user_id': user_id,
            'job_id': job_id,
            'action': action,  # 'opened', 'closed', 'error', 'retry'
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'additional_data': additional_data or {}
        }
        
        self.analytics_logger.info(json.dumps(event))
    
    def track_match_score_display(self, user_id: str, job_count: int, 
                                 scores_displayed: int, page_type: str):
        """Track match score display on job listing pages"""
        event = {
            'event_type': 'match_scores_displayed',
            'user_id': user_id,
            'job_count': job_count,
            'scores_displayed': scores_displayed,
            'page_type': page_type,  # 'browse', 'search', 'category', etc.
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.analytics_logger.info(json.dumps(event))
    
    def track_conversion_event(self, user_id: str, job_id: str, 
                              match_score: float, action: str):
        """Track conversion events (job applications, saves, etc.)"""
        event = {
            'event_type': 'conversion',
            'user_id': user_id,
            'job_id': job_id,
            'match_score': match_score,
            'action': action,  # 'applied', 'saved', 'viewed_details'
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.analytics_logger.info(json.dumps(event))


# Global analytics instance
analytics = UsageAnalytics()


def get_system_health() -> Dict[str, Any]:
    """Get overall system health for match scoring feature"""
    try:
        # Get recent performance summary
        performance = monitor.get_performance_summary(hours=1)
        
        # Check cache health (if using Redis)
        cache_health = _check_cache_health()
        
        # Check database health
        db_health = _check_database_health()
        
        # Overall health status
        health_status = "healthy"
        issues = []
        
        # Check for performance issues
        for op, stats in performance.items():
            if isinstance(stats, dict):
                if stats.get('success_rate', 1.0) < 0.95:
                    health_status = "degraded"
                    issues.append(f"{op} success rate below 95%")
                
                if stats.get('average_time', 0) > monitor.performance_thresholds.get(op, float('inf')):
                    health_status = "degraded"
                    issues.append(f"{op} average time exceeds threshold")
        
        return {
            'status': health_status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'performance': performance,
            'cache_health': cache_health,
            'database_health': db_health,
            'issues': issues
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': str(e)
        }


def _check_cache_health() -> Dict[str, Any]:
    """Check Redis cache health"""
    try:
        from src.cache.cache_redis import cache
        
        # Test cache connectivity
        test_key = "health_check_test"
        cache.set(test_key, "test_value", ttl=10)
        retrieved = cache.get(test_key)
        cache.delete(test_key)
        
        if retrieved == "test_value":
            return {'status': 'healthy', 'connectivity': True}
        else:
            return {'status': 'degraded', 'connectivity': False, 'issue': 'Cache read/write failed'}
            
    except Exception as e:
        return {'status': 'error', 'connectivity': False, 'error': str(e)}


def _check_database_health() -> Dict[str, Any]:
    """Check database health for match scoring queries"""
    try:
        # This would test database connectivity and query performance
        # Implementation depends on your database setup
        
        return {'status': 'healthy', 'connectivity': True}
        
    except Exception as e:
        return {'status': 'error', 'connectivity': False, 'error': str(e)}


# Export monitoring functions for use in routes
__all__ = [
    'track_performance',
    'monitor',
    'analytics',
    'get_system_health',
    'MatchScoringMetrics',
    'MatchScoringMonitor',
    'UsageAnalytics'
]
"""
Job Actions Monitoring and Alerting System

Provides real-time monitoring, alerting, and performance tracking for job actions.
Includes:
- Real-time metrics collection
- Performance threshold monitoring
- Error rate tracking
- Automated alerting
- Dashboard data preparation
"""

import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from threading import Lock
import asyncio

from src.database.constants import utc_time
from src.utils.job_actions_logger import job_actions_logger


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    labels: Dict[str, str]


@dataclass
class Alert:
    """Alert definition"""
    name: str
    condition: str
    threshold: float
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    cooldown_minutes: int = 5
    last_triggered: Optional[datetime] = None


class MetricsCollector:
    """Real-time metrics collector with time-series storage"""

    def __init__(self, max_points_per_metric: int = 1000):
        self.metrics = defaultdict(lambda: deque(maxlen=max_points_per_metric))
        self.counters = defaultdict(float)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.lock = Lock()

    def record_counter(self, name: str, value: float = 1, labels: Optional[Dict] = None):
        """Record counter metric (always increasing)"""
        with self.lock:
            key = self._make_key(name, labels or {})
            self.counters[key] += value

            point = MetricPoint(
                timestamp=utc_time(),
                value=self.counters[key],
                labels=labels or {}
            )
            self.metrics[name].append(point)

    def record_gauge(self, name: str, value: float, labels: Optional[Dict] = None):
        """Record gauge metric (can go up or down)"""
        with self.lock:
            key = self._make_key(name, labels or {})
            self.gauges[key] = value

            point = MetricPoint(
                timestamp=utc_time(),
                value=value,
                labels=labels or {}
            )
            self.metrics[name].append(point)

    def record_histogram(self, name: str, value: float, labels: Optional[Dict] = None):
        """Record histogram metric (for distributions)"""
        with self.lock:
            key = self._make_key(name, labels or {})
            self.histograms[key].append(value)

            # Keep only last 100 values for memory efficiency
            if len(self.histograms[key]) > 100:
                self.histograms[key] = self.histograms[key][-100:]

            point = MetricPoint(
                timestamp=utc_time(),
                value=value,
                labels=labels or {}
            )
            self.metrics[name].append(point)

    def get_metric_history(self, name: str, minutes: int = 60) -> List[MetricPoint]:
        """Get metric history for specified time window"""
        cutoff = utc_time() - timedelta(minutes=minutes)

        with self.lock:
            return [
                point for point in self.metrics[name]
                if point.timestamp >= cutoff
            ]

    def get_current_values(self) -> Dict[str, Any]:
        """Get current values for all metrics"""
        with self.lock:
            return {
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'histograms': {
                    key: {
                        'count': len(values),
                        'avg': sum(values) / len(values) if values else 0,
                        'min': min(values) if values else 0,
                        'max': max(values) if values else 0
                    }
                    for key, values in self.histograms.items()
                }
            }

    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        """Create unique key for metric with labels"""
        if not labels:
            return name

        label_str = ','.join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


class AlertManager:
    """Manages alerts and notifications"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alerts = {}
        self.alert_handlers = []
        self.active_alerts = set()

    def add_alert(self, alert: Alert):
        """Add alert definition"""
        self.alerts[alert.name] = alert
        job_actions_logger.log_analytics_event(
            event_type="alert_added",
            data={'alert_name': alert.name, 'severity': alert.severity}
        )

    def add_alert_handler(self, handler: Callable[[Alert, float], None]):
        """Add alert handler function"""
        self.alert_handlers.append(handler)

    def check_alerts(self):
        """Check all alerts and trigger if necessary"""
        current_values = self.metrics_collector.get_current_values()

        for alert_name, alert in self.alerts.items():
            try:
                should_trigger = self._evaluate_alert_condition(alert, current_values)

                if should_trigger:
                    if self._can_trigger_alert(alert):
                        self._trigger_alert(alert, current_values)
                else:
                    # Clear alert if it was active
                    if alert_name in self.active_alerts:
                        self.active_alerts.remove(alert_name)
                        self._clear_alert(alert)

            except Exception as e:
                job_actions_logger.log_error(e, {
                    'context': 'alert_check',
                    'alert_name': alert_name
                })

    def _evaluate_alert_condition(self, alert: Alert, current_values: Dict) -> bool:
        """Evaluate if alert condition is met"""
        # Simple condition evaluation - can be extended for complex conditions
        if alert.condition == 'error_rate_high':
            error_count = current_values['counters'].get('job_actions_errors', 0)
            total_requests = current_values['counters'].get('job_actions_requests', 1)
            error_rate = (error_count / total_requests) * 100
            return error_rate > alert.threshold

        elif alert.condition == 'response_time_high':
            response_times = current_values['histograms'].get('job_actions_response_time', {})
            avg_response_time = response_times.get('avg', 0)
            return avg_response_time > alert.threshold

        elif alert.condition == 'database_connections_high':
            db_connections = current_values['gauges'].get('database_connections', 0)
            return db_connections > alert.threshold

        elif alert.condition == 'memory_usage_high':
            memory_usage = current_values['gauges'].get('memory_usage_percent', 0)
            return memory_usage > alert.threshold

        return False

    def _can_trigger_alert(self, alert: Alert) -> bool:
        """Check if alert can be triggered (respects cooldown)"""
        if alert.last_triggered is None:
            return True

        cooldown_period = timedelta(minutes=alert.cooldown_minutes)
        return utc_time() - alert.last_triggered > cooldown_period

    def _trigger_alert(self, alert: Alert, current_values: Dict):
        """Trigger alert and notify handlers"""
        alert.last_triggered = utc_time()
        self.active_alerts.add(alert.name)

        # Get the actual value that triggered the alert
        trigger_value = self._get_trigger_value(alert, current_values)

        job_actions_logger.log_security_event(
            event_type="alert_triggered",
            additional_data={
                'alert_name': alert.name,
                'severity': alert.severity,
                'threshold': alert.threshold,
                'actual_value': trigger_value,
                'message': alert.message
            }
        )

        # Notify all handlers
        for handler in self.alert_handlers:
            try:
                handler(alert, trigger_value)
            except Exception as e:
                job_actions_logger.log_error(e, {
                    'context': 'alert_handler',
                    'alert_name': alert.name
                })

    def _clear_alert(self, alert: Alert):
        """Clear alert when condition is no longer met"""
        job_actions_logger.log_analytics_event(
            event_type="alert_cleared",
            data={'alert_name': alert.name}
        )

    def _get_trigger_value(self, alert: Alert, current_values: Dict) -> float:
        """Get the actual value that triggered the alert"""
        if alert.condition == 'error_rate_high':
            error_count = current_values['counters'].get('job_actions_errors', 0)
            total_requests = current_values['counters'].get('job_actions_requests', 1)
            return (error_count / total_requests) * 100

        elif alert.condition == 'response_time_high':
            response_times = current_values['histograms'].get('job_actions_response_time', {})
            return response_times.get('avg', 0)

        elif alert.condition == 'database_connections_high':
            return current_values['gauges'].get('database_connections', 0)

        elif alert.condition == 'memory_usage_high':
            return current_values['gauges'].get('memory_usage_percent', 0)

        return 0


class JobActionsMonitor:
    """Main monitoring class that coordinates metrics collection and alerting"""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager(self.metrics_collector)
        self.is_running = False
        self.setup_default_alerts()
        self.setup_alert_handlers()

    def setup_default_alerts(self):
        """Setup default alerts for job actions"""
        alerts = [
            Alert(
                name="high_error_rate",
                condition="error_rate_high",
                threshold=5.0,  # 5% error rate
                severity="high",
                message="Job actions error rate is above 5%",
                cooldown_minutes=10
            ),
            Alert(
                name="slow_response_time",
                condition="response_time_high",
                threshold=2000,  # 2 seconds
                severity="medium",
                message="Job actions response time is above 2 seconds",
                cooldown_minutes=5
            ),
            Alert(
                name="high_database_connections",
                condition="database_connections_high",
                threshold=80,  # 80 connections
                severity="high",
                message="Database connection count is high",
                cooldown_minutes=5
            ),
            Alert(
                name="high_memory_usage",
                condition="memory_usage_high",
                threshold=85.0,  # 85% memory usage
                severity="critical",
                message="Memory usage is critically high",
                cooldown_minutes=2
            )
        ]

        for alert in alerts:
            self.alert_manager.add_alert(alert)

    def setup_alert_handlers(self):
        """Setup alert notification handlers"""

        def log_alert_handler(alert: Alert, value: float):
            """Log alert to file"""
            job_actions_logger.log_security_event(
                event_type="alert_notification",
                additional_data={
                    'alert_name': alert.name,
                    'severity': alert.severity,
                    'threshold': alert.threshold,
                    'actual_value': value,
                    'message': alert.message
                }
            )

        def email_alert_handler(alert: Alert, value: float):
            """Send email alert to administrators"""
            if alert.severity in ['high', 'critical']:
                try:
                    from src.emailer import send_email
                    subject = f"[{alert.severity.upper()}] Job Actions Alert: {alert.name}"
                    message = (
                        f"Alert: {alert.message}\n\n"
                        f"Severity: {alert.severity}\n"
                        f"Threshold: {alert.threshold}\n"
                        f"Current Value: {value:.2f}\n"
                        f"Time: {utc_time().isoformat()}"
                    )

                    # Send to admin team
                    send_email(
                        to="admin@jobfinders.site",
                        subject=subject,
                        body=message,
                        priority="high" if alert.severity == "critical" else "normal"
                    )

                    job_actions_logger.log_analytics_event(
                        event_type="email_alert_sent",
                        data={
                            'alert_name': alert.name,
                            'severity': alert.severity,
                            'recipient': 'admin@jobfinders.site',
                            'value': value
                        }
                    )
                except Exception as e:
                    job_actions_logger.log_error(e, {
                        'context': 'email_alert_handler',
                        'alert_name': alert.name
                    })

        self.alert_manager.add_alert_handler(log_alert_handler)
        self.alert_manager.add_alert_handler(email_alert_handler)

    def record_user_action(self, action: str, user_id: str, job_id: str,
                           duration: float, success: bool):
        """Record user action metrics"""
        labels = {'action': action, 'success': str(success)}

        # Count total actions
        self.metrics_collector.record_counter('job_actions_total', 1, labels)

        # Record response time
        self.metrics_collector.record_histogram('job_actions_response_time', duration * 1000, labels)

        # Count errors if not successful
        if not success:
            self.metrics_collector.record_counter('job_actions_errors', 1, labels)

        # Record per-action metrics
        self.metrics_collector.record_counter(f'job_actions_{action}_total', 1, {'success': str(success)})

        # Business intelligence metrics
        if action in ['like', 'share']:
            # Track engagement rate
            self.metrics_collector.record_counter('job_engagement_total', 1)

            # Track user engagement frequency
            self.metrics_collector.record_counter(f'user_{user_id}_engagement', 1)

            # Track job popularity
            self.metrics_collector.record_counter(f'job_{job_id}_engagement', 1)

            # Track action conversion rates
            if action == 'share':
                self.metrics_collector.record_counter('share_conversions', 1)

    def record_database_metrics(self, active_connections: int, query_time: float):
        """Record database performance metrics"""
        self.metrics_collector.record_gauge('database_connections', active_connections)
        self.metrics_collector.record_histogram('database_query_time', query_time * 1000)

    def record_system_metrics(self, memory_usage_percent: float, cpu_usage_percent: float):
        """Record system performance metrics"""
        self.metrics_collector.record_gauge('memory_usage_percent', memory_usage_percent)
        self.metrics_collector.record_gauge('cpu_usage_percent', cpu_usage_percent)

    def get_dashboard_data(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        current_values = self.metrics_collector.get_current_values()

        # Get time series data for charts
        metrics_history = {}
        key_metrics = [
            'job_actions_total',
            'job_actions_response_time',
            'job_actions_errors',
            'database_connections',
            'memory_usage_percent'
        ]

        for metric in key_metrics:
            history = self.metrics_collector.get_metric_history(metric, time_window_minutes)
            metrics_history[metric] = [
                {
                    'timestamp': point.timestamp.isoformat(),
                    'value': point.value,
                    'labels': point.labels
                }
                for point in history
            ]

        # Calculate summary statistics
        total_actions = current_values['counters'].get('job_actions_total', 0)
        total_errors = current_values['counters'].get('job_actions_errors', 0)
        error_rate = (total_errors / total_actions * 100) if total_actions > 0 else 0

        response_time_stats = current_values['histograms'].get('job_actions_response_time', {})
        avg_response_time = response_time_stats.get('avg', 0)

        return {
            'timestamp': utc_time().isoformat(),
            'summary': {
                'total_actions': total_actions,
                'total_errors': total_errors,
                'error_rate_percent': round(error_rate, 2),
                'avg_response_time_ms': round(avg_response_time, 2),
                'active_alerts': len(self.alert_manager.active_alerts)
            },
            'metrics_history': metrics_history,
            'current_values': current_values,
            'active_alerts': list(self.alert_manager.active_alerts),
            'alert_definitions': {
                name: asdict(alert) for name, alert in self.alert_manager.alerts.items()
            }
        }

    def start_monitoring(self, check_interval_seconds: int = 30):
        """Start background monitoring loop"""
        self.is_running = True

        async def monitoring_loop():
            while self.is_running:
                try:
                    # Check alerts
                    self.alert_manager.check_alerts()

                    # Record actual system metrics
                    import psutil
                    memory_usage = psutil.virtual_memory().percent
                    cpu_usage = psutil.cpu_percent()
                    self.record_system_metrics(memory_usage, cpu_usage)

                    await asyncio.sleep(check_interval_seconds)

                except Exception as e:
                    job_actions_logger.log_error(e, {'context': 'monitoring_loop'})
                    await asyncio.sleep(check_interval_seconds)

        # Start monitoring loop
        asyncio.create_task(monitoring_loop())

        job_actions_logger.log_analytics_event(
            event_type="monitoring_started",
            data={'check_interval_seconds': check_interval_seconds}
        )

    def stop_monitoring(self):
        """Stop background monitoring"""
        self.is_running = False
        job_actions_logger.log_analytics_event(
            event_type="monitoring_stopped",
            data={}
        )

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        current_values = self.metrics_collector.get_current_values()

        # Determine overall health based on metrics
        health_score = 100
        issues = []

        # Check error rate
        total_actions = current_values['counters'].get('job_actions_total', 0)
        total_errors = current_values['counters'].get('job_actions_errors', 0)
        if total_actions > 0:
            error_rate = (total_errors / total_actions) * 100
            if error_rate > 5:
                health_score -= 20
                issues.append(f"High error rate: {error_rate:.1f}%")

        # Check response time
        response_time_stats = current_values['histograms'].get('job_actions_response_time', {})
        avg_response_time = response_time_stats.get('avg', 0)
        if avg_response_time > 2000:  # 2 seconds
            health_score -= 15
            issues.append(f"Slow response time: {avg_response_time:.0f}ms")

        # Check active alerts
        active_alerts_count = len(self.alert_manager.active_alerts)
        if active_alerts_count > 0:
            health_score -= active_alerts_count * 10
            issues.append(f"Active alerts: {active_alerts_count}")

        health_score = max(0, health_score)

        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            'status': status,
            'health_score': health_score,
            'issues': issues,
            'active_alerts': list(self.alert_manager.active_alerts),
            'timestamp': utc_time().isoformat()
        }


# Global monitor instance
job_actions_monitor = JobActionsMonitor()

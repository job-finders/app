"""
Admin routes for monitoring candidate analysis performance
"""

from flask import Blueprint, jsonify, render_template
from src.routes import flask_error_handler
from src.authentication import system_admin_login
from src.monitoring.candidate_analysis_metrics import (
    get_candidate_analysis_health,
    get_candidate_analysis_metrics,
    candidate_analysis_monitor
)
from src.database.models import User

candidate_analysis_monitoring_bp = Blueprint(
    'candidate_analysis_monitoring',
    __name__,
    url_prefix='/admin/monitoring/candidate-analysis'
)


@candidate_analysis_monitoring_bp.route('/health', methods=['GET'])
@flask_error_handler
@system_admin_login
async def health_check(user: User):
    """Get health status of candidate analysis service"""
    health_data = get_candidate_analysis_health()

    # Return appropriate HTTP status based on health
    status_code = 200
    if health_data['status'] == 'degraded':
        status_code = 206  # Partial Content
    elif health_data['status'] == 'unhealthy':
        status_code = 503  # Service Unavailable

    return jsonify(health_data), status_code


@candidate_analysis_monitoring_bp.route('/metrics', methods=['GET'])
@flask_error_handler
@system_admin_login
async def metrics(user: User):
    """Get detailed metrics for candidate analysis"""
    metrics_data = get_candidate_analysis_metrics()
    return jsonify(metrics_data), 200


@candidate_analysis_monitoring_bp.route('/dashboard', methods=['GET'])
@flask_error_handler
@system_admin_login
def dashboard(user: User):
    """Render monitoring dashboard for candidate analysis"""
    metrics_data = get_candidate_analysis_metrics()
    health_data = get_candidate_analysis_health()

    return render_template(
        'admin/monitoring/candidate_analysis_dashboard.html',
        metrics=metrics_data,
        health=health_data
    )


@candidate_analysis_monitoring_bp.route('/reset-metrics', methods=['POST'])
@flask_error_handler
@system_admin_login
async def reset_metrics(user: User):
    """Reset all metrics (for testing or maintenance)"""
    candidate_analysis_monitor.reset_metrics()
    return jsonify({"message": "Metrics reset successfully"}), 200


@candidate_analysis_monitoring_bp.route('/alerts', methods=['GET'])
@flask_error_handler
@system_admin_login
async def alerts(user: User):
    """Get current alerts for candidate analysis"""
    health_data = get_candidate_analysis_health()
    metrics_data = get_candidate_analysis_metrics()

    alerts = []

    # Generate alerts based on metrics
    if metrics_data['success_rate'] < 95:
        alerts.append({
            'level': 'warning',
            'message': f"Low success rate: {metrics_data['success_rate']}%",
            'metric': 'success_rate',
            'value': metrics_data['success_rate'],
            'threshold': 95
        })

    if metrics_data['average_duration'] > 20:
        alerts.append({
            'level': 'warning',
            'message': f"High average response time: {metrics_data['average_duration']}s",
            'metric': 'average_duration',
            'value': metrics_data['average_duration'],
            'threshold': 20
        })

    if metrics_data['slow_requests'] > metrics_data['total_requests'] * 0.1:
        alerts.append({
            'level': 'critical',
            'message': f"Too many slow requests: {metrics_data['slow_requests']}",
            'metric': 'slow_requests',
            'value': metrics_data['slow_requests'],
            'threshold': metrics_data['total_requests'] * 0.1
        })

    if metrics_data['failed_requests'] > metrics_data['total_requests'] * 0.05:
        alerts.append({
            'level': 'critical',
            'message': f"High failure rate: {metrics_data['failed_requests']} failures",
            'metric': 'failed_requests',
            'value': metrics_data['failed_requests'],
            'threshold': metrics_data['total_requests'] * 0.05
        })

    return jsonify({
        'alerts': alerts,
        'alert_count': len(alerts),
        'health_status': health_data['status']
    }), 200


@candidate_analysis_monitoring_bp.route('/performance-summary', methods=['GET'])
@flask_error_handler
@system_admin_login
async def performance_summary(user: User):
    """Get performance summary for candidate analysis"""
    metrics_data = get_candidate_analysis_metrics()

    # Calculate additional performance metrics
    total_requests = metrics_data['total_requests']
    if total_requests > 0:
        error_rate = (metrics_data['failed_requests'] / total_requests) * 100
        cache_efficiency = (metrics_data['cache_hits'] / total_requests) * 100
    else:
        error_rate = 0
        cache_efficiency = 0

    # Performance grades
    def get_grade(value, thresholds):
        if value >= thresholds[0]:
            return 'A'
        elif value >= thresholds[1]:
            return 'B'
        elif value >= thresholds[2]:
            return 'C'
        else:
            return 'D'

    performance_summary = {
        'overall_grade': 'A',  # Will be calculated based on individual grades
        'metrics': {
            'success_rate': {
                'value': metrics_data['success_rate'],
                'grade': get_grade(metrics_data['success_rate'], [98, 95, 90]),
                'status': 'good' if metrics_data['success_rate'] >= 95 else 'poor'
            },
            'average_duration': {
                'value': metrics_data['average_duration'],
                'grade': get_grade(20 - min(metrics_data['average_duration'], 20), [15, 10, 5]),
                'status': 'good' if metrics_data['average_duration'] <= 15 else 'poor'
            },
            'cache_efficiency': {
                'value': cache_efficiency,
                'grade': get_grade(cache_efficiency, [30, 20, 10]),
                'status': 'good' if cache_efficiency >= 20 else 'poor'
            },
            'error_rate': {
                'value': error_rate,
                'grade': get_grade(10 - min(error_rate, 10), [8, 6, 4]),
                'status': 'good' if error_rate <= 5 else 'poor'
            }
        },
        'recommendations': []
    }

    # Generate recommendations
    if metrics_data['success_rate'] < 95:
        performance_summary['recommendations'].append(
            "Investigate causes of analysis failures and improve error handling"
        )

    if metrics_data['average_duration'] > 15:
        performance_summary['recommendations'].append(
            "Optimize analysis performance or consider increasing timeout limits"
        )

    if cache_efficiency < 20:
        performance_summary['recommendations'].append(
            "Review caching strategy to improve response times"
        )

    if error_rate > 5:
        performance_summary['recommendations'].append(
            "Address high error rate by improving input validation and error handling"
        )

    return jsonify(performance_summary), 200

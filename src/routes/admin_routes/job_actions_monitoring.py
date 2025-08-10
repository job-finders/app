"""
Job Actions Monitoring Dashboard Routes

Provides admin endpoints for monitoring job actions performance,
viewing metrics, and managing alerts.
"""

from flask import Blueprint, jsonify, request, render_template
from datetime import datetime, timedelta
import json

from src.utils.job_actions_monitoring import job_actions_monitor
from src.utils.job_actions_logger import job_actions_health, job_actions_logger
from src.authentication.auth import require_admin_auth
from src.database.sql import engine
from sqlalchemy import text

# Create blueprint
job_actions_monitoring_bp = Blueprint(
    'job_actions_monitoring',
    __name__,
    url_prefix='/admin/job-actions-monitoring'
)


@job_actions_monitoring_bp.route('/dashboard')
@require_admin_auth
def monitoring_dashboard():
    """Render monitoring dashboard page"""
    return render_template('admin/job_actions_monitoring_dashboard.html')


@job_actions_monitoring_bp.route('/api/metrics')
@require_admin_auth
def get_metrics():
    """Get current metrics data for dashboard"""
    try:
        time_window = request.args.get('time_window', 60, type=int)
        dashboard_data = job_actions_monitor.get_dashboard_data(time_window)

        return jsonify({
            'success': True,
            'data': dashboard_data
        })

    except Exception as e:
        job_actions_logger.log_error(e, {
            'context': 'monitoring_api_metrics',
            'endpoint': '/api/metrics'
        })

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@job_actions_monitoring_bp.route('/api/health')
@require_admin_auth
def get_health_status():
    """Get current health status"""
    try:
        # Get monitoring health status
        monitor_health = job_actions_monitor.get_health_status()

        # Get detailed health check
        detailed_health = job_actions_health.run_health_check()

        return jsonify({
            'success': True,
            'data': {
                'monitor_health': monitor_health,
                'detailed_health': detailed_health,
                'timestamp': datetime.utcnow().isoformat()
            }
        })

    except Exception as e:
        job_actions_logger.log_error(e, {
            'context': 'monitoring_api_health',
            'endpoint': '/api/health'
        })

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@job_actions_monitoring_bp.route('/api/alerts')
@require_admin_auth
def get_alerts():
    """Get current alerts and alert history"""
    try:
        dashboard_data = job_actions_monitor.get_dashboard_data(60)

        return jsonify({
            'success': True,
            'data': {
                'active_alerts': dashboard_data['active_alerts'],
                'alert_definitions': dashboard_data['alert_definitions']
            }
        })

    except Exception as e:
        job_actions_logger.log_error(e, {
            'context': 'monitoring_api_alerts',
            'endpoint': '/api/alerts'
        })

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@job_actions_monitoring_bp.route('/api/database-stats')
@require_admin_auth
def get_database_stats():
    """Get database statistics for job actions tables"""
    try:
        with engine.connect() as conn:
            # Get table sizes and row counts
            table_stats_query = text("""
                                     SELECT TABLE_NAME,
                                            TABLE_ROWS,
                                            ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS size_mb,
                                            ROUND((DATA_LENGTH / 1024 / 1024), 2)                  AS data_mb,
                                            ROUND((INDEX_LENGTH / 1024 / 1024), 2)                 AS index_mb
                                     FROM information_schema.TABLES
                                     WHERE TABLE_SCHEMA = DATABASE()
                                       AND TABLE_NAME IN ('job_likes', 'job_shares', 'jobs', 'jobseeker_profiles')
                                     ORDER BY TABLE_ROWS DESC
                                     """)

            table_stats = conn.execute(table_stats_query).fetchall()

            # Get recent activity stats
            activity_stats_query = text("""
                                        SELECT 'likes'                                                                     as action_type,
                                               COUNT(*)                                                                    as total_count,
                                               COUNT(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 1 END) as last_24h,
                                               COUNT(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 END)   as last_7d,
                                               COUNT(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 END)  as last_30d
                                        FROM job_likes

                                        UNION ALL

                                        SELECT 'shares'                                                                   as action_type,
                                               COUNT(*)                                                                   as total_count,
                                               COUNT(CASE WHEN shared_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 1 END) as last_24h,
                                               COUNT(CASE WHEN shared_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 END)   as last_7d,
                                               COUNT(CASE WHEN shared_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 END)  as last_30d
                                        FROM job_shares
                                        """)

            activity_stats = conn.execute(activity_stats_query).fetchall()

            # Get top performing jobs (most liked/shared)
            top_jobs_query = text("""
                                  SELECT j.job_id,
                                         j.title,
                                         j.company_id,
                                         COALESCE(like_counts.like_count, 0)     as like_count,
                                         COALESCE(share_counts.share_count, 0)   as share_count,
                                         (COALESCE(like_counts.like_count, 0) +
                                          COALESCE(share_counts.share_count, 0)) as total_engagement
                                  FROM jobs j
                                           LEFT JOIN (SELECT job_id, COUNT(*) as like_count
                                                      FROM job_likes
                                                      WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                                                      GROUP BY job_id) like_counts ON j.job_id = like_counts.job_id
                                           LEFT JOIN (SELECT job_id, COUNT(*) as share_count
                                                      FROM job_shares
                                                      WHERE shared_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                                                      GROUP BY job_id) share_counts ON j.job_id = share_counts.job_id
                                  WHERE j.status = 'active'
                                  ORDER BY total_engagement DESC
                                  LIMIT 10
                                  """)

            top_jobs = conn.execute(top_jobs_query).fetchall()

            # Get sharing platform statistics
            platform_stats_query = text("""
                                        SELECT share_method,
                                               COUNT(*)                                                                 as share_count,
                                               COUNT(CASE WHEN shared_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 END) as last_7d_count
                                        FROM job_shares
                                        GROUP BY share_method
                                        ORDER BY share_count DESC
                                        """)

            platform_stats = conn.execute(platform_stats_query).fetchall()

        return jsonify({
            'success': True,
            'data': {
                'table_stats': [
                    {
                        'table_name': row[0],
                        'row_count': row[1],
                        'size_mb': row[2],
                        'data_mb': row[3],
                        'index_mb': row[4]
                    }
                    for row in table_stats
                ],
                'activity_stats': [
                    {
                        'action_type': row[0],
                        'total_count': row[1],
                        'last_24h': row[2],
                        'last_7d': row[3],
                        'last_30d': row[4]
                    }
                    for row in activity_stats
                ],
                'top_jobs': [
                    {
                        'job_id': row[0],
                        'title': row[1],
                        'company_id': row[2],
                        'like_count': row[3],
                        'share_count': row[4],
                        'total_engagement': row[5]
                    }
                    for row in top_jobs
                ],
                'platform_stats': [
                    {
                        'platform': row[0],
                        'total_shares': row[1],
                        'recent_shares': row[2]
                    }
                    for row in platform_stats
                ]
            }
        })

    except Exception as e:
        job_actions_logger.log_error(e, {
            'context': 'monitoring_api_database_stats',
            'endpoint': '/api/database-stats'
        })

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@job_actions_monitoring_bp.route('/api/performance-analysis')
@require_admin_auth
def get_performance_analysis():
    """Get performance analysis data"""
    try:
        with engine.connect() as conn:
            # Analyze query performance (if slow query log is enabled)
            slow_queries_query = text("""
                                      SELECT 'job_actions' as category,
                                             COUNT(*)      as slow_query_count
                                      FROM information_schema.PROCESSLIST
                                      WHERE INFO LIKE '%job_likes%'
                                         OR INFO LIKE '%job_shares%'
                                          AND TIME > 1
                                      """)

            try:
                slow_queries = conn.execute(slow_queries_query).fetchall()
            except:
                slow_queries = []

            # Get index usage statistics
            index_stats_query = text("""
                                     SELECT TABLE_NAME,
                                            INDEX_NAME,
                                            CARDINALITY,
                                            CASE
                                                WHEN CARDINALITY = 0 THEN 'Unused'
                                                WHEN CARDINALITY < 100 THEN 'Low Usage'
                                                WHEN CARDINALITY < 1000 THEN 'Medium Usage'
                                                ELSE 'High Usage'
                                                END as usage_level
                                     FROM information_schema.STATISTICS
                                     WHERE TABLE_SCHEMA = DATABASE()
                                       AND TABLE_NAME IN ('job_likes', 'job_shares')
                                       AND INDEX_NAME != 'PRIMARY'
                                     ORDER BY TABLE_NAME, CARDINALITY DESC
                                     """)

            index_stats = conn.execute(index_stats_query).fetchall()

            # Get recent error patterns from logs (simplified)
            error_patterns = []  # Would be populated from log analysis

        # Get current metrics for performance analysis
        dashboard_data = job_actions_monitor.get_dashboard_data(60)
        response_time_history = dashboard_data['metrics_history'].get('job_actions_response_time', [])

        # Calculate performance trends
        if response_time_history:
            recent_times = [point['value'] for point in response_time_history[-10:]]
            avg_recent = sum(recent_times) / len(recent_times) if recent_times else 0

            older_times = [point['value'] for point in response_time_history[-20:-10]]
            avg_older = sum(older_times) / len(older_times) if older_times else 0

            trend = "improving" if avg_recent < avg_older else "degrading" if avg_recent > avg_older else "stable"
        else:
            avg_recent = 0
            trend = "no_data"

        return jsonify({
            'success': True,
            'data': {
                'slow_queries': [
                    {
                        'category': row[0],
                        'count': row[1]
                    }
                    for row in slow_queries
                ],
                'index_stats': [
                    {
                        'table_name': row[0],
                        'index_name': row[1],
                        'cardinality': row[2],
                        'usage_level': row[3]
                    }
                    for row in index_stats
                ],
                'performance_trend': {
                    'current_avg_response_time': avg_recent,
                    'trend': trend
                },
                'error_patterns': error_patterns,
                'recommendations': self._generate_performance_recommendations(index_stats, avg_recent)
            }
        })

    except Exception as e:
        job_actions_logger.log_error(e, {
            'context': 'monitoring_api_performance_analysis',
            'endpoint': '/api/performance-analysis'
        })

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _generate_performance_recommendations(index_stats, avg_response_time):
    """Generate performance recommendations based on current metrics"""
    recommendations = []

    # Check for unused indexes
    unused_indexes = [stat for stat in index_stats if stat[2] == 0]  # cardinality = 0
    if unused_indexes:
        recommendations.append({
            'type': 'index_optimization',
            'priority': 'medium',
            'message': f"Consider removing {len(unused_indexes)} unused indexes to improve write performance"
        })

    # Check response time
    if avg_response_time > 1000:  # 1 second
        recommendations.append({
            'type': 'performance',
            'priority': 'high',
            'message': f"Average response time ({avg_response_time:.0f}ms) is high. Consider query optimization."
        })

    # Check for missing indexes (simplified check)
    job_likes_indexes = [stat[1] for stat in index_stats if stat[0] == 'job_likes']
    if 'ix_job_likes_user_job' not in job_likes_indexes:
        recommendations.append({
            'type': 'index_missing',
            'priority': 'high',
            'message': "Missing essential index ix_job_likes_user_job for optimal query performance"
        })

    return recommendations


@job_actions_monitoring_bp.route('/api/export-metrics')
@require_admin_auth
def export_metrics():
    """Export metrics data for external analysis"""
    try:
        time_window = request.args.get('time_window', 1440, type=int)  # Default 24 hours
        format_type = request.args.get('format', 'json')

        dashboard_data = job_actions_monitor.get_dashboard_data(time_window)

        if format_type == 'csv':
            # Convert to CSV format (simplified)
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write headers
            writer.writerow(['timestamp', 'metric_name', 'value', 'labels'])

            # Write data
            for metric_name, history in dashboard_data['metrics_history'].items():
                for point in history:
                    writer.writerow([
                        point['timestamp'],
                        metric_name,
                        point['value'],
                        json.dumps(point['labels'])
                    ])

            response = output.getvalue()
            output.close()

            return response, 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename=job_actions_metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }

        else:  # JSON format
            return jsonify({
                'success': True,
                'data': dashboard_data,
                'export_info': {
                    'time_window_minutes': time_window,
                    'exported_at': datetime.utcnow().isoformat(),
                    'format': format_type
                }
            })

    except Exception as e:
        job_actions_logger.log_error(e, {
            'context': 'monitoring_api_export_metrics',
            'endpoint': '/api/export-metrics'
        })

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Error handlers
@job_actions_monitoring_bp.errorhandler(403)
def forbidden(error):
    return jsonify({
        'success': False,
        'error': 'Access denied. Admin privileges required.'
    }), 403


@job_actions_monitoring_bp.errorhandler(500)
def internal_error(error):
    job_actions_logger.log_error(error, {
        'context': 'monitoring_blueprint_error',
        'endpoint': request.endpoint
    })

    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

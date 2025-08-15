"""
Admin routes for job match scoring monitoring and management

This module provides admin endpoints for monitoring the performance
and health of the job match scoring system.
"""

from flask import Blueprint, render_template, jsonify, request
from src.authentication import system_admin_login
from src.routes import flask_error_handler
from src.monitoring.match_scoring_metrics import monitor, get_system_health
from src.services.optimized_match_scoring import optimizer


# Blueprint definition
match_scoring_admin = Blueprint('match_scoring_admin', __name__, url_prefix='/admin/match-scoring')


@match_scoring_admin.route('/dashboard')
@flask_error_handler
@system_admin_login
async def monitoring_dashboard():
    """Display match scoring monitoring dashboard"""
    return render_template('admin/match_scoring_dashboard.html')


@match_scoring_admin.route('/api/health')
@flask_error_handler
@system_admin_login
async def health_check():
    """Get system health status for match scoring"""
    health_data = get_system_health()
    return jsonify(health_data)


@match_scoring_admin.route('/api/performance')
@flask_error_handler
@system_admin_login
async def performance_metrics():
    """Get performance metrics for match scoring"""
    hours = request.args.get('hours', 24, type=int)
    
    # Get performance summary
    performance_data = monitor.get_performance_summary(hours=hours)
    
    # Get optimization stats
    optimization_stats = optimizer.service.get_performance_stats()
    
    # Get recommendations
    recommendations = optimizer.get_optimization_recommendations()
    
    return jsonify({
        'performance': performance_data,
        'optimization': optimization_stats,
        'recommendations': recommendations,
        'timeframe_hours': hours
    })


@match_scoring_admin.route('/api/cache-stats')
@flask_error_handler
@system_admin_login
async def cache_statistics():
    """Get cache performance statistics"""
    try:
        from src.cache.cache_redis import cache
        
        # Get cache info
        if hasattr(cache, 'redis_client'):
            info = cache.redis_client.info()
            
            cache_stats = {
                'memory_usage': info.get('used_memory_human', 'unknown'),
                'total_keys': info.get('db0', {}).get('keys', 0) if 'db0' in info else 0,
                'hit_rate': info.get('keyspace_hits', 0) / max(
                    info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1
                ),
                'connected_clients': info.get('connected_clients', 0),
                'uptime_seconds': info.get('uptime_in_seconds', 0)
            }
        else:
            cache_stats = {'error': 'Cache client not available'}
        
        return jsonify(cache_stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@match_scoring_admin.route('/api/clear-cache', methods=['POST'])
@flask_error_handler
@system_admin_login
async def clear_cache():
    """Clear match scoring cache"""
    try:
        from src.cache.cache_redis import cache
        
        # Get parameters
        cache_type = request.json.get('type', 'all')  # 'all', 'match_scores', 'user_profiles'
        user_id = request.json.get('user_id')  # Optional: clear cache for specific user
        
        if user_id:
            # Clear cache for specific user
            await optimizer.service.invalidate_user_cache(user_id)
            message = f"Cache cleared for user {user_id}"
        elif cache_type == 'match_scores':
            # Clear only match score cache
            cache.delete_pattern("match_score:*")
            message = "Match score cache cleared"
        elif cache_type == 'user_profiles':
            # Clear user profile cache
            cache.delete_pattern("user_profile:*")
            message = "User profile cache cleared"
        else:
            # Clear all match scoring related cache
            cache.delete_pattern("match_score:*")
            cache.delete_pattern("user_profile:*")
            cache.delete_pattern("detailed_match:*")
            message = "All match scoring cache cleared"
        
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@match_scoring_admin.route('/api/circuit-breaker')
@flask_error_handler
@system_admin_login
async def circuit_breaker_status():
    """Get circuit breaker status and controls"""
    service = optimizer.service
    
    status = {
        'is_open': service.circuit_open,
        'failure_count': service.failure_count,
        'failure_threshold': service.failure_threshold,
        'last_failure_time': service.last_failure_time,
        'timeout_seconds': service.circuit_timeout
    }
    
    return jsonify(status)


@match_scoring_admin.route('/api/circuit-breaker/reset', methods=['POST'])
@flask_error_handler
@system_admin_login
def reset_circuit_breaker():
    """Reset circuit breaker to closed state"""
    try:
        service = optimizer.service
        service.circuit_open = False
        service.failure_count = 0
        service.last_failure_time = 0
        
        return jsonify({
            'success': True, 
            'message': 'Circuit breaker reset successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@match_scoring_admin.route('/api/performance-tuning', methods=['POST'])
@flask_error_handler
@system_admin_login
async def update_performance_settings():
    """Update performance settings for match scoring"""
    try:
        settings = request.json
        service = optimizer.service
        
        # Update batch size
        if 'batch_size' in settings:
            batch_size = int(settings['batch_size'])
            if 1 <= batch_size <= 200:
                service.batch_size = batch_size
        
        # Update max workers
        if 'max_workers' in settings:
            max_workers = int(settings['max_workers'])
            if 1 <= max_workers <= 20:
                service.max_workers = max_workers
                # Recreate executor with new worker count
                service.executor.shutdown(wait=False)
                from concurrent.futures import ThreadPoolExecutor
                service.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Update circuit breaker settings
        if 'failure_threshold' in settings:
            threshold = int(settings['failure_threshold'])
            if 1 <= threshold <= 20:
                service.failure_threshold = threshold
        
        if 'circuit_timeout' in settings:
            timeout = int(settings['circuit_timeout'])
            if 60 <= timeout <= 3600:  # 1 minute to 1 hour
                service.circuit_timeout = timeout
        
        return jsonify({
            'success': True,
            'message': 'Performance settings updated',
            'current_settings': service.get_performance_stats()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@match_scoring_admin.route('/api/analytics')
@flask_error_handler
@system_admin_login
async def analytics_summary():
    """Get analytics summary for match scoring usage"""
    try:
        # This would read from analytics logs and provide summary
        # For now, return placeholder data
        
        analytics_data = {
            'modal_interactions': {
                'total_opens': 1250,
                'successful_loads': 1180,
                'errors': 70,
                'average_load_time': 0.85
            },
            'match_scores_displayed': {
                'total_jobs_scored': 15000,
                'unique_users': 450,
                'average_scores_per_user': 33.3
            },
            'conversion_rates': {
                'view_to_apply': 0.12,
                'high_match_apply_rate': 0.28,
                'low_match_apply_rate': 0.05
            },
            'cache_performance': {
                'hit_rate': 0.78,
                'average_response_time_cached': 0.05,
                'average_response_time_uncached': 0.95
            }
        }
        
        return jsonify(analytics_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@match_scoring_admin.route('/api/test-scoring', methods=['POST'])
@flask_error_handler
@system_admin_login
async def test_scoring_performance():
    """Test match scoring performance with sample data"""
    try:
        # Create test data
        from src.database.models import Job
        from unittest.mock import Mock
        
        # Mock jobs
        test_jobs = []
        for i in range(10):
            job = Mock(spec=Job)
            job.job_id = f"test_job_{i}"
            job.title = f"Test Job {i}"
            job.location = "Cape Town"
            test_jobs.append(job)
        
        # Mock user profile
        user_profile = Mock()
        user_profile.location = "Cape Town"
        user_profile.skills = ["Python", "Django"]
        user_profile.experience_level = "Mid Level"
        
        # Test batch scoring
        import time
        start_time = time.time()
        
        from src.services.optimized_match_scoring import BatchScoringRequest
        request = BatchScoringRequest(
            user_id="test_user",
            jobs=test_jobs,
            user_profile=user_profile
        )
        
        results = await optimizer.service.calculate_batch_scores(request)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        return jsonify({
            'success': True,
            'test_results': {
                'jobs_processed': len(results),
                'execution_time': execution_time,
                'average_time_per_job': execution_time / len(results),
                'successful_scores': sum(1 for r in results if r.score is not None),
                'cached_scores': sum(1 for r in results if r.cached),
                'errors': sum(1 for r in results if r.error is not None)
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
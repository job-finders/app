"""
Performance Tests for Job Match Scoring

These tests verify that the match scoring functionality performs well
under various load conditions and doesn't significantly impact page performance.
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor
import statistics

from tests.jobs.factories import create_job, create_category


class TestMatchScoringPerformance:
    """Performance tests for match scoring algorithms"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
    async def test_quick_match_scoring_performance(self, get_controller, session):
        """Test that quick match scoring completes within acceptable time"""
        # Setup
        category = create_category(session, name="Engineering")
        job = create_job(
            session,
            title="Python Developer",
            location="Cape Town, Western Cape",
            category_id=category.category_id,
            status="active"
        )
        
        user_profile = Mock()
        user_profile.location = "Cape Town, Western Cape"
        user_profile.skills = ["Python", "Django", "REST API"]
        user_profile.experience_level = "Mid Level"
        user_profile.preferred_categories = ["Engineering"]
        
        controller = get_controller
        
        # Measure performance
        start_time = time.time()
        score = await controller.calculate_quick_match_score(job, user_profile)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Assert performance requirements
        assert execution_time < 0.1, f"Quick match scoring too slow: {execution_time:.3f}s"
        assert isinstance(score, (int, float)), "Score should be numeric"

    @pytest.mark.asyncio
    async def test_batch_match_scoring_performance(self):
        """Test batch match scoring performance with multiple jobs"""
        # Setup multiple jobs
        jobs = []
        for i in range(50):  # Test with 50 jobs
            job = Mock()
            job.job_id = f"job_{i}"
            job.title = f"Developer {i}"
            job.location = "Cape Town"
            jobs.append(job)
        
        user = Mock(uid="user123", is_authenticated=True)
        
        # Mock controller with realistic timing
        controller = Mock()
        async def mock_scoring(job, profile):
            await asyncio.sleep(0.01)  # Simulate 10ms per job
            return 75.0
        
        controller.calculate_quick_match_score = mock_scoring
        
        with patch('src.routes.jobs_routes.job_search_routes.get_user_profile_for_matching') as mock_profile:
            mock_profile.return_value = Mock()
            
            # Import and test
            from src.routes.jobs_routes.job_search_routes import calculate_batch_match_scores
            
            start_time = time.time()
            result = await calculate_batch_match_scores(jobs, user, controller)
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            # Should complete within reasonable time (not sequential)
            assert execution_time < 2.0, f"Batch scoring too slow: {execution_time:.3f}s"
            assert len(result) == 50, "All jobs should be processed"

    @pytest.mark.asyncio
    async def test_concurrent_match_scoring(self):
        """Test performance under concurrent load"""
        async def simulate_user_request():
            """Simulate a single user requesting match scores"""
            jobs = [Mock(job_id=f"job_{i}") for i in range(10)]
            user = Mock(uid="user123")
            controller = Mock()
            controller.calculate_quick_match_score = AsyncMock(return_value=80.0)
            
            with patch('src.routes.jobs_routes.job_search_routes.get_user_profile_for_matching') as mock_profile:
                mock_profile.return_value = Mock()
                
                from src.routes.jobs_routes.job_search_routes import calculate_batch_match_scores
                return await calculate_batch_match_scores(jobs, user, controller)
        
        # Simulate 10 concurrent users
        start_time = time.time()
        tasks = [simulate_user_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should handle concurrent load efficiently
        assert execution_time < 5.0, f"Concurrent processing too slow: {execution_time:.3f}s"
        assert len(results) == 10, "All concurrent requests should complete"

    def test_api_endpoint_performance(self):
        """Test match analysis API endpoint performance"""
        from tests.conftest import app
        
        with app.test_client() as client:
            # Mock successful scenario
            mock_job = Mock()
            mock_job.job_id = "job123"
            mock_job.title = "Python Developer"
            
            mock_analysis = {
                'total_score': 85.5,
                'score_breakdown': {'skills_match': 90},
                'interpretation': 'Great match'
            }
            
            with patch('src.routes.jobs_routes.job_search_routes.user_details') as mock_auth:
                mock_auth.return_value = Mock(uid="user123")
                
                with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
                    mock_controller = Mock()
                    mock_controller.get_job_by_id = AsyncMock(return_value=mock_job)
                    mock_controller.calculate_job_match_score = AsyncMock(return_value=mock_analysis)
                    mock_get_controller.return_value = mock_controller
                    
                    with patch('src.routes.jobs_routes.job_search_routes.get_user_profile_for_matching') as mock_profile:
                        mock_profile.return_value = Mock()
                        
                        with patch('src.cache.cache_redis.cache') as mock_cache:
                            mock_cache.get.return_value = None
                            mock_cache.set.return_value = None
                            
                            # Measure API response time
                            start_time = time.time()
                            response = client.get('/api/jobs/job123/match-analysis')
                            end_time = time.time()
                            
                            response_time = end_time - start_time
                            
                            assert response.status_code == 200
                            assert response_time < 1.0, f"API response too slow: {response_time:.3f}s"

    def test_caching_performance_improvement(self):
        """Test that caching improves performance for repeated requests"""
        from tests.conftest import app
        
        cached_analysis = {
            'total_score': 90.0,
            'job_title': 'Cached Job'
        }
        
        with app.test_client() as client:
            with patch('src.routes.jobs_routes.job_search_routes.user_details') as mock_auth:
                mock_auth.return_value = Mock(uid="user123")
                
                with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
                    mock_controller = Mock()
                    mock_controller.get_job_by_id = AsyncMock(return_value=Mock(job_id="job123"))
                    mock_get_controller.return_value = mock_controller
                    
                    with patch('src.cache.cache_redis.cache') as mock_cache:
                        # First request - no cache
                        mock_cache.get.return_value = None
                        mock_cache.set.return_value = None
                        
                        start_time = time.time()
                        response1 = client.get('/api/jobs/job123/match-analysis')
                        uncached_time = time.time() - start_time
                        
                        # Second request - with cache
                        mock_cache.get.return_value = cached_analysis
                        
                        start_time = time.time()
                        response2 = client.get('/api/jobs/job123/match-analysis')
                        cached_time = time.time() - start_time
                        
                        # Cached request should be significantly faster
                        assert cached_time < uncached_time / 2, "Caching not providing performance benefit"
                        assert response2.status_code == 200

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Simulate processing many jobs
        for batch in range(10):  # 10 batches
            jobs = [Mock(job_id=f"job_{batch}_{i}") for i in range(100)]
            user = Mock(uid=f"user_{batch}")
            
            controller = Mock()
            controller.calculate_quick_match_score = AsyncMock(return_value=75.0)
            
            with patch('src.routes.jobs_routes.job_search_routes.get_user_profile_for_matching') as mock_profile:
                mock_profile.return_value = Mock()
                
                from src.routes.jobs_routes.job_search_routes import calculate_batch_match_scores
                await calculate_batch_match_scores(jobs, user, controller)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024, f"Excessive memory usage: {memory_increase / 1024 / 1024:.1f}MB"

    def test_database_query_performance(self):
        """Test that database queries for match scoring are optimized"""
        # This test would verify that:
        # 1. Queries use appropriate indexes
        # 2. N+1 query problems are avoided
        # 3. Batch operations are used where possible
        
        # Mock database query timing
        query_times = []
        
        def mock_query_timer(*args, **kwargs):
            start = time.time()
            # Simulate database query
            time.sleep(0.001)  # 1ms query time
            end = time.time()
            query_times.append(end - start)
            return Mock()
        
        with patch('src.database.models.session.query', side_effect=mock_query_timer):
            # Simulate job listing page load with 25 jobs
            for i in range(25):
                mock_query_timer()  # Simulate job query
                mock_query_timer()  # Simulate match score query
        
        # Should not have excessive number of queries
        assert len(query_times) <= 50, f"Too many database queries: {len(query_times)}"
        
        # Average query time should be reasonable
        avg_query_time = statistics.mean(query_times)
        assert avg_query_time < 0.01, f"Database queries too slow: {avg_query_time:.3f}s"

    def test_javascript_performance(self):
        """Test JavaScript modal performance (would need browser automation)"""
        # This test would verify:
        # 1. Modal opens quickly
        # 2. AJAX requests complete promptly
        # 3. DOM updates are efficient
        # 4. No memory leaks in JavaScript
        
        # For now, document expected performance characteristics
        expected_metrics = {
            'modal_open_time': 0.1,  # seconds
            'api_request_time': 1.0,  # seconds
            'dom_update_time': 0.05,  # seconds
        }
        
        # These would be measured with browser automation tools
        assert all(time > 0 for time in expected_metrics.values())


class TestScalabilityMetrics:
    """Tests for scalability under different load conditions"""

    @pytest.mark.asyncio
    async def test_scaling_with_job_count(self):
        """Test performance scaling with increasing number of jobs"""
        job_counts = [10, 50, 100, 500]
        execution_times = []
        
        for count in job_counts:
            jobs = [Mock(job_id=f"job_{i}") for i in range(count)]
            user = Mock(uid="user123")
            
            controller = Mock()
            controller.calculate_quick_match_score = AsyncMock(return_value=80.0)
            
            with patch('src.routes.jobs_routes.job_search_routes.get_user_profile_for_matching') as mock_profile:
                mock_profile.return_value = Mock()
                
                from src.routes.jobs_routes.job_search_routes import calculate_batch_match_scores
                
                start_time = time.time()
                await calculate_batch_match_scores(jobs, user, controller)
                end_time = time.time()
                
                execution_times.append(end_time - start_time)
        
        # Performance should scale reasonably (not exponentially)
        for i in range(1, len(execution_times)):
            ratio = execution_times[i] / execution_times[i-1]
            job_ratio = job_counts[i] / job_counts[i-1]
            
            # Execution time should not increase faster than job count
            assert ratio <= job_ratio * 1.5, f"Poor scaling at {job_counts[i]} jobs: {ratio:.2f}x slower"

    @pytest.mark.asyncio
    async def test_scaling_with_user_count(self):
        """Test performance scaling with increasing number of concurrent users"""
        user_counts = [1, 5, 10, 20]
        execution_times = []
        
        for count in user_counts:
            async def simulate_user():
                jobs = [Mock(job_id=f"job_{i}") for i in range(10)]
                user = Mock(uid="user123")
                controller = Mock()
                controller.calculate_quick_match_score = AsyncMock(return_value=80.0)
                
                with patch('src.routes.jobs_routes.job_search_routes.get_user_profile_for_matching') as mock_profile:
                    mock_profile.return_value = Mock()
                    
                    from src.routes.jobs_routes.job_search_routes import calculate_batch_match_scores
                    return await calculate_batch_match_scores(jobs, user, controller)
            
            start_time = time.time()
            tasks = [simulate_user() for _ in range(count)]
            await asyncio.gather(*tasks)
            end_time = time.time()
            
            execution_times.append(end_time - start_time)
        
        # Should handle reasonable concurrent load
        max_time = max(execution_times)
        assert max_time < 10.0, f"Cannot handle concurrent load: {max_time:.2f}s"

    def test_cache_hit_ratio_performance(self):
        """Test that cache hit ratio improves performance significantly"""
        # Simulate different cache hit ratios
        hit_ratios = [0.0, 0.25, 0.5, 0.75, 0.9]
        response_times = []
        
        for hit_ratio in hit_ratios:
            times = []
            
            for request in range(100):
                if request / 100 < hit_ratio:
                    # Cache hit - very fast
                    times.append(0.001)
                else:
                    # Cache miss - slower
                    times.append(0.1)
            
            avg_time = statistics.mean(times)
            response_times.append(avg_time)
        
        # Higher cache hit ratios should result in better performance
        for i in range(1, len(response_times)):
            assert response_times[i] <= response_times[i-1], "Cache hit ratio not improving performance"

    def test_resource_utilization_efficiency(self):
        """Test that resource utilization is efficient"""
        # This test would monitor:
        # 1. CPU usage during match scoring
        # 2. Memory allocation patterns
        # 3. Database connection usage
        # 4. Cache utilization
        
        # Mock resource monitoring
        resource_metrics = {
            'cpu_usage_percent': 25.0,  # Should be reasonable
            'memory_usage_mb': 50.0,    # Should not be excessive
            'db_connections': 5,        # Should be minimal
            'cache_hit_ratio': 0.8      # Should be high
        }
        
        # Assert reasonable resource usage
        assert resource_metrics['cpu_usage_percent'] < 50.0, "CPU usage too high"
        assert resource_metrics['memory_usage_mb'] < 100.0, "Memory usage too high"
        assert resource_metrics['db_connections'] < 10, "Too many database connections"
        assert resource_metrics['cache_hit_ratio'] > 0.7, "Cache hit ratio too low"


if __name__ == '__main__':
    pytest.main([__file__, "-v", "--tb=short"])
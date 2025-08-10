"""
Unit tests for Job Statistics Caching

Tests the caching behavior, TTL functionality, and cache invalidation
for the job statistics service.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.services.job_statistics_service import JobStatisticsService
from src.database.models.job_statistics import (
    JobStatistics, ApplicationStatistics, CompetitivenessMetrics,
    TrendAnalysis, CompanyStatistics
)
from src.database.constants import utc_time


class TestJobStatisticsCaching:
    """Test caching functionality for job statistics"""
    
    @pytest.fixture
    def service_with_redis(self):
        """Create a JobStatisticsService with mocked Redis"""
        service = JobStatisticsService()
        service.redis_client = AsyncMock()
        return service
    
    @pytest.fixture
    def service_without_redis(self):
        """Create a JobStatisticsService without Redis"""
        service = JobStatisticsService()
        service.redis_client = None
        return service
    
    @pytest.fixture
    def sample_statistics(self):
        """Create sample statistics for testing"""
        return JobStatistics(
            job_id="test-job-123",
            application_stats=ApplicationStatistics(
                total_applications=10,
                applications_per_day=2.0,
                days_since_posted=5
            ),
            competitiveness=CompetitivenessMetrics(
                average_match_score=75.0,
                total_ats_reports=8
            ),
            trends=TrendAnalysis(),
            company_stats=CompanyStatistics(
                total_jobs_12_months=12,
                application_response_rate=70.0
            ),
            calculated_at=utc_time()
        )


class TestCacheStorage:
    """Test cache storage operations"""
    
    def test_cache_statistics_success(self, service_with_redis, sample_statistics):
        """Test successful caching of statistics"""
        asyncio.run(service_with_redis._cache_statistics("test-job-123", sample_statistics))
        
        # Verify Redis setex was called with correct parameters
        service_with_redis.redis_client.setex.assert_called_once()
        call_args = service_with_redis.redis_client.setex.call_args
        
        # Check cache key
        assert call_args[0][0] == "job_stats:test-job-123"
        
        # Check TTL
        assert call_args[0][1] == sample_statistics.cache_ttl_seconds
        
        # Check data is JSON serializable
        cached_data = call_args[0][2]
        parsed_data = json.loads(cached_data)
        assert parsed_data["job_id"] == "test-job-123"
    
    def test_cache_statistics_redis_error(self, service_with_redis, sample_statistics):
        """Test caching when Redis raises an error"""
        service_with_redis.redis_client.setex.side_effect = Exception("Redis error")
        
        # Should not raise exception, just log warning
        asyncio.run(service_with_redis._cache_statistics("test-job-123", sample_statistics))
        
        service_with_redis.redis_client.setex.assert_called_once()
    
    def test_cache_statistics_no_redis(self, service_without_redis, sample_statistics):
        """Test caching when Redis is not available"""
        # Should not raise exception when Redis is None
        asyncio.run(service_without_redis._cache_statistics("test-job-123", sample_statistics))
        
        # No assertions needed - just verify it doesn't crash


class TestCacheRetrieval:
    """Test cache retrieval operations"""
    
    def test_get_cached_statistics_success(self, service_with_redis):
        """Test successful retrieval of cached statistics"""
        # Mock cached data
        cached_data = {
            "job_id": "test-job-123",
            "application_stats": {
                "total_applications": 10,
                "applications_per_day": 2.0,
                "application_sources": {"website": 8, "external": 2},
                "recent_application_trend": "stable",
                "days_since_posted": 5
            },
            "competitiveness": {
                "match_score_distribution": {"61-80": 5, "81-100": 3},
                "average_match_score": 75.0,
                "top_matched_keywords": ["python", "django"],
                "top_missing_keywords": ["react"],
                "ats_readiness_percentage": 80.0,
                "total_ats_reports": 8
            },
            "trends": {
                "daily_applications": [],
                "application_velocity": "steady",
                "industry_comparison": {"this_job": 2.0, "industry_average": 1.5},
                "peak_application_days": ["Monday", "Wednesday"],
                "trend_direction": "stable"
            },
            "company_stats": {
                "total_jobs_12_months": 12,
                "average_applications_per_job": 8.5,
                "application_response_rate": 70.0,
                "hiring_activity_level": "medium",
                "total_active_jobs": 3
            },
            "calculated_at": utc_time().isoformat(),
            "cache_ttl_seconds": 3600
        }
        
        service_with_redis.redis_client.get.return_value = json.dumps(cached_data)
        
        result = asyncio.run(service_with_redis._get_cached_statistics("test-job-123"))
        
        assert isinstance(result, JobStatistics)
        assert result.job_id == "test-job-123"
        assert result.application_stats.total_applications == 10
        assert result.competitiveness.average_match_score == 75.0
        
        # Verify correct cache key was used
        service_with_redis.redis_client.get.assert_called_once_with("job_stats:test-job-123")
    
    def test_get_cached_statistics_not_found(self, service_with_redis):
        """Test retrieval when no cached data exists"""
        service_with_redis.redis_client.get.return_value = None
        
        result = asyncio.run(service_with_redis._get_cached_statistics("test-job-123"))
        
        assert result is None
        service_with_redis.redis_client.get.assert_called_once_with("job_stats:test-job-123")
    
    def test_get_cached_statistics_invalid_json(self, service_with_redis):
        """Test retrieval when cached data is invalid JSON"""
        service_with_redis.redis_client.get.return_value = "invalid json data"
        
        result = asyncio.run(service_with_redis._get_cached_statistics("test-job-123"))
        
        assert result is None
    
    def test_get_cached_statistics_redis_error(self, service_with_redis):
        """Test retrieval when Redis raises an error"""
        service_with_redis.redis_client.get.side_effect = Exception("Redis connection error")
        
        result = asyncio.run(service_with_redis._get_cached_statistics("test-job-123"))
        
        assert result is None
    
    def test_get_cached_statistics_no_redis(self, service_without_redis):
        """Test retrieval when Redis is not available"""
        result = asyncio.run(service_without_redis._get_cached_statistics("test-job-123"))
        
        assert result is None


class TestCacheInvalidation:
    """Test cache invalidation operations"""
    
    def test_invalidate_job_statistics_cache_success(self, service_with_redis):
        """Test successful cache invalidation"""
        asyncio.run(service_with_redis.invalidate_job_statistics_cache("test-job-123"))
        
        service_with_redis.redis_client.delete.assert_called_once_with("job_stats:test-job-123")
    
    def test_invalidate_job_statistics_cache_redis_error(self, service_with_redis):
        """Test cache invalidation when Redis raises an error"""
        service_with_redis.redis_client.delete.side_effect = Exception("Redis error")
        
        # Should not raise exception, just log warning
        asyncio.run(service_with_redis.invalidate_job_statistics_cache("test-job-123"))
        
        service_with_redis.redis_client.delete.assert_called_once()
    
    def test_invalidate_job_statistics_cache_no_redis(self, service_without_redis):
        """Test cache invalidation when Redis is not available"""
        # Should not raise exception when Redis is None
        asyncio.run(service_without_redis.invalidate_job_statistics_cache("test-job-123"))


class TestCacheTTL:
    """Test cache TTL (Time To Live) functionality"""
    
    def test_default_cache_ttl(self, sample_statistics):
        """Test default cache TTL value"""
        assert sample_statistics.cache_ttl_seconds == 3600  # 1 hour default
    
    def test_custom_cache_ttl(self):
        """Test custom cache TTL value"""
        stats = JobStatistics(
            job_id="test-job-123",
            application_stats=ApplicationStatistics(),
            competitiveness=CompetitivenessMetrics(),
            trends=TrendAnalysis(),
            company_stats=CompanyStatistics(),
            cache_ttl_seconds=7200  # 2 hours
        )
        
        assert stats.cache_ttl_seconds == 7200
    
    def test_is_data_fresh_within_ttl(self):
        """Test is_data_fresh when data is within TTL"""
        fresh_stats = JobStatistics(
            job_id="test-job-123",
            application_stats=ApplicationStatistics(),
            competitiveness=CompetitivenessMetrics(),
            trends=TrendAnalysis(),
            company_stats=CompanyStatistics(),
            calculated_at=utc_time() - timedelta(minutes=30)  # 30 minutes ago
        )
        
        assert fresh_stats.is_data_fresh is True
    
    def test_is_data_fresh_beyond_ttl(self):
        """Test is_data_fresh when data is beyond TTL"""
        stale_stats = JobStatistics(
            job_id="test-job-123",
            application_stats=ApplicationStatistics(),
            competitiveness=CompetitivenessMetrics(),
            trends=TrendAnalysis(),
            company_stats=CompanyStatistics(),
            calculated_at=utc_time() - timedelta(hours=2)  # 2 hours ago
        )
        
        assert stale_stats.is_data_fresh is False
    
    def test_cache_ttl_used_in_storage(self, service_with_redis):
        """Test that cache TTL is used when storing data"""
        custom_ttl_stats = JobStatistics(
            job_id="test-job-123",
            application_stats=ApplicationStatistics(),
            competitiveness=CompetitivenessMetrics(),
            trends=TrendAnalysis(),
            company_stats=CompanyStatistics(),
            cache_ttl_seconds=1800  # 30 minutes
        )
        
        asyncio.run(service_with_redis._cache_statistics("test-job-123", custom_ttl_stats))
        
        call_args = service_with_redis.redis_client.setex.call_args
        assert call_args[0][1] == 1800  # TTL should be 30 minutes


class TestCacheIntegration:
    """Test cache integration with main service methods"""
    
    @patch('src.utils.route_helpers.get_controller')
    def test_get_job_statistics_uses_cache(self, mock_get_controller, service_with_redis, sample_statistics):
        """Test that get_job_statistics uses cached data when available"""
        # Mock cached data that is fresh
        fresh_cached_data = sample_statistics.model_dump(mode='json')
        service_with_redis.redis_client.get.return_value = json.dumps(fresh_cached_data)
        
        result = asyncio.run(service_with_redis.get_job_statistics("test-job-123"))
        
        # Should return cached data without calling controllers
        assert isinstance(result, JobStatistics)
        assert result.job_id == "test-job-123"
        
        # Verify cache was checked
        service_with_redis.redis_client.get.assert_called_once()
        
        # Verify controllers were not called (since we used cache)
        mock_get_controller.assert_not_called()
    
    @patch('src.utils.route_helpers.get_controller')
    def test_get_job_statistics_bypasses_stale_cache(self, mock_get_controller, service_with_redis):
        """Test that get_job_statistics bypasses stale cached data"""
        # Mock stale cached data
        stale_stats = JobStatistics(
            job_id="test-job-123",
            application_stats=ApplicationStatistics(),
            competitiveness=CompetitivenessMetrics(),
            trends=TrendAnalysis(),
            company_stats=CompanyStatistics(),
            calculated_at=utc_time() - timedelta(hours=2)  # 2 hours ago (stale)
        )
        
        stale_cached_data = stale_stats.model_dump(mode='json')
        service_with_redis.redis_client.get.return_value = json.dumps(stale_cached_data)
        
        # Mock job controller to return a job
        mock_job = Mock()
        mock_job.job_id = "test-job-123"
        mock_job.company_id = "test-company-123"
        mock_job.applications = []
        mock_job.ats_reports = []
        mock_job.posted_at = utc_time() - timedelta(days=7)
        mock_job.total_applications_count = 0
        
        mock_job_controller = AsyncMock()
        mock_job_controller.get_job_by_id.return_value = mock_job
        
        mock_company_controller = AsyncMock()
        mock_company_controller.get_company_by_id.return_value = None
        
        def mock_controller_factory(controller_name):
            if controller_name == 'jobs_search':
                return mock_job_controller
            elif controller_name == 'company':
                return mock_company_controller
            return None
        
        mock_get_controller.side_effect = mock_controller_factory
        
        result = asyncio.run(service_with_redis.get_job_statistics("test-job-123"))
        
        # Should calculate fresh data, not use stale cache
        assert isinstance(result, JobStatistics)
        
        # Verify controllers were called (since cache was stale)
        mock_job_controller.get_job_by_id.assert_called_once_with("test-job-123")
        
        # Verify new data was cached
        service_with_redis.redis_client.setex.assert_called_once()
    
    def test_cache_key_format(self, service_with_redis):
        """Test that cache keys follow the expected format"""
        asyncio.run(service_with_redis._get_cached_statistics("test-job-123"))
        
        service_with_redis.redis_client.get.assert_called_once_with("job_stats:test-job-123")
        
        asyncio.run(service_with_redis.invalidate_job_statistics_cache("another-job-456"))
        
        service_with_redis.redis_client.delete.assert_called_once_with("job_stats:another-job-456")


class TestCachePerformance:
    """Test cache performance characteristics"""
    
    def test_cache_serialization_performance(self, sample_statistics):
        """Test that statistics can be efficiently serialized for caching"""
        # Test model_dump performance
        start_time = datetime.now()
        data = sample_statistics.model_dump(mode='json')
        serialization_time = (datetime.now() - start_time).total_seconds()
        
        # Should serialize quickly (less than 0.1 seconds)
        assert serialization_time < 0.1
        assert isinstance(data, dict)
        assert data["job_id"] == "test-job-123"
        
        # Test JSON serialization
        start_time = datetime.now()
        json_str = json.dumps(data)
        json_time = (datetime.now() - start_time).total_seconds()
        
        assert json_time < 0.1
        assert isinstance(json_str, str)
        assert len(json_str) > 0
    
    def test_cache_deserialization_performance(self, sample_statistics):
        """Test that cached statistics can be efficiently deserialized"""
        # Serialize data
        data = sample_statistics.model_dump(mode='json')
        json_str = json.dumps(data)
        
        # Test JSON deserialization
        start_time = datetime.now()
        parsed_data = json.loads(json_str)
        json_parse_time = (datetime.now() - start_time).total_seconds()
        
        assert json_parse_time < 0.1
        
        # Test Pydantic model creation
        start_time = datetime.now()
        reconstructed_stats = JobStatistics(**parsed_data)
        model_creation_time = (datetime.now() - start_time).total_seconds()
        
        assert model_creation_time < 0.1
        assert reconstructed_stats.job_id == sample_statistics.job_id
        assert reconstructed_stats.application_stats.total_applications == sample_statistics.application_stats.total_applications


class TestCacheErrorRecovery:
    """Test cache error recovery scenarios"""
    
    @patch('src.utils.route_helpers.get_controller')
    def test_service_continues_without_cache(self, mock_get_controller, service_without_redis):
        """Test that service continues to work without Redis cache"""
        # Mock job controller
        mock_job = Mock()
        mock_job.job_id = "test-job-123"
        mock_job.company_id = "test-company-123"
        mock_job.applications = []
        mock_job.ats_reports = []
        mock_job.posted_at = utc_time() - timedelta(days=7)
        mock_job.total_applications_count = 0
        
        mock_job_controller = AsyncMock()
        mock_job_controller.get_job_by_id.return_value = mock_job
        
        mock_company_controller = AsyncMock()
        mock_company_controller.get_company_by_id.return_value = None
        
        def mock_controller_factory(controller_name):
            if controller_name == 'jobs_search':
                return mock_job_controller
            elif controller_name == 'company':
                return mock_company_controller
            return None
        
        mock_get_controller.side_effect = mock_controller_factory
        
        result = asyncio.run(service_without_redis.get_job_statistics("test-job-123"))
        
        # Should still return valid statistics
        assert isinstance(result, JobStatistics)
        assert result.job_id == "test-job-123"
        
        # Verify controllers were called (no cache available)
        mock_job_controller.get_job_by_id.assert_called_once()
    
    def test_cache_corruption_recovery(self, service_with_redis):
        """Test recovery from corrupted cache data"""
        # Mock corrupted cache data
        service_with_redis.redis_client.get.return_value = "corrupted data that's not JSON"
        
        result = asyncio.run(service_with_redis._get_cached_statistics("test-job-123"))
        
        # Should return None and not crash
        assert result is None
        
        # Test with partial JSON data
        service_with_redis.redis_client.get.return_value = '{"job_id": "test", "incomplete": true'
        
        result = asyncio.run(service_with_redis._get_cached_statistics("test-job-123"))
        
        # Should return None and not crash
        assert result is None
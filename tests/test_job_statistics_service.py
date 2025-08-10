"""
Unit tests for JobStatisticsService

Tests the calculation, caching, and error handling of job statistics.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, date

from src.services.job_statistics_service import JobStatisticsService
from src.database.models.job_statistics import (
    JobStatistics, ApplicationStatistics, CompetitivenessMetrics,
    TrendAnalysis, TrendDataPoint, CompanyStatistics
)
from src.database.constants import utc_time


class MockJob:
    """Mock Job class for testing"""
    def __init__(self, job_id="test-job-123", title="Software Engineer", 
                 company_id="test-company-123", posted_at=None, applications=None, ats_reports=None):
        self.job_id = job_id
        self.title = title
        self.company_id = company_id
        self.posted_at = posted_at or utc_time() - timedelta(days=7)
        self.applications = applications or []
        self.ats_reports = ats_reports or []
        self.total_applications_count = len(self.applications)


class MockJobApplication:
    """Mock JobApplication class for testing"""
    def __init__(self, applied_date=None, method="website"):
        self.applied_date = applied_date or utc_time()
        self.method = method


class MockATSReport:
    """Mock ATS Report class for testing"""
    def __init__(self, score=None, matched_keywords=None, missing_keywords=None):
        self.score = score
        self.matched_keywords = matched_keywords or []
        self.missing_keywords = missing_keywords or []


class MockCompany:
    """Mock Company class for testing"""
    def __init__(self, company_id="test-company-123", jobs=None, created_at=None):
        self.company_id = company_id
        self.jobs = jobs or []
        self.created_at = created_at or utc_time() - timedelta(days=365)
        self.avg_applications_per_job = 5.0
        self.application_response_rate = 75.0
        self.active_jobs = 3


class TestJobStatisticsService:
    """Test cases for JobStatisticsService"""
    
    @pytest.fixture
    def service(self):
        """Create a JobStatisticsService instance for testing"""
        service = JobStatisticsService()
        service.redis_client = Mock()  # Mock Redis client
        return service
    
    @pytest.fixture
    def sample_job(self):
        """Create a sample job for testing"""
        applications = [
            MockJobApplication(utc_time() - timedelta(days=1), "website"),
            MockJobApplication(utc_time() - timedelta(days=2), "external"),
            MockJobApplication(utc_time() - timedelta(days=3), "website"),
        ]
        
        ats_reports = [
            MockATSReport(85, ["python", "django"], ["react"]),
            MockATSReport(65, ["python", "sql"], ["javascript", "react"]),
            MockATSReport(45, ["sql"], ["python", "django", "react"]),
        ]
        
        return MockJob(
            applications=applications,
            ats_reports=ats_reports
        )
    
    @pytest.fixture
    def sample_company(self):
        """Create a sample company for testing"""
        jobs = [
            MockJob(posted_at=utc_time() - timedelta(days=30)),
            MockJob(posted_at=utc_time() - timedelta(days=60)),
            MockJob(posted_at=utc_time() - timedelta(days=90)),
        ]
        return MockCompany(jobs=jobs)


class TestApplicationStatistics:
    """Test application statistics calculation"""
    
    def test_get_application_statistics_with_applications(self, service, sample_job):
        """Test calculating application statistics for job with applications"""
        result = asyncio.run(service.get_application_statistics(sample_job))
        
        assert isinstance(result, ApplicationStatistics)
        assert result.total_applications == 3
        assert result.applications_per_day > 0
        assert result.application_sources["website"] == 2
        assert result.application_sources["external"] == 1
        assert result.days_since_posted == 7
        assert result.recent_application_trend in ["increasing", "decreasing", "stable"]
    
    def test_get_application_statistics_no_applications(self, service):
        """Test calculating application statistics for job with no applications"""
        job = MockJob(applications=[])
        result = asyncio.run(service.get_application_statistics(job))
        
        assert isinstance(result, ApplicationStatistics)
        assert result.total_applications == 0
        assert result.applications_per_day == 0.0
        assert result.application_sources == {}
        assert result.recent_application_trend == "stable"
    
    def test_get_application_statistics_error_handling(self, service):
        """Test error handling in application statistics calculation"""
        # Create a job that will cause an error
        job = MockJob()
        job.posted_at = None  # This should cause an error
        
        result = asyncio.run(service.get_application_statistics(job))
        
        assert isinstance(result, ApplicationStatistics)
        assert result.total_applications == 0
        assert result.applications_per_day == 0.0


class TestCompetitivenessMetrics:
    """Test competitiveness metrics calculation"""
    
    def test_get_competitiveness_metrics_with_ats_data(self, service, sample_job):
        """Test calculating competitiveness metrics with ATS data"""
        result = asyncio.run(service.get_competitiveness_metrics(sample_job))
        
        assert isinstance(result, CompetitivenessMetrics)
        assert result.total_ats_reports == 3
        assert result.average_match_score == 65.0  # (85 + 65 + 45) / 3
        assert "python" in result.top_matched_keywords
        assert "react" in result.top_missing_keywords
        assert result.ats_readiness_percentage > 0
        assert "0-20" in result.match_score_distribution
    
    def test_get_competitiveness_metrics_no_ats_data(self, service):
        """Test calculating competitiveness metrics without ATS data"""
        job = MockJob(ats_reports=[])
        result = asyncio.run(service.get_competitiveness_metrics(job))
        
        assert isinstance(result, CompetitivenessMetrics)
        assert result.total_ats_reports == 0
        assert result.average_match_score is None
        assert result.top_matched_keywords == []
        assert result.top_missing_keywords == []
        assert result.ats_readiness_percentage == 0.0
    
    def test_score_distribution_calculation(self, service):
        """Test ATS score distribution calculation"""
        ats_reports = [
            MockATSReport(15),  # 0-20 range
            MockATSReport(35),  # 21-40 range
            MockATSReport(55),  # 41-60 range
            MockATSReport(75),  # 61-80 range
            MockATSReport(95),  # 81-100 range
        ]
        
        distribution = service._calculate_score_distribution(ats_reports)
        
        assert distribution["0-20"] == 1
        assert distribution["21-40"] == 1
        assert distribution["41-60"] == 1
        assert distribution["61-80"] == 1
        assert distribution["81-100"] == 1


class TestTrendAnalysis:
    """Test trend analysis calculation"""
    
    def test_get_trend_analysis_with_data(self, service, sample_job):
        """Test calculating trend analysis with application data"""
        result = asyncio.run(service.get_trend_analysis(sample_job))
        
        assert isinstance(result, TrendAnalysis)
        assert len(result.daily_applications) > 0
        assert result.application_velocity in ["accelerating", "decelerating", "steady"]
        assert result.trend_direction in ["increasing", "decreasing", "stable"]
        assert isinstance(result.peak_application_days, list)
    
    def test_get_trend_analysis_no_data(self, service):
        """Test calculating trend analysis without application data"""
        job = MockJob(applications=[])
        result = asyncio.run(service.get_trend_analysis(job))
        
        assert isinstance(result, TrendAnalysis)
        assert result.daily_applications == []
        assert result.application_velocity == "steady"
        assert result.trend_direction == "stable"
        assert result.peak_application_days == []
    
    def test_group_applications_by_date(self, service):
        """Test grouping applications by date"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        applications = [
            MockJobApplication(datetime.combine(today, datetime.min.time().replace(tzinfo=timezone.utc))),
            MockJobApplication(datetime.combine(today, datetime.min.time().replace(tzinfo=timezone.utc))),
            MockJobApplication(datetime.combine(yesterday, datetime.min.time().replace(tzinfo=timezone.utc))),
        ]
        
        result = service._group_applications_by_date(applications)
        
        assert result[today] == 2
        assert result[yesterday] == 1
    
    def test_find_peak_application_days(self, service):
        """Test finding peak application days"""
        # Create applications for different days of the week
        applications = []
        base_date = datetime(2025, 1, 6, tzinfo=timezone.utc)  # Monday
        
        # Add more applications on Monday and Wednesday
        for i in range(3):  # Monday
            applications.append(MockJobApplication(base_date + timedelta(hours=i)))
        for i in range(2):  # Wednesday
            applications.append(MockJobApplication(base_date + timedelta(days=2, hours=i)))
        for i in range(1):  # Friday
            applications.append(MockJobApplication(base_date + timedelta(days=4, hours=i)))
        
        result = service._find_peak_application_days(applications)
        
        assert "Monday" in result
        assert len(result) <= 2


class TestCompanyStatistics:
    """Test company statistics calculation"""
    
    @patch('src.utils.route_helpers.get_controller')
    def test_get_company_statistics_with_data(self, mock_get_controller, service, sample_company):
        """Test calculating company statistics with data"""
        # Mock the company controller
        mock_controller = AsyncMock()
        mock_controller.get_company_by_id.return_value = sample_company
        mock_get_controller.return_value = mock_controller
        
        result = asyncio.run(service.get_company_statistics("test-company-123"))
        
        assert isinstance(result, CompanyStatistics)
        assert result.total_jobs_12_months == 3
        assert result.average_applications_per_job == 5.0
        assert result.application_response_rate == 75.0
        assert result.total_active_jobs == 3
        assert result.hiring_activity_level in ["high", "medium", "low"]
    
    @patch('src.utils.route_helpers.get_controller')
    def test_get_company_statistics_company_not_found(self, mock_get_controller, service):
        """Test company statistics when company not found"""
        mock_controller = AsyncMock()
        mock_controller.get_company_by_id.return_value = None
        mock_get_controller.return_value = mock_controller
        
        result = asyncio.run(service.get_company_statistics("nonexistent-company"))
        
        assert isinstance(result, CompanyStatistics)
        assert result.total_jobs_12_months == 0
        assert result.average_applications_per_job == 0.0
        assert result.application_response_rate == 0.0
        assert result.total_active_jobs == 0
    
    def test_count_jobs_last_12_months(self, service):
        """Test counting jobs posted in last 12 months"""
        jobs = [
            MockJob(posted_at=utc_time() - timedelta(days=30)),   # Within 12 months
            MockJob(posted_at=utc_time() - timedelta(days=180)),  # Within 12 months
            MockJob(posted_at=utc_time() - timedelta(days=400)),  # Outside 12 months
        ]
        
        result = service._count_jobs_last_12_months(jobs)
        assert result == 2
    
    def test_determine_hiring_activity_level(self, service):
        """Test determining hiring activity level"""
        assert service._determine_hiring_activity_level(25, 15) == "high"
        assert service._determine_hiring_activity_level(10, 5) == "medium"
        assert service._determine_hiring_activity_level(2, 1) == "low"


class TestCaching:
    """Test caching functionality"""
    
    def test_cache_statistics(self, service):
        """Test caching statistics"""
        statistics = JobStatistics(
            job_id="test-job-123",
            application_stats=ApplicationStatistics(
                total_applications=5,
                applications_per_day=1.0,
                application_sources={"website": 5},
                recent_application_trend="stable",
                days_since_posted=5
            ),
            competitiveness=CompetitivenessMetrics(),
            trends=TrendAnalysis(),
            company_stats=CompanyStatistics(),
            calculated_at=utc_time()
        )
        
        # Mock Redis client
        service.redis_client.setex = AsyncMock()
        
        asyncio.run(service._cache_statistics("test-job-123", statistics))
        
        service.redis_client.setex.assert_called_once()
        call_args = service.redis_client.setex.call_args
        assert call_args[0][0] == "job_stats:test-job-123"  # cache key
        assert call_args[0][1] == statistics.cache_ttl_seconds  # TTL
    
    def test_get_cached_statistics(self, service):
        """Test retrieving cached statistics"""
        # Mock cached data
        cached_data = {
            "job_id": "test-job-123",
            "application_stats": {
                "total_applications": 5,
                "applications_per_day": 1.0,
                "application_sources": {"website": 5},
                "recent_application_trend": "stable",
                "days_since_posted": 5
            },
            "competitiveness": {
                "match_score_distribution": {},
                "average_match_score": None,
                "top_matched_keywords": [],
                "top_missing_keywords": [],
                "ats_readiness_percentage": 0.0,
                "total_ats_reports": 0
            },
            "trends": {
                "daily_applications": [],
                "application_velocity": "steady",
                "industry_comparison": {},
                "peak_application_days": [],
                "trend_direction": "stable"
            },
            "company_stats": {
                "total_jobs_12_months": 0,
                "average_applications_per_job": 0.0,
                "application_response_rate": 0.0,
                "total_active_jobs": 0
            },
            "calculated_at": utc_time().isoformat(),
            "cache_ttl_seconds": 3600
        }
        
        service.redis_client.get = AsyncMock(return_value=json.dumps(cached_data))
        
        result = asyncio.run(service._get_cached_statistics("test-job-123"))
        
        assert isinstance(result, JobStatistics)
        assert result.job_id == "test-job-123"
    
    def test_get_cached_statistics_no_cache(self, service):
        """Test retrieving cached statistics when no cache exists"""
        service.redis_client.get = AsyncMock(return_value=None)
        
        result = asyncio.run(service._get_cached_statistics("test-job-123"))
        
        assert result is None
    
    def test_invalidate_job_statistics_cache(self, service):
        """Test invalidating cached statistics"""
        service.redis_client.delete = AsyncMock()
        
        asyncio.run(service.invalidate_job_statistics_cache("test-job-123"))
        
        service.redis_client.delete.assert_called_once_with("job_stats:test-job-123")


class TestErrorHandling:
    """Test error handling and fallback mechanisms"""
    
    @patch('src.utils.route_helpers.get_controller')
    def test_get_job_statistics_job_not_found(self, mock_get_controller, service):
        """Test handling when job is not found"""
        mock_controller = AsyncMock()
        mock_controller.get_job_by_id.return_value = None
        mock_get_controller.return_value = mock_controller
        
        result = asyncio.run(service.get_job_statistics("nonexistent-job"))
        
        assert result is None
    
    def test_get_job_statistics_invalid_job_id(self, service):
        """Test handling invalid job ID"""
        result = asyncio.run(service.get_job_statistics(""))
        assert result is None
        
        result = asyncio.run(service.get_job_statistics(None))
        assert result is None
    
    @patch('src.utils.route_helpers.get_controller')
    def test_get_job_statistics_timeout_handling(self, mock_get_controller, service):
        """Test timeout handling in job statistics calculation"""
        mock_controller = AsyncMock()
        mock_controller.get_job_by_id.side_effect = asyncio.TimeoutError()
        mock_get_controller.return_value = mock_controller
        
        result = asyncio.run(service.get_job_statistics("test-job-123"))
        
        # Should return minimal fallback statistics
        assert isinstance(result, JobStatistics)
        assert result.job_id == "test-job-123"
    
    def test_fallback_application_stats(self, service):
        """Test fallback application statistics"""
        job = MockJob(applications=[MockJobApplication(), MockJobApplication()])
        
        result = service._get_fallback_application_stats(job)
        
        assert isinstance(result, ApplicationStatistics)
        assert result.total_applications == 2
        assert result.applications_per_day > 0
    
    def test_fallback_methods(self, service):
        """Test all fallback methods return appropriate objects"""
        assert isinstance(service._get_fallback_competitiveness_metrics(), CompetitivenessMetrics)
        assert isinstance(service._get_fallback_trend_analysis(), TrendAnalysis)
        assert isinstance(service._get_fallback_company_stats(), CompanyStatistics)
        
        minimal_stats = service._get_minimal_fallback_statistics("test-job-123")
        assert isinstance(minimal_stats, JobStatistics)
        assert minimal_stats.job_id == "test-job-123"


class TestHelperMethods:
    """Test helper methods"""
    
    def test_analyze_application_sources(self, service):
        """Test application source analysis"""
        applications = [
            MockJobApplication(method="website"),
            MockJobApplication(method="website"),
            MockJobApplication(method="external"),
            MockJobApplication(method=None),  # Should default to website
        ]
        
        result = service._analyze_application_sources(applications)
        
        assert result["website"] == 3  # 2 explicit + 1 default
        assert result["external"] == 1
    
    def test_calculate_recent_application_trend(self, service):
        """Test recent application trend calculation"""
        now = utc_time()
        
        # Create applications with increasing trend
        applications = [
            MockJobApplication(now - timedelta(days=1)),  # Recent
            MockJobApplication(now - timedelta(days=2)),  # Recent
            MockJobApplication(now - timedelta(days=10)), # Previous period
        ]
        
        result = asyncio.run(service._calculate_recent_application_trend(applications))
        
        assert result in ["increasing", "decreasing", "stable"]
    
    def test_get_top_keywords(self, service):
        """Test getting top keywords from lists"""
        keyword_lists = [
            ["python", "django", "sql"],
            ["python", "react", "javascript"],
            ["python", "sql", "mongodb"]
        ]
        
        result = service._get_top_keywords(keyword_lists, top_n=3)
        
        assert "python" in result  # Should be most common
        assert len(result) <= 3
    
    def test_calculate_velocity_and_direction(self, service):
        """Test velocity and direction calculation"""
        # Create trend data with increasing pattern
        trend_points = [
            TrendDataPoint(date=date.today() - timedelta(days=6), count=1),
            TrendDataPoint(date=date.today() - timedelta(days=5), count=2),
            TrendDataPoint(date=date.today() - timedelta(days=4), count=3),
            TrendDataPoint(date=date.today() - timedelta(days=3), count=4),
            TrendDataPoint(date=date.today() - timedelta(days=2), count=5),
            TrendDataPoint(date=date.today() - timedelta(days=1), count=6),
            TrendDataPoint(date=date.today(), count=7),
        ]
        
        velocity, direction = service._calculate_velocity_and_direction(trend_points)
        
        assert velocity in ["accelerating", "decelerating", "steady"]
        assert direction in ["increasing", "decreasing", "stable"]


class TestIntegration:
    """Integration tests for the complete statistics service"""
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.utils.route_helpers.get_service')
    def test_full_statistics_calculation(self, mock_get_service, mock_get_controller, service, sample_job, sample_company):
        """Test complete statistics calculation flow"""
        # Mock controllers
        job_controller = AsyncMock()
        job_controller.get_job_by_id.return_value = sample_job
        
        company_controller = AsyncMock()
        company_controller.get_company_by_id.return_value = sample_company
        
        def mock_controller_factory(controller_name):
            if controller_name == 'jobs_search':
                return job_controller
            elif controller_name == 'company':
                return company_controller
            return None
        
        mock_get_controller.side_effect = mock_controller_factory
        
        # Mock cache service
        mock_cache_service = Mock()
        mock_cache_service.redis_client = Mock()
        mock_get_service.return_value = mock_cache_service
        
        # Mock Redis operations
        service.redis_client = Mock()
        service.redis_client.get = AsyncMock(return_value=None)  # No cache
        service.redis_client.setex = AsyncMock()
        
        result = asyncio.run(service.get_job_statistics("test-job-123"))
        
        assert isinstance(result, JobStatistics)
        assert result.job_id == "test-job-123"
        assert isinstance(result.application_stats, ApplicationStatistics)
        assert isinstance(result.competitiveness, CompetitivenessMetrics)
        assert isinstance(result.trends, TrendAnalysis)
        assert isinstance(result.company_stats, CompanyStatistics)
        
        # Verify caching was attempted
        service.redis_client.setex.assert_called_once()
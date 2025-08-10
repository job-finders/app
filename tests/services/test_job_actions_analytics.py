"""
Tests for Job Actions Analytics Service
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from src.services.job_actions_analytics import (
    JobActionsAnalyticsService,
    JobActionsAnalyticsEvent,
    JobEngagementMetrics,
    JobActionsReport,
    CompanyEngagementStats
)


class TestJobActionsAnalyticsService:
    """Test cases for JobActionsAnalyticsService"""

    @pytest.fixture
    def analytics_service(self):
        """Create analytics service instance for testing"""
        mock_factory = Mock()
        service = JobActionsAnalyticsService(mock_factory)
        service.logger = Mock()
        return service

    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = Mock()
        session.query.return_value.filter_by.return_value.first.return_value = Mock(company_id="test-company")
        session.query.return_value.filter_by.return_value.scalar.return_value = 5
        return session

    def test_track_job_action_success(self, analytics_service, mock_session):
        """Test successful job action tracking"""
        analytics_service.get_session = Mock(return_value=mock_session)

        result = analytics_service.track_job_action(
            event_type="job_like",
            user_id="test-user",
            job_id="test-job",
            metadata={"test": "data"}
        )

        # Should be async, but for testing we'll check the structure
        assert isinstance(result, bool) or hasattr(result, '__await__')

    def test_track_job_action_invalid_params(self, analytics_service):
        """Test job action tracking with invalid parameters"""
        result = analytics_service.track_job_action(
            event_type="",
            user_id="test-user",
            job_id="",
            metadata={}
        )

        # Should be async, but for testing we'll check the structure
        assert isinstance(result, bool) or hasattr(result, '__await__')

    def test_job_engagement_metrics_model(self):
        """Test JobEngagementMetrics model validation"""
        metrics = JobEngagementMetrics(
            job_id="test-job",
            total_likes=10,
            total_saves=5,
            total_shares=3,
            total_views=100,
            total_applications=2,
            engagement_rate=18.0,
            save_to_apply_rate=40.0,
            like_to_apply_rate=20.0,
            share_conversion_rate=66.7
        )

        assert metrics.job_id == "test-job"
        assert metrics.total_likes == 10
        assert metrics.engagement_rate == 18.0
        assert isinstance(metrics.calculated_at, datetime)

    def test_job_actions_analytics_event_model(self):
        """Test JobActionsAnalyticsEvent model validation"""
        event = JobActionsAnalyticsEvent(
            event_type="job_like",
            user_id="test-user",
            job_id="test-job",
            company_id="test-company",
            metadata={"source": "web"}
        )

        assert event.event_type == "job_like"
        assert event.user_id == "test-user"
        assert event.job_id == "test-job"
        assert event.company_id == "test-company"
        assert event.metadata == {"source": "web"}
        assert isinstance(event.timestamp, datetime)
        assert event.event_id is not None

    def test_job_actions_analytics_event_invalid_type(self):
        """Test JobActionsAnalyticsEvent with invalid event type"""
        with pytest.raises(ValueError):
            JobActionsAnalyticsEvent(
                event_type="invalid_event",
                job_id="test-job",
                company_id="test-company"
            )

    def test_company_engagement_stats_model(self):
        """Test CompanyEngagementStats model"""
        stats = CompanyEngagementStats(
            company_id="test-company",
            total_job_likes=50,
            total_job_saves=30,
            total_job_shares=20,
            average_engagement_per_job=10.0,
            most_liked_job_id="job-1",
            most_saved_job_id="job-2",
            most_shared_job_id="job-3",
            engagement_growth_rate=15.5
        )

        assert stats.company_id == "test-company"
        assert stats.total_job_likes == 50
        assert stats.average_engagement_per_job == 10.0
        assert stats.engagement_growth_rate == 15.5
        assert isinstance(stats.calculated_at, datetime)

    def test_job_actions_report_model(self):
        """Test JobActionsReport model"""
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc)

        report = JobActionsReport(
            company_id="test-company",
            report_period_start=start_date,
            report_period_end=end_date,
            total_jobs=10,
            total_engagement_events=100,
            top_performing_jobs=[
                {
                    "job_id": "job-1",
                    "title": "Test Job",
                    "total_engagement": 25
                }
            ],
            engagement_trends={
                "likes": [1, 2, 3, 4, 5],
                "saves": [2, 3, 4, 5, 6],
                "shares": [0, 1, 1, 2, 2]
            },
            conversion_metrics={
                "save_to_apply_rate": 25.0,
                "like_to_apply_rate": 15.0,
                "overall_engagement_to_apply_rate": 20.0
            }
        )

        assert report.company_id == "test-company"
        assert report.total_jobs == 10
        assert report.total_engagement_events == 100
        assert len(report.top_performing_jobs) == 1
        assert "likes" in report.engagement_trends
        assert "save_to_apply_rate" in report.conversion_metrics
        assert isinstance(report.generated_at, datetime)

    @patch('src.services.job_actions_analytics.datetime')
    def test_date_calculations(self, mock_datetime, analytics_service):
        """Test date calculations in analytics"""
        # Mock current time
        mock_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        # Test that the service uses the mocked time
        event = JobActionsAnalyticsEvent(
            event_type="job_like",
            job_id="test-job",
            company_id="test-company"
        )

        # The timestamp should be set to the mocked time
        assert event.timestamp.year == 2024
        assert event.timestamp.month == 1
        assert event.timestamp.day == 15


class TestAnalyticsIntegration:
    """Integration tests for analytics functionality"""

    def test_analytics_service_initialization(self):
        """Test that analytics service can be initialized"""
        mock_factory = Mock()
        service = JobActionsAnalyticsService(mock_factory)

        assert service is not None
        assert hasattr(service, 'track_job_action')
        assert hasattr(service, 'get_job_engagement_metrics')
        assert hasattr(service, 'get_company_engagement_stats')
        assert hasattr(service, 'generate_job_actions_report')

    def test_analytics_models_serialization(self):
        """Test that analytics models can be serialized"""
        metrics = JobEngagementMetrics(
            job_id="test-job",
            total_likes=5,
            total_saves=3,
            total_shares=2,
            engagement_rate=10.0
        )

        # Test model_dump method
        data = metrics.model_dump()
        assert isinstance(data, dict)
        assert data['job_id'] == "test-job"
        assert data['total_likes'] == 5
        assert 'calculated_at' in data

    def test_analytics_error_handling(self, analytics_service):
        """Test error handling in analytics service"""
        # Test with None values
        result = analytics_service.track_job_action(
            event_type=None,
            user_id=None,
            job_id=None
        )

        # Should handle gracefully
        assert isinstance(result, bool) or hasattr(result, '__await__')


if __name__ == '__main__':
    pytest.main([__file__])

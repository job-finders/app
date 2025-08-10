"""
Unit tests for Job Statistics Models

Tests the Pydantic models used for job statistics including computed properties,
validation, and data transformations.
"""

import pytest
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List

from src.database.models.job_statistics import (
    ApplicationStatistics, CompetitivenessMetrics, TrendAnalysis, 
    TrendDataPoint, CompanyStatistics, JobStatistics, StatisticsError
)
from src.database.constants import utc_time


class TestApplicationStatistics:
    """Test ApplicationStatistics model"""
    
    def test_application_statistics_creation(self):
        """Test creating ApplicationStatistics with valid data"""
        stats = ApplicationStatistics(
            total_applications=10,
            applications_per_day=2.5,
            application_sources={"website": 7, "external": 3},
            recent_application_trend="increasing",
            days_since_posted=4
        )
        
        assert stats.total_applications == 10
        assert stats.applications_per_day == 2.5
        assert stats.application_sources["website"] == 7
        assert stats.recent_application_trend == "increasing"
        assert stats.days_since_posted == 4
    
    def test_application_statistics_defaults(self):
        """Test ApplicationStatistics with default values"""
        stats = ApplicationStatistics(
            total_applications=0,
            applications_per_day=0.0,
            days_since_posted=1
        )
        
        assert stats.application_sources == {}
        assert stats.recent_application_trend == "stable"
    
    def test_has_applications_computed_field(self):
        """Test has_applications computed property"""
        stats_with_apps = ApplicationStatistics(
            total_applications=5,
            applications_per_day=1.0,
            days_since_posted=5
        )
        
        stats_no_apps = ApplicationStatistics(
            total_applications=0,
            applications_per_day=0.0,
            days_since_posted=1
        )
        
        assert stats_with_apps.has_applications is True
        assert stats_no_apps.has_applications is False
    
    def test_application_rate_category_computed_field(self):
        """Test application_rate_category computed property"""
        high_rate = ApplicationStatistics(
            total_applications=25,
            applications_per_day=5.0,
            days_since_posted=5
        )
        
        medium_rate = ApplicationStatistics(
            total_applications=10,
            applications_per_day=3.0,
            days_since_posted=3
        )
        
        low_rate = ApplicationStatistics(
            total_applications=2,
            applications_per_day=1.0,
            days_since_posted=2
        )
        
        assert high_rate.application_rate_category == "high"
        assert medium_rate.application_rate_category == "medium"
        assert low_rate.application_rate_category == "low"
    
    def test_application_statistics_validation(self):
        """Test validation of ApplicationStatistics fields"""
        # Test negative values are rejected
        with pytest.raises(ValueError):
            ApplicationStatistics(
                total_applications=-1,
                applications_per_day=1.0,
                days_since_posted=1
            )
        
        with pytest.raises(ValueError):
            ApplicationStatistics(
                total_applications=1,
                applications_per_day=-1.0,
                days_since_posted=1
            )


class TestCompetitivenessMetrics:
    """Test CompetitivenessMetrics model"""
    
    def test_competitiveness_metrics_creation(self):
        """Test creating CompetitivenessMetrics with valid data"""
        metrics = CompetitivenessMetrics(
            match_score_distribution={"0-20": 1, "21-40": 2, "41-60": 3, "61-80": 2, "81-100": 2},
            average_match_score=65.5,
            top_matched_keywords=["python", "django", "sql"],
            top_missing_keywords=["react", "javascript"],
            ats_readiness_percentage=40.0,
            total_ats_reports=10
        )
        
        assert metrics.average_match_score == 65.5
        assert len(metrics.top_matched_keywords) == 3
        assert metrics.ats_readiness_percentage == 40.0
        assert metrics.total_ats_reports == 10
    
    def test_competitiveness_metrics_defaults(self):
        """Test CompetitivenessMetrics with default values"""
        metrics = CompetitivenessMetrics()
        
        assert metrics.match_score_distribution == {}
        assert metrics.average_match_score is None
        assert metrics.top_matched_keywords == []
        assert metrics.top_missing_keywords == []
        assert metrics.ats_readiness_percentage == 0.0
        assert metrics.total_ats_reports == 0
    
    def test_has_ats_data_computed_field(self):
        """Test has_ats_data computed property"""
        with_data = CompetitivenessMetrics(total_ats_reports=5)
        without_data = CompetitivenessMetrics(total_ats_reports=0)
        
        assert with_data.has_ats_data is True
        assert without_data.has_ats_data is False
    
    def test_competitiveness_level_computed_field(self):
        """Test competitiveness_level computed property"""
        high_comp = CompetitivenessMetrics(
            average_match_score=80.0,
            total_ats_reports=10
        )
        
        medium_comp = CompetitivenessMetrics(
            average_match_score=60.0,
            total_ats_reports=10
        )
        
        low_comp = CompetitivenessMetrics(
            average_match_score=40.0,
            total_ats_reports=10
        )
        
        no_data = CompetitivenessMetrics(total_ats_reports=0)
        
        assert high_comp.competitiveness_level == "high"
        assert medium_comp.competitiveness_level == "medium"
        assert low_comp.competitiveness_level == "low"
        assert no_data.competitiveness_level == "unknown"


class TestTrendAnalysis:
    """Test TrendAnalysis model"""
    
    def test_trend_data_point_creation(self):
        """Test creating TrendDataPoint"""
        point = TrendDataPoint(
            date=date(2025, 1, 15),
            count=5
        )
        
        assert point.date == date(2025, 1, 15)
        assert point.count == 5
    
    def test_trend_analysis_creation(self):
        """Test creating TrendAnalysis with valid data"""
        daily_apps = [
            TrendDataPoint(date=date(2025, 1, 10), count=2),
            TrendDataPoint(date=date(2025, 1, 11), count=3),
            TrendDataPoint(date=date(2025, 1, 12), count=5),
        ]
        
        trends = TrendAnalysis(
            daily_applications=daily_apps,
            application_velocity="accelerating",
            industry_comparison={"this_job": 3.3, "industry_average": 2.5},
            peak_application_days=["Monday", "Wednesday"],
            trend_direction="increasing"
        )
        
        assert len(trends.daily_applications) == 3
        assert trends.application_velocity == "accelerating"
        assert trends.industry_comparison["this_job"] == 3.3
        assert "Monday" in trends.peak_application_days
        assert trends.trend_direction == "increasing"
    
    def test_has_trend_data_computed_field(self):
        """Test has_trend_data computed property"""
        with_data = TrendAnalysis(
            daily_applications=[
                TrendDataPoint(date=date(2025, 1, 10), count=2),
                TrendDataPoint(date=date(2025, 1, 11), count=3),
                TrendDataPoint(date=date(2025, 1, 12), count=5),
            ]
        )
        
        insufficient_data = TrendAnalysis(
            daily_applications=[
                TrendDataPoint(date=date(2025, 1, 10), count=2),
            ]
        )
        
        no_data = TrendAnalysis()
        
        assert with_data.has_trend_data is True
        assert insufficient_data.has_trend_data is False
        assert no_data.has_trend_data is False


class TestCompanyStatistics:
    """Test CompanyStatistics model"""
    
    def test_company_statistics_creation(self):
        """Test creating CompanyStatistics with valid data"""
        stats = CompanyStatistics(
            total_jobs_12_months=15,
            average_applications_per_job=8.5,
            average_time_to_fill=25.0,
            application_response_rate=75.0,
            hiring_activity_level="high",
            total_active_jobs=5,
            company_age_days=730
        )
        
        assert stats.total_jobs_12_months == 15
        assert stats.average_applications_per_job == 8.5
        assert stats.average_time_to_fill == 25.0
        assert stats.application_response_rate == 75.0
        assert stats.hiring_activity_level == "high"
        assert stats.total_active_jobs == 5
        assert stats.company_age_days == 730
    
    def test_is_active_hirer_computed_field(self):
        """Test is_active_hirer computed property"""
        active_by_jobs = CompanyStatistics(total_jobs_12_months=10)
        active_by_current = CompanyStatistics(total_active_jobs=3)
        inactive = CompanyStatistics(total_jobs_12_months=2, total_active_jobs=1)
        
        assert active_by_jobs.is_active_hirer is True
        assert active_by_current.is_active_hirer is True
        assert inactive.is_active_hirer is False


class TestJobStatistics:
    """Test JobStatistics model"""
    
    def test_job_statistics_creation(self):
        """Test creating JobStatistics with all components"""
        app_stats = ApplicationStatistics(
            total_applications=10,
            applications_per_day=2.0,
            days_since_posted=5
        )
        
        comp_metrics = CompetitivenessMetrics(
            average_match_score=70.0,
            total_ats_reports=8
        )
        
        trends = TrendAnalysis(
            daily_applications=[
                TrendDataPoint(date=date(2025, 1, 10), count=2),
                TrendDataPoint(date=date(2025, 1, 11), count=3),
            ]
        )
        
        company_stats = CompanyStatistics(
            total_jobs_12_months=12,
            application_response_rate=65.0
        )
        
        job_stats = JobStatistics(
            job_id="test-job-123",
            application_stats=app_stats,
            competitiveness=comp_metrics,
            trends=trends,
            company_stats=company_stats
        )
        
        assert job_stats.job_id == "test-job-123"
        assert isinstance(job_stats.application_stats, ApplicationStatistics)
        assert isinstance(job_stats.competitiveness, CompetitivenessMetrics)
        assert isinstance(job_stats.trends, TrendAnalysis)
        assert isinstance(job_stats.company_stats, CompanyStatistics)
        assert job_stats.cache_ttl_seconds == 3600  # Default
    
    def test_is_data_fresh_computed_field(self):
        """Test is_data_fresh computed property"""
        fresh_stats = JobStatistics(
            job_id="test-job-123",
            application_stats=ApplicationStatistics(),
            competitiveness=CompetitivenessMetrics(),
            trends=TrendAnalysis(),
            company_stats=CompanyStatistics(),
            calculated_at=utc_time()  # Just calculated
        )
        
        old_stats = JobStatistics(
            job_id="test-job-123",
            application_stats=ApplicationStatistics(),
            competitiveness=CompetitivenessMetrics(),
            trends=TrendAnalysis(),
            company_stats=CompanyStatistics(),
            calculated_at=utc_time() - timedelta(hours=2)  # 2 hours ago
        )
        
        assert fresh_stats.is_data_fresh is True
        assert old_stats.is_data_fresh is False
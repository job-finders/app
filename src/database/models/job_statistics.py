"""
Job Statistics Data Models

This module contains Pydantic models for job-related statistics including
application metrics, competitiveness analysis, trend data, and company statistics.
"""

from typing import Optional, List, Dict, Any
from datetime import date
from pydantic import BaseModel, Field, ConfigDict, computed_field
from src.database.constants import utc_time, AwareDatetime


class ApplicationStatistics(BaseModel):
    """Statistics related to job applications"""
    
    total_applications: int = Field(ge=0, description="Total number of applications received")
    applications_per_day: float = Field(ge=0.0, description="Average applications per day since posting")
    application_sources: Dict[str, int] = Field(
        default_factory=dict, 
        description="Breakdown of application sources (website, external, etc.)"
    )
    recent_application_trend: str = Field(
        default="stable", 
        description="Recent trend direction: increasing, decreasing, stable"
    )
    days_since_posted: int = Field(ge=0, description="Number of days since job was posted")
    
    @computed_field
    @property
    def has_applications(self) -> bool:
        """Check if job has received any applications"""
        return self.total_applications > 0
    
    @computed_field
    @property
    def application_rate_category(self) -> str:
        """Categorize application rate as low, medium, or high"""
        if self.applications_per_day >= 5.0:
            return "high"
        elif self.applications_per_day >= 2.0:
            return "medium"
        else:
            return "low"
    
    model_config = ConfigDict(from_attributes=True)


class CompetitivenessMetrics(BaseModel):
    """Metrics related to job competitiveness and ATS analysis"""
    
    match_score_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of match scores in ranges: 0-20, 21-40, 41-60, 61-80, 81-100"
    )
    average_match_score: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=100.0,
        description="Average ATS match score across all applications"
    )
    top_matched_keywords: List[str] = Field(
        default_factory=list,
        description="Top 5 most commonly matched keywords"
    )
    top_missing_keywords: List[str] = Field(
        default_factory=list,
        description="Top 5 most commonly missing keywords"
    )
    ats_readiness_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Percentage of applications with good ATS scores (>=75)"
    )
    total_ats_reports: int = Field(ge=0, description="Total number of ATS reports available")
    
    @computed_field
    @property
    def has_ats_data(self) -> bool:
        """Check if ATS analysis data is available"""
        return self.total_ats_reports > 0
    
    @computed_field
    @property
    def competitiveness_level(self) -> str:
        """Determine competitiveness level based on average match score"""
        if not self.has_ats_data or self.average_match_score is None:
            return "unknown"
        
        if self.average_match_score >= 75:
            return "high"  # High average score means high competition
        elif self.average_match_score >= 50:
            return "medium"
        else:
            return "low"
    
    @computed_field
    @property
    def match_quality_indicator(self) -> str:
        """Indicate overall match quality of applicants"""
        if not self.has_ats_data:
            return "No data available"
        
        if self.ats_readiness_percentage >= 60:
            return "High quality applicants"
        elif self.ats_readiness_percentage >= 30:
            return "Mixed quality applicants"
        else:
            return "Lower quality applicants"
    
    model_config = ConfigDict(from_attributes=True)


class TrendDataPoint(BaseModel):
    """Single data point for trend analysis"""
    
    date: date = Field(description="Date of the data point")
    count: int = Field(ge=0, description="Number of applications on this date")
    
    model_config = ConfigDict(from_attributes=True)


class TrendAnalysis(BaseModel):
    """Analysis of application trends over time"""
    
    daily_applications: List[TrendDataPoint] = Field(
        default_factory=list,
        description="Daily application counts over time"
    )
    application_velocity: str = Field(
        default="steady",
        description="Application trend: accelerating, decelerating, steady"
    )
    industry_comparison: Dict[str, float] = Field(
        default_factory=dict,
        description="Comparison with industry averages"
    )
    peak_application_days: List[str] = Field(
        default_factory=list,
        description="Days of the week with highest application rates"
    )
    trend_direction: str = Field(
        default="stable",
        description="Overall trend direction: increasing, decreasing, stable"
    )
    
    @computed_field
    @property
    def has_trend_data(self) -> bool:
        """Check if sufficient trend data is available"""
        return len(self.daily_applications) >= 3
    
    @computed_field
    @property
    def total_days_tracked(self) -> int:
        """Total number of days with application data"""
        return len(self.daily_applications)
    
    @computed_field
    @property
    def trend_summary(self) -> str:
        """Human-readable trend summary"""
        if not self.has_trend_data:
            return "Insufficient data for trend analysis"
        
        total_apps = sum(point.count for point in self.daily_applications)
        avg_per_day = total_apps / len(self.daily_applications)
        
        return f"Averaging {avg_per_day:.1f} applications per day, trend is {self.trend_direction}"
    
    model_config = ConfigDict(from_attributes=True)


class CompanyStatistics(BaseModel):
    """Statistics related to the hiring company"""
    
    total_jobs_12_months: int = Field(ge=0, description="Total jobs posted in last 12 months")
    average_applications_per_job: float = Field(
        ge=0.0, 
        description="Average applications per job for this company"
    )
    average_time_to_fill: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Average days to fill positions (if available)"
    )
    application_response_rate: float = Field(
        ge=0.0,
        le=100.0,
        description="Percentage of applications that receive employer response"
    )
    hiring_activity_level: str = Field(
        default="medium",
        description="Company hiring activity: high, medium, low"
    )
    total_active_jobs: int = Field(ge=0, description="Currently active job postings")
    company_age_days: Optional[int] = Field(default=None, description="Days since company registration")
    
    @computed_field
    @property
    def is_active_hirer(self) -> bool:
        """Check if company is actively hiring"""
        return self.total_jobs_12_months >= 5 or self.total_active_jobs >= 2
    
    @computed_field
    @property
    def response_rate_category(self) -> str:
        """Categorize response rate"""
        if self.application_response_rate >= 70:
            return "excellent"
        elif self.application_response_rate >= 50:
            return "good"
        elif self.application_response_rate >= 30:
            return "fair"
        else:
            return "poor"
    
    @computed_field
    @property
    def hiring_frequency_description(self) -> str:
        """Describe hiring frequency"""
        if self.total_jobs_12_months >= 20:
            return "Very active hirer"
        elif self.total_jobs_12_months >= 10:
            return "Regular hirer"
        elif self.total_jobs_12_months >= 3:
            return "Occasional hirer"
        else:
            return "Infrequent hirer"
    
    model_config = ConfigDict(from_attributes=True)


class JobStatistics(BaseModel):
    """Comprehensive job statistics container"""
    
    job_id: str = Field(description="Job ID these statistics relate to")
    application_stats: ApplicationStatistics = Field(description="Application-related statistics")
    competitiveness: CompetitivenessMetrics = Field(description="Job competitiveness metrics")
    trends: TrendAnalysis = Field(description="Application trend analysis")
    company_stats: CompanyStatistics = Field(description="Company hiring statistics")
    calculated_at: AwareDatetime = Field(
        default_factory=utc_time,
        description="When these statistics were calculated"
    )
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")
    
    @computed_field
    @property
    def is_data_fresh(self) -> bool:
        """Check if statistics data is fresh (less than 1 hour old)"""
        from datetime import timedelta
        return (utc_time() - self.calculated_at) < timedelta(hours=1)
    
    @computed_field
    @property
    def overall_attractiveness_score(self) -> float:
        """Calculate overall job attractiveness score (0-100)"""
        score = 0.0
        factors = 0
        
        # Application rate factor (0-25 points)
        if self.application_stats.application_rate_category == "high":
            score += 25
        elif self.application_stats.application_rate_category == "medium":
            score += 15
        else:
            score += 5
        factors += 1
        
        # Company response rate factor (0-25 points)
        score += (self.company_stats.application_response_rate / 100) * 25
        factors += 1
        
        # Company activity factor (0-25 points)
        if self.company_stats.is_active_hirer:
            score += 20
        else:
            score += 10
        factors += 1
        
        # ATS readiness factor (0-25 points)
        if self.competitiveness.has_ats_data:
            score += (self.competitiveness.ats_readiness_percentage / 100) * 25
        else:
            score += 12.5  # Neutral score when no data
        factors += 1
        
        return min(score, 100.0)
    
    @computed_field
    @property
    def summary_insights(self) -> List[str]:
        """Generate key insights about this job"""
        insights = []
        
        # Application insights
        if self.application_stats.total_applications == 0:
            insights.append("Be the first to apply for this position")
        elif self.application_stats.application_rate_category == "high":
            insights.append("High competition - many applicants")
        elif self.application_stats.application_rate_category == "low":
            insights.append("Lower competition - good opportunity")
        
        # Company insights
        if self.company_stats.response_rate_category == "excellent":
            insights.append("Company has excellent response rate to applicants")
        elif self.company_stats.response_rate_category == "poor":
            insights.append("Company response rate is below average")
        
        # Trend insights
        if self.trends.trend_direction == "increasing":
            insights.append("Application interest is growing")
        elif self.trends.trend_direction == "decreasing":
            insights.append("Application interest is declining")
        
        # ATS insights
        if self.competitiveness.has_ats_data and self.competitiveness.average_match_score:
            if self.competitiveness.average_match_score >= 75:
                insights.append("High-quality applicants are applying")
            elif self.competitiveness.average_match_score < 50:
                insights.append("Opportunity for well-matched candidates")
        
        return insights[:4]  # Return top 4 insights
    
    model_config = ConfigDict(from_attributes=True)


class StatisticsError(BaseModel):
    """Error information when statistics calculation fails"""
    
    error_type: str = Field(description="Type of error encountered")
    error_message: str = Field(description="Human-readable error message")
    fallback_available: bool = Field(default=False, description="Whether fallback data is available")
    retry_after_seconds: Optional[int] = Field(default=None, description="Suggested retry delay")
    
    model_config = ConfigDict(from_attributes=True)
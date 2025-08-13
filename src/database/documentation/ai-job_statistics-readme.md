# job_statistics.py Documentation

## Overview

This module defines Pydantic models for job-related statistics, including application metrics, competitiveness analysis, trend data, and company statistics.

## Models

### ApplicationStatistics

Statistics related to job applications.

*   `total_applications`: Total number of applications received.
*   `applications_per_day`: Average applications per day since posting.
*   `application_sources`: Breakdown of application sources (website, external, etc.).
*   `recent_application_trend`: Recent trend direction: increasing, decreasing, stable.
*   `days_since_posted`: Number of days since job was posted.

### CompetitivenessMetrics

Metrics related to job competitiveness and ATS analysis.

*   `match_score_distribution`: Distribution of match scores in ranges: 0-20, 21-40, 41-60, 61-80, 81-100.
*   `average_match_score`: Average ATS match score across all applications.
*   `top_matched_keywords`: Top 5 most commonly matched keywords.
*   `top_missing_keywords`: Top 5 most commonly missing keywords.
*   `ats_readiness_percentage`: Percentage of applications with good ATS scores (>=75).
*   `total_ats_reports`: Total number of ATS reports available.

### TrendDataPoint

Single data point for trend analysis.

*   `date`: Date of the data point.
*   `count`: Number of applications on this date.

### TrendAnalysis

Analysis of application trends over time.

*   `daily_applications`: Daily application counts over time.
*   `application_velocity`: Application trend: accelerating, decelerating, steady.
*   `industry_comparison`: Comparison with industry averages.
*   `peak_application_days`: Days of the week with highest application rates.
*   `trend_direction`: Overall trend direction: increasing, decreasing, stable.

### CompanyStatistics

Statistics related to the hiring company.

*   `total_jobs_12_months`: Total jobs posted in last 12 months.
*   `average_applications_per_job`: Average applications per job for this company.
*   `average_time_to_fill`: Average days to fill positions (if available).
*   `application_response_rate`: Percentage of applications that receive employer response.
*   `hiring_activity_level`: Company hiring activity: high, medium, low.
*   `total_active_jobs`: Currently active job postings.
*   `company_age_days`: Days since company registration
    *

### JobStatistics

Comprehensive job statistics container for candidate job intelligence display.

*   `job_id`: Job ID these statistics relate to.
*   `application_stats`: `ApplicationStatistics` object.
*   `competitiveness`: `CompetitivenessMetrics` object.
*   `trends`: `TrendAnalysis` object.
*   `company_stats`: `CompanyStatistics` object.
*   `calculated_at`: When these statistics were calculated.
*   `cache_ttl_seconds`: Cache TTL in seconds.

### StatisticsError

Error information when statistics calculation fails

*   `error_type`: Type of error encountered
*   `error_message`: Human-readable error message
*   `fallback_available`: Whether fallback data is available
*   `retry_after_seconds`: Suggested retry delay

## Relationships to SQL Models

These models are used for statistical analysis and reporting and do not directly map to any specific SQL models, but they might be related to other models.
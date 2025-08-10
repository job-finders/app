"""
Job Statistics Service

This service handles the calculation, caching, and retrieval of comprehensive
job-related statistics including application metrics, competitiveness analysis,
trend data, and company statistics.
"""

import asyncio
import logging
from collections import Counter, defaultdict
from datetime import date
from datetime import timedelta
from typing import Optional, Dict, List, Tuple

from src.cache.cache_redis import cache
from src.database.constants import utc_time
from src.database.models.job_statistics import (
    JobStatistics, ApplicationStatistics, CompetitivenessMetrics,
    TrendAnalysis, TrendDataPoint, CompanyStatistics
)
from src.database.models.jobs_model import Job, JobApplication
from src.utils.route_helpers import get_controller

logger = logging.getLogger(__name__)


class JobStatisticsService:
    """Service for calculating and caching job-related statistics"""

    def __init__(self):
        self.cache = cache

    async def get_job_statistics(self, job_id: str) -> Optional[JobStatistics]:
        """
        Get comprehensive statistics for a job with caching and fallback handling

        Args:
            job_id: The job ID to get statistics for

        Returns:
            JobStatistics object or None if job not found
        """
        try:
            # Validate input
            if not job_id or not isinstance(job_id, str):
                logger.error(f"Invalid job_id provided: {job_id}")
                return None

            # Try to get from cache first
            try:
                cached_stats = self._get_cached_statistics(job_id)
                if cached_stats and cached_stats.is_data_fresh:
                    logger.debug(f"Returning cached statistics for job {job_id}")
                    return cached_stats
            except Exception as cache_error:
                logger.warning(f"Cache retrieval failed for job {job_id}: {cache_error}")
                # Continue with fresh calculation

            # Get job data with timeout
            job_controller = get_controller('jobs_search')
            job = await asyncio.wait_for(
                job_controller.get_complete_job_by_id(job_id=job_id),
                timeout=10.0  # 10 second timeout
            )

            if not job:
                logger.warning(f"Job not found: {job_id}")
                return None

            # Calculate statistics with individual error handling
            statistics_components = {}

            # Application statistics (most critical)
            try:
                statistics_components['app_stats'] = await asyncio.wait_for(
                    self.get_application_statistics(job),
                    timeout=5.0
                )
            except Exception as e:
                logger.error(f"Error calculating application statistics for {job_id}: {e}")
                statistics_components['app_stats'] = self._get_fallback_application_stats(job)

            # Competitiveness metrics (can fail gracefully)
            try:
                statistics_components['competitiveness'] = await asyncio.wait_for(
                    self.get_competitiveness_metrics(job),
                    timeout=5.0
                )
            except Exception as e:
                logger.error(f"Error calculating competitiveness metrics for {job_id}: {e}")
                statistics_components['competitiveness'] = self._get_fallback_competitiveness_metrics()

            # Trend analysis (can fail gracefully)
            try:
                statistics_components['trends'] = await asyncio.wait_for(
                    self.get_trend_analysis(job),
                    timeout=5.0
                )
            except Exception as e:
                logger.error(f"Error calculating trend analysis for {job_id}: {e}")
                statistics_components['trends'] = self._get_fallback_trend_analysis()

            # Company statistics (can fail gracefully)
            try:
                if job.company_id:
                    statistics_components['company_stats'] = await asyncio.wait_for(
                        self.get_company_statistics(job.company_id),
                        timeout=5.0
                    )
                else:
                    statistics_components['company_stats'] = self._get_fallback_company_stats()
            except Exception as e:
                logger.error(f"Error calculating company statistics for {job_id}: {e}")
                statistics_components['company_stats'] = self._get_fallback_company_stats()

            # Create comprehensive statistics object
            statistics = JobStatistics(
                job_id=job_id,
                application_stats=statistics_components['app_stats'],
                competitiveness=statistics_components['competitiveness'],
                trends=statistics_components['trends'],
                company_stats=statistics_components['company_stats'],
                calculated_at=utc_time()
            )

            # Cache the results (don't fail if caching fails)
            try:
                self._cache_statistics(job_id, statistics)
            except Exception as cache_error:
                logger.warning(f"Failed to cache statistics for job {job_id}: {cache_error}")

            return statistics

        except asyncio.TimeoutError:
            logger.error(f"Timeout calculating job statistics for {job_id}")
            return self._get_minimal_fallback_statistics(job_id)
        except Exception as e:
            logger.error(f"Unexpected error calculating job statistics for {job_id}: {e}")
            return self._get_minimal_fallback_statistics(job_id)

    async def get_application_statistics(self, job: Job) -> ApplicationStatistics:
        """
        Calculate application-related statistics for a job

        Args:
            job: The Job object to analyze

        Returns:
            ApplicationStatistics object
        """
        try:
            # Use existing computed properties from Job model
            total_applications = job.total_applications_count if hasattr(job, 'total_applications_count') else len(job.applications or [])

            # Calculate days since posted
            days_since_posted = (utc_time() - job.posted_at).days if job.posted_at else 1
            days_since_posted = max(1, days_since_posted)  # Avoid division by zero

            # Calculate applications per day
            applications_per_day = total_applications / days_since_posted

            # Analyze application sources
            application_sources = self._analyze_application_sources(job.applications or [])

            # Determine recent trend
            recent_trend = await self._calculate_recent_application_trend(job.applications or [])

            return ApplicationStatistics(
                total_applications=total_applications,
                applications_per_day=applications_per_day,
                application_sources=application_sources,
                recent_application_trend=recent_trend,
                days_since_posted=days_since_posted
            )

        except Exception as e:
            logger.error(f"Error calculating application statistics: {e}")
            return ApplicationStatistics(
                total_applications=0,
                applications_per_day=0.0,
                application_sources={},
                recent_application_trend="stable",
                days_since_posted=1
            )

    async def get_competitiveness_metrics(self, job: Job) -> CompetitivenessMetrics:
        """
        Calculate job competitiveness metrics based on ATS data

        Args:
            job: The Job object to analyze

        Returns:
            CompetitivenessMetrics object
        """
        try:
            ats_reports = job.ats_reports or []

            if not ats_reports:
                return CompetitivenessMetrics(
                    match_score_distribution={},
                    average_match_score=None,
                    top_matched_keywords=[],
                    top_missing_keywords=[],
                    ats_readiness_percentage=0.0,
                    total_ats_reports=0
                )

            # Calculate match score distribution
            score_distribution = self._calculate_score_distribution(ats_reports)

            # Calculate average match score
            scores = [report.score for report in ats_reports if report.score is not None]
            average_score = sum(scores) / len(scores) if scores else None

            # Get top matched and missing keywords
            top_matched = self._get_top_keywords([report.matched_keywords for report in ats_reports])
            top_missing = self._get_top_keywords([report.missing_keywords for report in ats_reports])

            # Calculate ATS readiness percentage
            ready_count = sum(1 for report in ats_reports if report.score and report.score >= 75)
            readiness_percentage = (ready_count / len(ats_reports)) * 100 if ats_reports else 0.0

            return CompetitivenessMetrics(
                match_score_distribution=score_distribution,
                average_match_score=average_score,
                top_matched_keywords=top_matched,
                top_missing_keywords=top_missing,
                ats_readiness_percentage=readiness_percentage,
                total_ats_reports=len(ats_reports)
            )

        except Exception as e:
            logger.error(f"Error calculating competitiveness metrics: {e}")
            return CompetitivenessMetrics(
                match_score_distribution={},
                average_match_score=None,
                top_matched_keywords=[],
                top_missing_keywords=[],
                ats_readiness_percentage=0.0,
                total_ats_reports=0
            )

    async def get_trend_analysis(self, job: Job) -> TrendAnalysis:
        """
        Calculate application trends over time

        Args:
            job: The Job object to analyze

        Returns:
            TrendAnalysis object
        """
        try:
            applications = job.applications or []

            if not applications:
                return TrendAnalysis(
                    daily_applications=[],
                    application_velocity="steady",
                    industry_comparison={},
                    peak_application_days=[],
                    trend_direction="stable"
                )

            # Group applications by date
            daily_counts = self._group_applications_by_date(applications)

            # Create trend data points
            daily_applications = [
                TrendDataPoint(date=date_obj, count=count)
                for date_obj, count in sorted(daily_counts.items())
            ]

            # Calculate application velocity and trend direction
            velocity, direction = self._calculate_velocity_and_direction(daily_applications)

            # Find peak application days
            peak_days = self._find_peak_application_days(applications)

            # Get industry comparison (simplified for now)
            industry_comparison = await self._get_industry_comparison(job)

            return TrendAnalysis(
                daily_applications=daily_applications,
                application_velocity=velocity,
                industry_comparison=industry_comparison,
                peak_application_days=peak_days,
                trend_direction=direction
            )

        except Exception as e:
            logger.error(f"Error calculating trend analysis: {e}")
            return TrendAnalysis(
                daily_applications=[],
                application_velocity="steady",
                industry_comparison={},
                peak_application_days=[],
                trend_direction="stable"
            )

    async def get_company_statistics(self, company_id: str) -> CompanyStatistics:
        """
        Calculate company hiring statistics

        Args:
            company_id: The company ID to analyze

        Returns:
            CompanyStatistics object
        """
        try:
            # Get company data
            company_controller = get_controller('company')
            company = await company_controller.get_company_by_id(company_id)

            if not company:
                return CompanyStatistics(
                    total_jobs_12_months=0,
                    average_applications_per_job=0.0,
                    application_response_rate=0.0,
                    total_active_jobs=0
                )

            # Use existing computed properties from Company model
            total_jobs_12_months = self._count_jobs_last_12_months(company.jobs or [])
            avg_applications = company.avg_applications_per_job if hasattr(company, 'avg_applications_per_job') else 0.0
            response_rate = company.application_response_rate if hasattr(company, 'application_response_rate') else 0.0
            active_jobs = company.active_jobs if hasattr(company, 'active_jobs') else 0

            # Determine hiring activity level
            activity_level = self._determine_hiring_activity_level(total_jobs_12_months, active_jobs)

            # Calculate company age
            company_age = (utc_time() - company.posted_at).days if company.posted_at else None

            return CompanyStatistics(
                total_jobs_12_months=total_jobs_12_months,
                average_applications_per_job=avg_applications,
                application_response_rate=response_rate,
                hiring_activity_level=activity_level,
                total_active_jobs=active_jobs,
                company_age_days=company_age
            )

        except Exception as e:
            logger.error(f"Error calculating company statistics: {e}")
            return CompanyStatistics(
                total_jobs_12_months=0,
                average_applications_per_job=0.0,
                application_response_rate=0.0,
                total_active_jobs=0
            )

    # Helper methods

    @staticmethod
    def _analyze_application_sources(applications: List[JobApplication]) -> Dict[str, int]:
        """Analyze where applications are coming from"""
        sources = Counter()
        for app in applications:
            method = getattr(app, 'method', 'website') or 'website'
            sources[method] += 1
        return dict(sources)

    @staticmethod
    async def _calculate_recent_application_trend(applications: List[JobApplication]) -> str:
        """Calculate recent application trend (last 7 days vs previous 7 days)"""
        if len(applications) < 2:
            return "stable"

        now = utc_time()
        last_7_days = now - timedelta(days=7)
        previous_7_days = now - timedelta(days=14)

        recent_count = sum(1 for app in applications if app.applied_date_as_datetime >= last_7_days)
        previous_count = sum(1 for app in applications
                             if previous_7_days <= app.applied_date_as_datetime < last_7_days)

        if recent_count > previous_count * 1.2:
            return "increasing"
        elif recent_count < previous_count * 0.8:
            return "decreasing"
        else:
            return "stable"

    # noinspection DuplicatedCode
    @staticmethod
    def _calculate_score_distribution(ats_reports) -> Dict[str, int]:
        """Calculate distribution of ATS scores in ranges"""
        distribution = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}

        for report in ats_reports:
            if report.score is None:
                continue

            score = report.score
            if score <= 20:
                distribution["0-20"] += 1
            elif score <= 40:
                distribution["21-40"] += 1
            elif score <= 60:
                distribution["41-60"] += 1
            elif score <= 80:
                distribution["61-80"] += 1
            else:
                distribution["81-100"] += 1

        return distribution

    @staticmethod
    def _get_top_keywords(keyword_lists: List[List[str]], top_n: int = 5) -> List[str]:
        """Get top N most common keywords from lists of keywords"""
        all_keywords = []
        for keyword_list in keyword_lists:
            if keyword_list:
                all_keywords.extend(keyword_list)

        counter = Counter(all_keywords)
        return [keyword for keyword, _ in counter.most_common(top_n)]

    @staticmethod
    def _group_applications_by_date(applications: List[JobApplication]) -> Dict[date, int]:
        """Group applications by date"""
        daily_counts = defaultdict(int)

        for app in applications:
            if app.applied_date:
                app_date = app.applied_date_as_datetime.date()
                daily_counts[app_date] += 1

        return dict(daily_counts)

    @staticmethod
    def _calculate_velocity_and_direction(daily_applications: List[TrendDataPoint]) -> Tuple[str, str]:
        """Calculate application velocity and overall direction"""
        if len(daily_applications) < 3:
            return "steady", "stable"

        # Calculate trend over recent data points
        recent_points = daily_applications[-7:]  # Last 7 days
        if len(recent_points) < 2:
            return "steady", "stable"

        # Simple linear trend calculation
        total_change = recent_points[-1].count - recent_points[0].count
        days_span = len(recent_points) - 1

        if days_span == 0:
            return "steady", "stable"

        avg_change_per_day = total_change / days_span

        # Determine velocity
        if abs(avg_change_per_day) >= 2:
            velocity = "accelerating" if avg_change_per_day > 0 else "decelerating"
        else:
            velocity = "steady"

        # Determine direction
        if avg_change_per_day > 0.5:
            direction = "increasing"
        elif avg_change_per_day < -0.5:
            direction = "decreasing"
        else:
            direction = "stable"

        return velocity, direction

    @staticmethod
    def _find_peak_application_days(applications: List[JobApplication]) -> List[str]:
        """Find days of the week with highest application rates"""
        day_counts = defaultdict(int)
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for app in applications:
            if app.applied_date:
                day_of_week = app.applied_date_as_datetime.weekday()  # 0 = Monday
                day_counts[day_names[day_of_week]] += 1

        if not day_counts:
            return []

        # Return top 2 days
        sorted_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)
        return [day for day, _ in sorted_days[:2]]

    @staticmethod
    async def _get_industry_comparison(job: Job) -> Dict[str, float]:
        """Get industry comparison data (simplified implementation)"""
        try:
            # This would ideally compare with other jobs in the same category
            # For now, return a simple comparison
            job_apps_per_day = len(job.applications or []) / max(1, (utc_time() - job.posted_at).days)

            # Simplified industry average (would be calculated from actual data)
            industry_average = 2.5  # This should come from actual industry data

            return {
                "this_job": round(job_apps_per_day, 1),
                "industry_average": industry_average,
                "comparison": "above" if job_apps_per_day > industry_average else "below"
            }
        except Exception:
            return {}

    @staticmethod
    def _count_jobs_last_12_months(jobs: List[Job]) -> int:
        """Count jobs posted in the last 12 months"""
        cutoff_date = utc_time() - timedelta(days=365)
        return sum(1 for job in jobs if job.posted_at and job.posted_at >= cutoff_date)

    @staticmethod
    def _determine_hiring_activity_level(jobs_12_months: int, active_jobs: int) -> str:
        """Determine company hiring activity level"""
        if jobs_12_months >= 20 or active_jobs >= 10:
            return "high"
        elif jobs_12_months >= 5 or active_jobs >= 3:
            return "medium"
        else:
            return "low"

    # Caching methods - now using custom RedisCache

    def _get_cached_statistics(self, job_id: str) -> Optional[JobStatistics]:
        """Get statistics from cache using custom RedisCache"""
        if not self.cache:
            return None

        try:
            cache_key = f"job_stats:{job_id}"
            cached_data = self.cache.get(cache_key)

            if cached_data:
                # cached_data is already unpickled by RedisCache
                return JobStatistics(**cached_data)
        except Exception as e:
            logger.warning(f"Error retrieving cached statistics: {e}")

        return None

    def _cache_statistics(self, job_id: str, statistics: JobStatistics):
        """Cache statistics using custom RedisCache with appropriate TTL"""
        if not self.cache:
            return

        try:
            cache_key = f"job_stats:{job_id}"
            cache_data = statistics.model_dump(mode='json')

            # Set TTL based on data freshness requirements
            ttl = getattr(statistics, 'cache_ttl_seconds', 30 * 60)  # default 30 minutes

            self.cache.set(cache_key, cache_data, ttl)
        except Exception as e:
            logger.warning(f"Error caching statistics: {e}")

    def invalidate_job_statistics_cache(self, job_id: str):
        """Invalidate cached statistics for a job"""
        if not self.cache:
            return

        try:
            cache_key = f"job_stats:{job_id}"
            self.cache.delete(cache_key)
        except Exception as e:
            logger.warning(f"Error invalidating statistics cache: {e}")
    
    # Fallback methods for error handling

    @staticmethod
    def _get_fallback_application_stats(job) -> ApplicationStatistics:
        """Get minimal application statistics when calculation fails"""
        try:
            total_apps = len(job.applications or [])
            days_posted = max(1, (utc_time() - job.posted_at).days) if job.posted_at else 1
            
            return ApplicationStatistics(
                total_applications=total_apps,
                applications_per_day=total_apps / days_posted,
                application_sources={"website": total_apps} if total_apps > 0 else {},
                recent_application_trend="stable",
                days_since_posted=days_posted
            )
        except Exception:
            return ApplicationStatistics(
                total_applications=0,
                applications_per_day=0.0,
                application_sources={},
                recent_application_trend="stable",
                days_since_posted=1
            )

    @staticmethod
    def _get_fallback_competitiveness_metrics() -> CompetitivenessMetrics:
        """Get empty competitiveness metrics when calculation fails"""
        return CompetitivenessMetrics(
            match_score_distribution={},
            average_match_score=None,
            top_matched_keywords=[],
            top_missing_keywords=[],
            ats_readiness_percentage=0.0,
            total_ats_reports=0
        )

    @staticmethod
    def _get_fallback_trend_analysis() -> TrendAnalysis:
        """Get empty trend analysis when calculation fails"""
        return TrendAnalysis(
            daily_applications=[],
            application_velocity="steady",
            industry_comparison={},
            peak_application_days=[],
            trend_direction="stable"
        )

    @staticmethod
    def _get_fallback_company_stats() -> CompanyStatistics:
        """Get empty company statistics when calculation fails"""
        return CompanyStatistics(
            total_jobs_12_months=0,
            average_applications_per_job=0.0,
            application_response_rate=0.0,
            total_active_jobs=0
        )

    @staticmethod
    def _get_minimal_fallback_statistics(job_id: str) -> Optional[JobStatistics]:
        """Get minimal statistics when everything fails"""
        try:
            return JobStatistics(
                job_id=job_id,
                application_stats=ApplicationStatistics(
                    total_applications=0,
                    applications_per_day=0.0,
                    application_sources={},
                    recent_application_trend="stable",
                    days_since_posted=1
                ),
                competitiveness=CompetitivenessMetrics(
                    match_score_distribution={},
                    average_match_score=None,
                    top_matched_keywords=[],
                    top_missing_keywords=[],
                    ats_readiness_percentage=0.0,
                    total_ats_reports=0
                ),
                trends=TrendAnalysis(
                    daily_applications=[],
                    application_velocity="steady",
                    industry_comparison={},
                    peak_application_days=[],
                    trend_direction="stable"
                ),
                company_stats=CompanyStatistics(
                    total_jobs_12_months=0,
                    average_applications_per_job=0.0,
                    application_response_rate=0.0,
                    total_active_jobs=0
                ),
                calculated_at=utc_time()
            )
        except Exception as e:
            logger.error(f"Failed to create minimal fallback statistics: {e}")
            return None
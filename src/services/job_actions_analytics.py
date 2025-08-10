# Standard Library
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any

# Third-party
from pydantic import BaseModel, Field

# Flask Core
from flask import Flask

# SQLAlchemy Core & ORM
from sqlalchemy import select, func, and_, case, desc
from sqlalchemy.orm import joinedload

# Controllers
from src.controllers.controller import Controllers, error_handler

# Domain Models
# These models are defined inline since they're specific to analytics

# SQL Models (ORMs)
from src.database import (
    JobsORM,
    JobLikeORM,
    JobShareORM,
    SavedJobORM,
    CompanyORM,
    JobApplicationORM
)


class JobActionsAnalyticsEvent(BaseModel):
    """Analytics event for job actions tracking"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = Field(pattern="^(job_like|job_unlike|job_save|job_unsave|job_share|job_view)$")
    user_id: Optional[str] = None
    job_id: str
    company_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class JobEngagementMetrics(BaseModel):
    """Job engagement metrics for analytics"""
    job_id: str
    total_likes: int = 0
    total_saves: int = 0
    total_shares: int = 0
    total_views: int = 0
    total_applications: int = 0
    engagement_rate: float = 0.0
    save_to_apply_rate: float = 0.0
    like_to_apply_rate: float = 0.0
    share_conversion_rate: float = 0.0
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        from_attributes = True


class JobActionsReport(BaseModel):
    """Comprehensive job actions analytics report"""
    company_id: str
    report_period_start: datetime
    report_period_end: datetime
    total_jobs: int = 0
    total_engagement_events: int = 0
    top_performing_jobs: List[Dict[str, Any]] = Field(default_factory=list)
    engagement_trends: Dict[str, List[int]] = Field(default_factory=dict)
    conversion_metrics: Dict[str, float] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        from_attributes = True


class CompanyEngagementStats(BaseModel):
    """Company-level engagement statistics"""
    company_id: str
    total_job_likes: int = 0
    total_job_saves: int = 0
    total_job_shares: int = 0
    average_engagement_per_job: float = 0.0
    most_liked_job_id: Optional[str] = None
    most_saved_job_id: Optional[str] = None
    most_shared_job_id: Optional[str] = None
    engagement_growth_rate: float = 0.0
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        from_attributes = True


class JobActionsAnalyticsService(Controllers):
    """Service for tracking and analyzing job actions analytics"""

    def __init__(self, factory):
        super().__init__(factory)
        self.analytics_events = []  # In-memory buffer for events

    def init_app(self, app: Flask):
        super().init_app(app=app)

    @error_handler
    async def track_job_action(self, event_type: str, user_id: Optional[str], job_id: str,
                               metadata: Dict[str, Any] = None) -> bool:
        """Track a job action event for analytics"""
        if not job_id or not event_type:
            return False

        if metadata is None:
            metadata = {}

        # Get company_id for the job
        with self.get_session() as session:
            job_orm = session.query(JobsORM).filter_by(job_id=job_id).first()
            if not job_orm:
                return False

            company_id = job_orm.company_id

        # Create analytics event
        event = JobActionsAnalyticsEvent(
            event_type=event_type,
            user_id=user_id,
            job_id=job_id,
            company_id=company_id,
            metadata=metadata
        )

        # Store event (in production, this would go to a proper analytics service)
        self.analytics_events.append(event)

        # Log for monitoring
        self.logger.info(f"Tracked job action: {event_type} for job {job_id} by user {user_id}")

        return True

    @error_handler
    async def get_job_engagement_metrics(self, job_id: str) -> Optional[JobEngagementMetrics]:
        """Get comprehensive engagement metrics for a specific job"""
        if not job_id:
            return None

        with self.get_session() as session:
            # Get basic job info
            job_orm = session.query(JobsORM).filter_by(job_id=job_id).first()
            if not job_orm:
                return None

            # Count likes
            total_likes = session.query(func.count(JobLikeORM.like_id)).filter_by(job_id=job_id).scalar() or 0

            # Count saves
            total_saves = session.query(func.count(SavedJobORM.saved_job_id)).filter_by(job_id=job_id).scalar() or 0

            # Count shares
            total_shares = session.query(func.count(JobShareORM.share_id)).filter_by(job_id=job_id).scalar() or 0

            # Get views from job table
            total_views = job_orm.view_count or 0

            # Count applications
            total_applications = session.query(func.count(JobApplicationORM.application_id)).filter_by(
                job_id=job_id).scalar() or 0

            # Calculate engagement rate (total engagements / views)
            total_engagements = total_likes + total_saves + total_shares
            engagement_rate = (total_engagements / total_views * 100) if total_views > 0 else 0.0

            # Calculate conversion rates
            save_to_apply_rate = (total_applications / total_saves * 100) if total_saves > 0 else 0.0
            like_to_apply_rate = (total_applications / total_likes * 100) if total_likes > 0 else 0.0
            share_conversion_rate = (total_applications / total_shares * 100) if total_shares > 0 else 0.0

            return JobEngagementMetrics(
                job_id=job_id,
                total_likes=total_likes,
                total_saves=total_saves,
                total_shares=total_shares,
                total_views=total_views,
                total_applications=total_applications,
                engagement_rate=round(engagement_rate, 2),
                save_to_apply_rate=round(save_to_apply_rate, 2),
                like_to_apply_rate=round(like_to_apply_rate, 2),
                share_conversion_rate=round(share_conversion_rate, 2)
            )

    @error_handler
    async def get_company_engagement_stats(self, company_id: str, days: int = 30) -> Optional[CompanyEngagementStats]:
        """Get engagement statistics for all jobs from a company"""
        if not company_id:
            return None

        with self.get_session() as session:
            # Get all jobs for the company
            company_jobs = session.query(JobsORM.job_id).filter_by(company_id=company_id).subquery()

            # Calculate totals
            total_likes = session.query(func.count(JobLikeORM.like_id)).filter(
                JobLikeORM.job_id.in_(select(company_jobs.c.job_id))
            ).scalar() or 0

            total_saves = session.query(func.count(SavedJobORM.saved_job_id)).filter(
                SavedJobORM.job_id.in_(select(company_jobs.c.job_id))
            ).scalar() or 0

            total_shares = session.query(func.count(JobShareORM.share_id)).filter(
                JobShareORM.job_id.in_(select(company_jobs.c.job_id))
            ).scalar() or 0

            # Get job count
            job_count = session.query(func.count(JobsORM.job_id)).filter_by(company_id=company_id).scalar() or 1

            # Calculate average engagement per job
            total_engagements = total_likes + total_saves + total_shares
            average_engagement = total_engagements / job_count if job_count > 0 else 0.0

            # Find most engaged jobs
            most_liked_job = session.query(JobsORM.job_id).join(JobLikeORM).filter(
                JobsORM.company_id == company_id
            ).group_by(JobsORM.job_id).order_by(
                func.count(JobLikeORM.like_id).desc()
            ).first()

            most_saved_job = session.query(JobsORM.job_id).join(SavedJobORM).filter(
                JobsORM.company_id == company_id
            ).group_by(JobsORM.job_id).order_by(
                func.count(SavedJobORM.saved_job_id).desc()
            ).first()

            most_shared_job = session.query(JobsORM.job_id).join(JobShareORM).filter(
                JobsORM.company_id == company_id
            ).group_by(JobsORM.job_id).order_by(
                func.count(JobShareORM.share_id).desc()
            ).first()

            # Calculate growth rate (simplified - comparing last 30 days to previous 30 days)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            recent_engagements = session.query(func.count(JobLikeORM.like_id)).filter(
                JobLikeORM.job_id.in_(select(company_jobs.c.job_id)),
                JobLikeORM.created_at >= cutoff_date
            ).scalar() or 0

            previous_cutoff = cutoff_date - timedelta(days=days)
            previous_engagements = session.query(func.count(JobLikeORM.like_id)).filter(
                JobLikeORM.job_id.in_(select(company_jobs.c.job_id)),
                JobLikeORM.created_at >= previous_cutoff,
                JobLikeORM.created_at < cutoff_date
            ).scalar() or 0

            growth_rate = ((
                                       recent_engagements - previous_engagements) / previous_engagements * 100) if previous_engagements > 0 else 0.0

            return CompanyEngagementStats(
                company_id=company_id,
                total_job_likes=total_likes,
                total_job_saves=total_saves,
                total_job_shares=total_shares,
                average_engagement_per_job=round(average_engagement, 2),
                most_liked_job_id=most_liked_job[0] if most_liked_job else None,
                most_saved_job_id=most_saved_job[0] if most_saved_job else None,
                most_shared_job_id=most_shared_job[0] if most_shared_job else None,
                engagement_growth_rate=round(growth_rate, 2)
            )

    @error_handler
    async def generate_job_actions_report(self, company_id: str, days: int = 30) -> Optional[JobActionsReport]:
        """Generate comprehensive job actions analytics report for a company"""
        if not company_id:
            return None

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        with self.get_session() as session:
            # Get company jobs
            company_jobs = session.query(JobsORM).filter_by(company_id=company_id).all()
            job_ids = [job.job_id for job in company_jobs]

            if not job_ids:
                return JobActionsReport(
                    company_id=company_id,
                    report_period_start=start_date,
                    report_period_end=end_date
                )

            # Count total engagement events in period
            total_likes = session.query(func.count(JobLikeORM.like_id)).filter(
                JobLikeORM.job_id.in_(job_ids),
                JobLikeORM.created_at >= start_date
            ).scalar() or 0

            total_saves = session.query(func.count(SavedJobORM.saved_job_id)).filter(
                SavedJobORM.job_id.in_(job_ids),
                SavedJobORM.saved_at >= start_date
            ).scalar() or 0

            total_shares = session.query(func.count(JobShareORM.share_id)).filter(
                JobShareORM.job_id.in_(job_ids),
                JobShareORM.shared_at >= start_date
            ).scalar() or 0

            total_engagement_events = total_likes + total_saves + total_shares

            # Get top performing jobs
            top_jobs_query = session.query(
                JobsORM.job_id,
                JobsORM.title,
                func.count(JobLikeORM.like_id).label('likes'),
                func.count(SavedJobORM.saved_job_id).label('saves'),
                func.count(JobShareORM.share_id).label('shares')
            ).outerjoin(JobLikeORM).outerjoin(SavedJobORM).outerjoin(JobShareORM).filter(
                JobsORM.company_id == company_id
            ).group_by(JobsORM.job_id, JobsORM.title).order_by(
                (func.count(JobLikeORM.like_id) + func.count(SavedJobORM.saved_job_id) + func.count(
                    JobShareORM.share_id)).desc()
            ).limit(10).all()

            top_performing_jobs = [
                {
                    "job_id": job.job_id,
                    "title": job.title,
                    "total_likes": job.likes,
                    "total_saves": job.saves,
                    "total_shares": job.shares,
                    "total_engagement": job.likes + job.saves + job.shares
                }
                for job in top_jobs_query
            ]

            # Generate engagement trends (daily counts for the period)
            engagement_trends = await self._calculate_engagement_trends(job_ids, start_date, end_date)

            # Calculate conversion metrics
            total_applications = session.query(func.count(JobApplicationORM.application_id)).filter(
                JobApplicationORM.job_id.in_(job_ids),
                JobApplicationORM.applied_date >= start_date
            ).scalar() or 0

            conversion_metrics = {
                "save_to_apply_rate": (total_applications / total_saves * 100) if total_saves > 0 else 0.0,
                "like_to_apply_rate": (total_applications / total_likes * 100) if total_likes > 0 else 0.0,
                "share_to_apply_rate": (total_applications / total_shares * 100) if total_shares > 0 else 0.0,
                "overall_engagement_to_apply_rate": (
                            total_applications / total_engagement_events * 100) if total_engagement_events > 0 else 0.0
            }

            return JobActionsReport(
                company_id=company_id,
                report_period_start=start_date,
                report_period_end=end_date,
                total_jobs=len(company_jobs),
                total_engagement_events=total_engagement_events,
                top_performing_jobs=top_performing_jobs,
                engagement_trends=engagement_trends,
                conversion_metrics={k: round(v, 2) for k, v in conversion_metrics.items()}
            )

    async def _calculate_engagement_trends(self, job_ids: List[str], start_date: datetime, end_date: datetime) -> Dict[
        str, List[int]]:
        """Calculate daily engagement trends for the reporting period"""
        if not job_ids:
            return {}

        with self.get_session() as session:
            # Generate daily buckets
            days = (end_date - start_date).days
            daily_likes = [0] * days
            daily_saves = [0] * days
            daily_shares = [0] * days

            # Get daily like counts
            likes_by_day = session.query(
                func.date(JobLikeORM.created_at).label('date'),
                func.count(JobLikeORM.like_id).label('count')
            ).filter(
                JobLikeORM.job_id.in_(job_ids),
                JobLikeORM.created_at >= start_date,
                JobLikeORM.created_at < end_date
            ).group_by(func.date(JobLikeORM.created_at)).all()

            # Get daily save counts
            saves_by_day = session.query(
                func.date(SavedJobORM.saved_at).label('date'),
                func.count(SavedJobORM.saved_job_id).label('count')
            ).filter(
                SavedJobORM.job_id.in_(job_ids),
                SavedJobORM.saved_at >= start_date,
                SavedJobORM.saved_at < end_date
            ).group_by(func.date(SavedJobORM.saved_at)).all()

            # Get daily share counts
            shares_by_day = session.query(
                func.date(JobShareORM.shared_at).label('date'),
                func.count(JobShareORM.share_id).label('count')
            ).filter(
                JobShareORM.job_id.in_(job_ids),
                JobShareORM.shared_at >= start_date,
                JobShareORM.shared_at < end_date
            ).group_by(func.date(JobShareORM.shared_at)).all()

            # Fill in the daily arrays
            for date, count in likes_by_day:
                day_index = (date - start_date.date()).days
                if 0 <= day_index < days:
                    daily_likes[day_index] = count

            for date, count in saves_by_day:
                day_index = (date - start_date.date()).days
                if 0 <= day_index < days:
                    daily_saves[day_index] = count

            for date, count in shares_by_day:
                day_index = (date - start_date.date()).days
                if 0 <= day_index < days:
                    daily_shares[day_index] = count

            return {
                "likes": daily_likes,
                "saves": daily_saves,
                "shares": daily_shares
            }

    @error_handler
    async def get_user_engagement_history(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get a user's job engagement history"""
        if not user_id:
            return {}

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        with self.get_session() as session:
            # Get user's likes in period
            likes = session.query(JobLikeORM).filter(
                JobLikeORM.user_id == user_id,
                JobLikeORM.created_at >= start_date
            ).count()

            # Get user's saves in period
            saves = session.query(SavedJobORM).filter(
                SavedJobORM.user_id == user_id,
                SavedJobORM.saved_at >= start_date
            ).count()

            # Get user's shares in period
            shares = session.query(JobShareORM).filter(
                JobShareORM.user_id == user_id,
                JobShareORM.shared_at >= start_date
            ).count()

            # Get user's applications in period
            applications = session.query(JobApplicationORM).filter(
                JobApplicationORM.user_id == user_id,
                JobApplicationORM.applied_date >= start_date
            ).count()

            return {
                "user_id": user_id,
                "period_days": days,
                "total_likes": likes,
                "total_saves": saves,
                "total_shares": shares,
                "total_applications": applications,
                "engagement_score": likes + saves + shares,
                "conversion_rate": (applications / (likes + saves) * 100) if (likes + saves) > 0 else 0.0
            }

    @error_handler
    async def get_popular_jobs_by_engagement(self, limit: int = 10, days: int = 7) -> List[Dict[str, Any]]:
        """Get most popular jobs based on recent engagement"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        with self.get_session() as session:
            # Query jobs with engagement counts
            popular_jobs = session.query(
                JobsORM.job_id,
                JobsORM.title,
                JobsORM.company_id,
                CompanyORM.company_name,
                func.count(JobLikeORM.like_id).label('recent_likes'),
                func.count(SavedJobORM.saved_job_id).label('recent_saves'),
                func.count(JobShareORM.share_id).label('recent_shares')
            ).outerjoin(
                JobLikeORM, and_(
                    JobLikeORM.job_id == JobsORM.job_id,
                    JobLikeORM.created_at >= start_date
                )
            ).outerjoin(
                SavedJobORM, and_(
                    SavedJobORM.job_id == JobsORM.job_id,
                    SavedJobORM.saved_at >= start_date
                )
            ).outerjoin(
                JobShareORM, and_(
                    JobShareORM.job_id == JobsORM.job_id,
                    JobShareORM.shared_at >= start_date
                )
            ).join(CompanyORM).group_by(
                JobsORM.job_id, JobsORM.title, JobsORM.company_id, CompanyORM.company_name
            ).order_by(
                (func.count(JobLikeORM.like_id) + func.count(SavedJobORM.saved_job_id) + func.count(
                    JobShareORM.share_id)).desc()
            ).limit(limit).all()

            return [
                {
                    "job_id": job.job_id,
                    "title": job.title,
                    "company_id": job.company_id,
                    "company_name": job.company_name,
                    "recent_likes": job.recent_likes,
                    "recent_saves": job.recent_saves,
                    "recent_shares": job.recent_shares,
                    "total_recent_engagement": job.recent_likes + job.recent_saves + job.recent_shares
                }
                for job in popular_jobs
            ]

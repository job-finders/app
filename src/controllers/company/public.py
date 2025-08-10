"""
Company Public Profile Controller

Handles public-facing company profile functionality for job seekers to view
company information, active jobs, and statistics.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

from flask import Flask
from sqlalchemy import and_, func, desc
from sqlalchemy.orm import joinedload

from src.controllers.controller import Controllers, error_handler
from src.database.models import Company, Job
from src.database import CompanyORM, JobsORM, JobApplicationORM, JobLikeORM, JobShareORM
from src.cache.job_actions_cache import job_actions_cache


class CompanyPublicController(Controllers):
    """Controller for public company profiles"""

    def __init__(self, factory):
        super().__init__(factory)

    def init_app(self, app: Flask):
        super().init_app(app=app)

    @error_handler
    async def get_public_profile(self, company_id: str) -> Dict[str, Any]:
        """
        Get public company profile information
        
        Args:
            company_id: Company ID
            
        Returns:
            Dict with company profile data
        """
        if not company_id or not company_id.strip():
            return {"success": False, "message": "Invalid company ID", "code": 400}

        # Try to get from cache first
        cached_profile = job_actions_cache.get_company_profile(company_id)
        if cached_profile:
            return {
                "success": True,
                "data": cached_profile
            }

        with self.get_session() as session:
            try:
                # Get company with basic info
                company_orm = (
                    session.query(CompanyORM)
                    .filter_by(company_id=company_id)
                    .first()
                )

                if not company_orm:
                    return {"success": False, "message": "Company not found", "code": 404}

                # Convert to domain model
                company = Company(**company_orm.to_dict())

                # Get additional public statistics
                stats = await self._get_company_public_stats(session, company_id)

                # Prepare public profile data (exclude sensitive information)
                profile_data = {
                    "company_id": company.company_id,
                    "name": company.name,
                    "description": company.description,
                    "industry": company.industry,
                    "website": str(company.website) if company.website else None,
                    "logo_url": str(company.logo_url) if company.logo_url else None,
                    "location": company.location,
                    "employee_count": company.employee_count,
                    "founded_year": company.founded_year,
                    "tech_stack": company.tech_stack or [],
                    "linkedin_url": str(company.linkedin_url) if company.linkedin_url else None,
                    "twitter_handle": company.twitter_handle,
                    "is_verified": company.is_verified,
                    "statistics": stats
                }

                # Cache the result
                job_actions_cache.set_company_profile(company_id, profile_data)

                self.logger.info(f"Retrieved public profile for company {company_id}")

                return {
                    "success": True,
                    "data": profile_data
                }

            except Exception as e:
                self.logger.error(f"Error getting company public profile: {e}")
                return {"success": False, "message": "Internal server error", "code": 500}

    @error_handler
    async def get_company_active_jobs(self, company_id: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Get active jobs for a company
        
        Args:
            company_id: Company ID
            limit: Number of jobs to return
            offset: Offset for pagination
            
        Returns:
            Dict with active jobs data
        """
        if not company_id or not company_id.strip():
            return {"success": False, "message": "Invalid company ID", "code": 400}

        with self.get_session() as session:
            try:
                # Verify company exists
                company_exists = session.query(CompanyORM).filter_by(company_id=company_id).first()
                if not company_exists:
                    return {"success": False, "message": "Company not found", "code": 404}

                # Get active jobs
                current_time = datetime.now(timezone.utc)

                active_jobs_query = (
                    session.query(JobsORM)
                    .filter(
                        and_(
                            JobsORM.company_id == company_id,
                            JobsORM.status == 'active',
                            JobsORM.expires_at > current_time
                        )
                    )
                    .order_by(desc(JobsORM.posted_at))
                    .offset(offset)
                    .limit(limit)
                )

                active_jobs = active_jobs_query.all()

                # Get total count
                total_count = (
                    session.query(func.count(JobsORM.job_id))
                    .filter(
                        and_(
                            JobsORM.company_id == company_id,
                            JobsORM.status == 'active',
                            JobsORM.expires_at > current_time
                        )
                    )
                    .scalar()
                )

                # Format jobs data
                jobs_data = []
                for job_orm in active_jobs:
                    job_data = job_orm.to_dict()

                    # Add engagement metrics
                    like_count = session.query(func.count(JobLikeORM.like_id)).filter_by(job_id=job_orm.job_id).scalar()
                    share_count = session.query(func.count(JobShareORM.share_id)).filter_by(
                        job_id=job_orm.job_id).scalar()

                    job_data.update({
                        "like_count": like_count or 0,
                        "share_count": share_count or 0
                    })

                    jobs_data.append(job_data)

                return {
                    "success": True,
                    "data": {
                        "jobs": jobs_data,
                        "total_count": total_count or 0,
                        "limit": limit,
                        "offset": offset
                    }
                }

            except Exception as e:
                self.logger.error(f"Error getting company active jobs: {e}")
                return {"success": False, "message": "Internal server error", "code": 500}

    @error_handler
    async def get_company_statistics(self, company_id: str) -> Dict[str, Any]:
        """
        Get public statistics for a company
        
        Args:
            company_id: Company ID
            
        Returns:
            Dict with company statistics
        """
        if not company_id or not company_id.strip():
            return {"success": False, "message": "Invalid company ID", "code": 400}

        # Try to get from cache first
        cached_stats = job_actions_cache.get_company_statistics(company_id)
        if cached_stats:
            return {
                "success": True,
                "data": cached_stats
            }

        with self.get_session() as session:
            try:
                # Verify company exists
                company_exists = session.query(CompanyORM).filter_by(company_id=company_id).first()
                if not company_exists:
                    return {"success": False, "message": "Company not found", "code": 404}

                stats = await self._get_company_public_stats(session, company_id)

                # Cache the result
                job_actions_cache.set_company_statistics(company_id, stats)

                return {
                    "success": True,
                    "data": stats
                }

            except Exception as e:
                self.logger.error(f"Error getting company statistics: {e}")
                return {"success": False, "message": "Internal server error", "code": 500}

    @error_handler
    async def get_company_job_categories(self, company_id: str) -> Dict[str, Any]:
        """
        Get job categories for a company's active jobs
        
        Args:
            company_id: Company ID
            
        Returns:
            Dict with job categories data
        """
        if not company_id or not company_id.strip():
            return {"success": False, "message": "Invalid company ID", "code": 400}

        with self.get_session() as session:
            try:
                # Get job categories with counts
                current_time = datetime.now(timezone.utc)

                categories_query = (
                    session.query(
                        JobsORM.category_id,
                        func.count(JobsORM.job_id).label('job_count')
                    )
                    .filter(
                        and_(
                            JobsORM.company_id == company_id,
                            JobsORM.status == 'active',
                            JobsORM.expires_at > current_time
                        )
                    )
                    .group_by(JobsORM.category_id)
                    .all()
                )

                categories_data = []
                for category_id, job_count in categories_query:
                    if category_id:  # Skip jobs without categories
                        categories_data.append({
                            "category_id": category_id,
                            "job_count": job_count
                        })

                return {
                    "success": True,
                    "data": {
                        "categories": categories_data
                    }
                }

            except Exception as e:
                self.logger.error(f"Error getting company job categories: {e}")
                return {"success": False, "message": "Internal server error", "code": 500}

    async def _get_company_public_stats(self, session, company_id: str) -> Dict[str, Any]:
        """
        Get public statistics for a company (internal helper)
        
        Args:
            session: Database session
            company_id: Company ID
            
        Returns:
            Dict with statistics
        """
        current_time = datetime.now(timezone.utc)
        last_30_days = current_time - timedelta(days=30)
        last_12_months = current_time - timedelta(days=365)

        # Total jobs posted
        total_jobs = session.query(func.count(JobsORM.job_id)).filter_by(company_id=company_id).scalar()

        # Active jobs
        active_jobs = (
            session.query(func.count(JobsORM.job_id))
            .filter(
                and_(
                    JobsORM.company_id == company_id,
                    JobsORM.status == 'active',
                    JobsORM.expires_at > current_time
                )
            )
            .scalar()
        )

        # Jobs posted in last 30 days
        recent_jobs = (
            session.query(func.count(JobsORM.job_id))
            .filter(
                and_(
                    JobsORM.company_id == company_id,
                    JobsORM.posted_at >= last_30_days
                )
            )
            .scalar()
        )

        # Jobs posted in last 12 months
        jobs_last_year = (
            session.query(func.count(JobsORM.job_id))
            .filter(
                and_(
                    JobsORM.company_id == company_id,
                    JobsORM.posted_at >= last_12_months
                )
            )
            .scalar()
        )

        # Total applications received
        total_applications = (
            session.query(func.count(JobApplicationORM.application_id))
            .join(JobsORM, JobApplicationORM.job_id == JobsORM.job_id)
            .filter(JobsORM.company_id == company_id)
            .scalar()
        )

        # Average applications per job
        avg_applications = 0
        if total_jobs and total_jobs > 0:
            avg_applications = round((total_applications or 0) / total_jobs, 1)

        # Total job engagement (likes + shares)
        total_likes = (
            session.query(func.count(JobLikeORM.like_id))
            .join(JobsORM, JobLikeORM.job_id == JobsORM.job_id)
            .filter(JobsORM.company_id == company_id)
            .scalar()
        )

        total_shares = (
            session.query(func.count(JobShareORM.share_id))
            .join(JobsORM, JobShareORM.job_id == JobsORM.job_id)
            .filter(JobsORM.company_id == company_id)
            .scalar()
        )

        # Hiring activity level
        hiring_activity = "low"
        if jobs_last_year >= 20 or active_jobs >= 10:
            hiring_activity = "high"
        elif jobs_last_year >= 5 or active_jobs >= 3:
            hiring_activity = "medium"

        return {
            "total_jobs_posted": total_jobs or 0,
            "active_jobs": active_jobs or 0,
            "jobs_posted_last_30_days": recent_jobs or 0,
            "jobs_posted_last_12_months": jobs_last_year or 0,
            "total_applications_received": total_applications or 0,
            "average_applications_per_job": avg_applications,
            "total_job_likes": total_likes or 0,
            "total_job_shares": total_shares or 0,
            "hiring_activity_level": hiring_activity
        }

    @error_handler
    async def search_company_jobs(self, company_id: str, query: str = "", category_id: str = "",
                                  limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Search jobs within a specific company
        
        Args:
            company_id: Company ID
            query: Search query for job title/description
            category_id: Filter by job category
            limit: Number of jobs to return
            offset: Offset for pagination
            
        Returns:
            Dict with search results
        """
        if not company_id or not company_id.strip():
            return {"success": False, "message": "Invalid company ID", "code": 400}

        with self.get_session() as session:
            try:
                # Verify company exists
                company_exists = session.query(CompanyORM).filter_by(company_id=company_id).first()
                if not company_exists:
                    return {"success": False, "message": "Company not found", "code": 404}

                # Build query
                current_time = datetime.now(timezone.utc)

                jobs_query = session.query(JobsORM).filter(
                    and_(
                        JobsORM.company_id == company_id,
                        JobsORM.status == 'active',
                        JobsORM.expires_at > current_time
                    )
                )

                # Add search filters
                if query and query.strip():
                    search_term = f"%{query.strip()}%"
                    jobs_query = jobs_query.filter(
                        JobsORM.title.ilike(search_term) |
                        JobsORM.description.ilike(search_term)
                    )

                if category_id and category_id.strip():
                    jobs_query = jobs_query.filter(JobsORM.category_id == category_id)

                # Get total count
                total_count = jobs_query.count()

                # Apply pagination and ordering
                jobs = (
                    jobs_query
                    .order_by(desc(JobsORM.posted_at))
                    .offset(offset)
                    .limit(limit)
                    .all()
                )

                # Format results
                jobs_data = []
                for job_orm in jobs:
                    job_data = job_orm.to_dict()

                    # Add engagement metrics
                    like_count = session.query(func.count(JobLikeORM.like_id)).filter_by(job_id=job_orm.job_id).scalar()
                    share_count = session.query(func.count(JobShareORM.share_id)).filter_by(
                        job_id=job_orm.job_id).scalar()

                    job_data.update({
                        "like_count": like_count or 0,
                        "share_count": share_count or 0
                    })

                    jobs_data.append(job_data)

                return {
                    "success": True,
                    "data": {
                        "jobs": jobs_data,
                        "total_count": total_count,
                        "query": query,
                        "category_id": category_id,
                        "limit": limit,
                        "offset": offset
                    }
                }

            except Exception as e:
                self.logger.error(f"Error searching company jobs: {e}")
                return {"success": False, "message": "Internal server error", "code": 500}

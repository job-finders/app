"""
Job Actions Controller

Handles job interaction actions like liking, saving, and sharing jobs.
Extends the existing jobs workflow functionality.
"""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from flask import Flask
from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from src.controllers.controller import Controllers, error_handler
from src.database.models import (
    JobLike, JobShare, JobActionsState, JobLikeRequest, JobSaveRequest,
    JobShareRequest, JobActionsResponse, ShareMethodEnum, SavedJob
)
from src.database import (
    JobLikeORM, JobShareORM, JobsORM, JobSeekerProfileORM, SavedJobORM
)
from src.cache.job_actions_cache import job_actions_cache


class JobActionsController(Controllers):
    """Controller for job interaction actions"""

    def __init__(self, factory):
        super().__init__(factory)
        self.analytics_service = None

    def init_app(self, app: Flask):
        super().init_app(app=app)
        # Initialize analytics service
        from src.utils.route_helpers import get_controller
        self.analytics_service = get_controller('job_actions_analytics')

        # Initialize monitoring service
        from src.utils.job_actions_monitoring import job_actions_monitor
        job_actions_monitor.start_monitoring()

    @error_handler
    async def like_job(self, user_id: str, job_id: str) -> Dict[str, Any]:
        """
        Like a job for a user
        
        Args:
            user_id: JobSeeker profile user_uid
            job_id: Job ID to like
            
        Returns:
            Dict with success status and data
        """
        if not self._validate_user_and_job_ids(user_id, job_id):
            return {"success": False, "message": "Invalid user or job ID", "code": 400}

        with self.get_session() as session:
            # Check if user and job exist
            user_exists = session.query(JobSeekerProfileORM).filter_by(user_uid=user_id).first()
            job_exists = session.query(JobsORM).filter_by(job_id=job_id).first()

            if not user_exists:
                return {"success": False, "message": "User not found", "code": 404}
            if not job_exists:
                return {"success": False, "message": "Job not found", "code": 404}

            # Check if already liked
            existing_like = session.query(JobLikeORM).filter_by(
                user_id=user_id, job_id=job_id
            ).first()

            if existing_like:
                return {"success": False, "message": "Job already liked", "code": 409}

            try:
                # Create new like
                job_like = JobLike(user_id=user_id, job_id=job_id)
                like_orm = JobLikeORM(**job_like.model_dump())

                session.add(like_orm)
                session.commit()

                # Get updated like count
                like_count = session.query(func.count(JobLikeORM.like_id)).filter_by(job_id=job_id).scalar()

                # Invalidate related cache
                job_actions_cache.invalidate_user_action_cache(user_id, job_id)

                # Track analytics event
                if self.analytics_service:
                    await self.analytics_service.track_job_action(
                        event_type="job_like",
                        user_id=user_id,
                        job_id=job_id,
                        metadata={"like_id": like_orm.like_id}
                    )

                self.logger.info(f"User {user_id} liked job {job_id}")

                return {
                    "success": True,
                    "message": "Job liked successfully",
                    "data": {
                        "like_id": like_orm.like_id,
                        "like_count": like_count
                    }
                }

            except IntegrityError as e:
                session.rollback()
                self.logger.error(f"Integrity error liking job: {e}")
                return {"success": False, "message": "Database constraint violation", "code": 409}
            except Exception as e:
                session.rollback()
                self.logger.error(f"Error liking job: {e}")
                return {"success": False, "message": "Internal server error", "code": 500}

    @error_handler
    async def unlike_job(self, user_id: str, job_id: str) -> Dict[str, Any]:
        """
        Remove a like from a job
        
        Args:
            user_id: JobSeeker profile user_uid
            job_id: Job ID to unlike
            
        Returns:
            Dict with success status and data
        """
        if not self._validate_user_and_job_ids(user_id, job_id):
            return {"success": False, "message": "Invalid user or job ID", "code": 400}

        with self.get_session() as session:
            # Find existing like
            existing_like = session.query(JobLikeORM).filter_by(
                user_id=user_id, job_id=job_id
            ).first()

            if not existing_like:
                return {"success": False, "message": "Like not found", "code": 404}

            try:
                session.delete(existing_like)
                session.commit()

                # Get updated like count
                like_count = session.query(func.count(JobLikeORM.like_id)).filter_by(job_id=job_id).scalar()

                # Invalidate related cache
                job_actions_cache.invalidate_user_action_cache(user_id, job_id)

                # Track analytics event
                if self.analytics_service:
                    await self.analytics_service.track_job_action(
                        event_type="job_unlike",
                        user_id=user_id,
                        job_id=job_id,
                        metadata={"like_count": like_count}
                    )

                self.logger.info(f"User {user_id} unliked job {job_id}")

                return {
                    "success": True,
                    "message": "Job unliked successfully",
                    "data": {
                        "like_count": like_count
                    }
                }

            except Exception as e:
                session.rollback()
                self.logger.error(f"Error unliking job: {e}")
                return {"success": False, "message": "Internal server error", "code": 500}

    @error_handler
    async def save_job(self, user_id: str, job_id: str) -> Dict[str, Any]:
        """
        Save a job for a user (extends existing SavedJob functionality)
        
        Args:
            user_id: JobSeeker profile user_uid
            job_id: Job ID to save
            
        Returns:
            Dict with success status and data
        """
        if not self._validate_user_and_job_ids(user_id, job_id):
            return {"success": False, "message": "Invalid user or job ID", "code": 400}

        with self.get_session() as session:
            # Check if user and job exist
            user_exists = session.query(JobSeekerProfileORM).filter_by(user_uid=user_id).first()
            job_exists = session.query(JobsORM).filter_by(job_id=job_id).first()

            if not user_exists:
                return {"success": False, "message": "User not found", "code": 404}
            if not job_exists:
                return {"success": False, "message": "Job not found", "code": 404}

            # Check if already saved
            existing_save = session.query(SavedJobORM).filter_by(
                user_id=user_id, job_id=job_id
            ).first()

            if existing_save:
                return {"success": False, "message": "Job already saved", "code": 409}

            try:
                # Create new saved job
                saved_job = SavedJob(user_id=user_id, job_id=job_id)
                saved_job_orm = SavedJobORM(**saved_job.model_dump())

                session.add(saved_job_orm)
                session.commit()

                # Invalidate related cache
                job_actions_cache.invalidate_job_actions_state(user_id, job_id)
                job_actions_cache.invalidate_user_liked_jobs(user_id)

                # Track analytics event
                if self.analytics_service:
                    await self.analytics_service.track_job_action(
                        event_type="job_save",
                        user_id=user_id,
                        job_id=job_id,
                        metadata={"saved_job_id": saved_job_orm.saved_job_id}
                    )

                self.logger.info(f"User {user_id} saved job {job_id}")

                return {
                    "success": True,
                    "message": "Job saved successfully",
                    "data": {
                        "saved_job_id": saved_job_orm.saved_job_id
                    }
                }

            except IntegrityError as e:
                session.rollback()
                self.logger.error(f"Integrity error saving job: {e}")
                return {"success": False, "message": "Database constraint violation", "code": 409}
            except Exception as e:
                session.rollback()
                self.logger.error(f"Error saving job: {e}")
                return {"success": False, "message": "Internal server error", "code": 500}

    @error_handler
    async def unsave_job(self, user_id: str, job_id: str) -> Dict[str, Any]:
        """
        Remove a saved job
        
        Args:
            user_id: JobSeeker profile user_uid
            job_id: Job ID to unsave
            
        Returns:
            Dict with success status and data
        """
        if not self._validate_user_and_job_ids(user_id, job_id):
            return {"success": False, "message": "Invalid user or job ID", "code": 400}

        with self.get_session() as session:
            # Find existing saved job
            existing_save = session.query(SavedJobORM).filter_by(
                user_id=user_id, job_id=job_id
            ).first()

            if not existing_save:
                return {"success": False, "message": "Saved job not found", "code": 404}

            try:
                session.delete(existing_save)
                session.commit()

                # Track analytics event
                if self.analytics_service:
                    await self.analytics_service.track_job_action(
                        event_type="job_unsave",
                        user_id=user_id,
                        job_id=job_id,
                        metadata={}
                    )

                self.logger.info(f"User {user_id} unsaved job {job_id}")

                return {
                    "success": True,
                    "message": "Job unsaved successfully"
                }

            except Exception as e:
                session.rollback()
                self.logger.error(f"Error unsaving job: {e}")
                return {"success": False, "message": "Internal server error", "code": 500}

    @error_handler
    async def share_job(self, user_id: Optional[str], job_id: str, share_method: str) -> Dict[str, Any]:
        """
        Share a job (allows anonymous sharing)
        
        Args:
            user_id: JobSeeker profile user_uid (optional for anonymous sharing)
            job_id: Job ID to share
            share_method: Method used to share (email, linkedin, etc.)
            
        Returns:
            Dict with success status and data
        """
        if not job_id or not job_id.strip():
            return {"success": False, "message": "Invalid job ID", "code": 400}

        # Validate share method
        try:
            share_method_enum = ShareMethodEnum(share_method)
        except ValueError:
            return {"success": False, "message": "Invalid share method", "code": 400}

        with self.get_session() as session:
            # Check if job exists
            job_exists = session.query(JobsORM).filter_by(job_id=job_id).first()
            if not job_exists:
                return {"success": False, "message": "Job not found", "code": 404}

            # If user_id provided, check if user exists
            if user_id:
                user_exists = session.query(JobSeekerProfileORM).filter_by(user_uid=user_id).first()
                if not user_exists:
                    return {"success": False, "message": "User not found", "code": 404}

            try:
                # Generate referral code if user is authenticated
                referral_code = None
                if user_id:
                    referral_code = JobShare.generate_referral_code(user_id, job_id)

                # Create job share
                job_share = JobShare(
                    user_id=user_id,
                    job_id=job_id,
                    share_method=share_method_enum,
                    referral_code=referral_code
                )
                share_orm = JobShareORM(**job_share.model_dump())

                session.add(share_orm)
                session.commit()

                # Get updated share count
                share_count = session.query(func.count(JobShareORM.share_id)).filter_by(job_id=job_id).scalar()

                # Invalidate engagement cache
                job_actions_cache.invalidate_job_engagement_stats(job_id)
                if user_id:
                    job_actions_cache.invalidate_job_actions_state(user_id, job_id)

                # Track analytics event
                if self.analytics_service:
                    await self.analytics_service.track_job_action(
                        event_type="job_share",
                        user_id=user_id,
                        job_id=job_id,
                        metadata={
                            "share_method": share_method,
                            "share_id": share_orm.share_id,
                            "referral_code": referral_code,
                            "is_anonymous": user_id is None
                        }
                    )

                self.logger.info(f"Job {job_id} shared via {share_method} by user {user_id or 'anonymous'}")

                return {
                    "success": True,
                    "message": "Job shared successfully",
                    "data": {
                        "share_id": share_orm.share_id,
                        "referral_code": referral_code,
                        "share_count": share_count
                    }
                }

            except Exception as e:
                session.rollback()
                self.logger.error(f"Error sharing job: {e}")
                return {"success": False, "message": "Internal server error", "code": 500}

    @error_handler
    async def get_job_actions_state(self, user_id: str, job_id: str) -> Dict[str, Any]:
        """
        Get the current state of job actions for a user and job
        
        Args:
            user_id: JobSeeker profile user_uid
            job_id: Job ID
            
        Returns:
            Dict with job actions state
        """
        if not self._validate_user_and_job_ids(user_id, job_id):
            return {"success": False, "message": "Invalid user or job ID", "code": 400}

        # Try to get from cache first
        cached_state = job_actions_cache.get_job_actions_state(user_id, job_id)
        if cached_state:
            return {
                "success": True,
                "data": cached_state
            }

        with self.get_session() as session:
            try:
                # Check if user has liked the job
                user_has_liked = session.query(JobLikeORM).filter_by(
                    user_id=user_id, job_id=job_id
                ).first() is not None

                # Check if user has saved the job
                user_has_saved = session.query(SavedJobORM).filter_by(
                    user_id=user_id, job_id=job_id
                ).first() is not None

                # Get total like count
                like_count = session.query(func.count(JobLikeORM.like_id)).filter_by(job_id=job_id).scalar()

                # Get total share count
                share_count = session.query(func.count(JobShareORM.share_id)).filter_by(job_id=job_id).scalar()

                # Create actions state
                actions_state = JobActionsState(
                    job_id=job_id,
                    user_has_liked=user_has_liked,
                    user_has_saved=user_has_saved,
                    like_count=like_count or 0,
                    share_count=share_count or 0
                )

                state_dict = actions_state.to_dict()

                # Cache the result
                job_actions_cache.set_job_actions_state(user_id, job_id, state_dict)

                return {
                    "success": True,
                    "data": state_dict
                }

            except Exception as e:
                self.logger.error(f"Error getting job actions state: {e}")
                return {"success": False, "message": "Internal server error", "code": 500}

    @error_handler
    async def get_user_liked_jobs(self, user_id: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Get jobs liked by a user
        
        Args:
            user_id: JobSeeker profile user_uid
            limit: Number of jobs to return
            offset: Offset for pagination
            
        Returns:
            Dict with liked jobs data
        """
        if not user_id or not user_id.strip():
            return {"success": False, "message": "Invalid user ID", "code": 400}

        with self.get_session() as session:
            try:
                # Get liked jobs with job details
                liked_jobs_query = (
                    session.query(JobLikeORM)
                    .options(joinedload(JobLikeORM.job))
                    .filter_by(user_id=user_id)
                    .order_by(JobLikeORM.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                )

                liked_jobs = liked_jobs_query.all()

                # Get total count
                total_count = session.query(func.count(JobLikeORM.like_id)).filter_by(user_id=user_id).scalar()

                # Format response
                jobs_data = []
                for like in liked_jobs:
                    if like.job:
                        job_data = like.job.to_dict()
                        job_data['liked_at'] = like.created_at.replace(tzinfo=timezone.utc).isoformat()
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
                self.logger.error(f"Error getting user liked jobs: {e}")
                return {"success": False, "message": "Internal server error", "code": 500}

    def _validate_user_and_job_ids(self, user_id: str, job_id: str) -> bool:
        """Validate user_id and job_id are not empty"""
        return bool(user_id and user_id.strip() and job_id and job_id.strip())

    @error_handler
    async def get_user_saved_jobs(self, user_id: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Get jobs saved by a user with caching
        
        Args:
            user_id: JobSeeker profile user_uid
            limit: Number of jobs to return
            offset: Offset for pagination
            
        Returns:
            Dict with saved jobs data
        """
        if not user_id or not user_id.strip():
            return {"success": False, "message": "Invalid user ID", "code": 400}

        # Try cache first
        cached = job_actions_cache.get_user_saved_jobs(user_id, limit, offset)
        if cached:
            return cached

        with self.get_session() as session:
            try:
                # Get saved jobs with job details
                saved_jobs_query = (
                    session.query(SavedJobORM)
                    .options(joinedload(SavedJobORM.job))
                    .filter_by(user_id=user_id)
                    .order_by(SavedJobORM.saved_at.desc())
                    .offset(offset)
                    .limit(limit)
                )

                saved_jobs = saved_jobs_query.all()

                # Get total count
                total_count = session.query(func.count(SavedJobORM.saved_job_id)).filter_by(user_id=user_id).scalar()

                # Format response
                jobs_data = []
                for saved in saved_jobs:
                    if saved.job:
                        job_data = saved.job.to_dict()
                        job_data['saved_at'] = saved.saved_at.replace(tzinfo=timezone.utc).isoformat()
                        job_data['saved_job_id'] = saved.saved_job_id
                        jobs_data.append(job_data)

                response = {
                    "success": True,
                    "data": {
                        "jobs": jobs_data,
                        "total_count": total_count or 0,
                        "limit": limit,
                        "offset": offset
                    }
                }

                # Cache the result
                job_actions_cache.set_user_saved_jobs(user_id, response, limit, offset)
                return response

            except Exception as e:
                self.logger.error(f"Error getting user saved jobs: {e}")
                return {"success": False, "message": "Internal server error", "code": 500}

    @error_handler
    async def get_job_engagement_stats(self, job_id: str) -> Dict[str, Any]:
        """
        Get engagement statistics for a job
        
        Args:
            job_id: Job ID
            
        Returns:
            Dict with engagement statistics
        """
        if not job_id or not job_id.strip():
            return {"success": False, "message": "Invalid job ID", "code": 400}

        with self.get_session() as session:
            try:
                # Get like count
                like_count = session.query(func.count(JobLikeORM.like_id)).filter_by(job_id=job_id).scalar()

                # Get share count by method
                share_stats = (
                    session.query(JobShareORM.share_method, func.count(JobShareORM.share_id))
                    .filter_by(job_id=job_id)
                    .group_by(JobShareORM.share_method)
                    .all()
                )

                # Get recent activity (last 7 days)
                from datetime import timedelta
                week_ago = datetime.now(timezone.utc) - timedelta(days=7)

                recent_likes = session.query(func.count(JobLikeORM.like_id)).filter(
                    and_(JobLikeORM.job_id == job_id, JobLikeORM.created_at >= week_ago)
                ).scalar()

                recent_shares = session.query(func.count(JobShareORM.share_id)).filter(
                    and_(JobShareORM.job_id == job_id, JobShareORM.shared_at >= week_ago)
                ).scalar()

                # Format share stats
                share_by_method = {method: count for method, count in share_stats}
                total_shares = sum(share_by_method.values())

                return {
                    "success": True,
                    "data": {
                        "job_id": job_id,
                        "like_count": like_count or 0,
                        "share_count": total_shares,
                        "share_by_method": share_by_method,
                        "recent_activity": {
                            "likes_last_7_days": recent_likes or 0,
                            "shares_last_7_days": recent_shares or 0
                        }
                    }
                }

            except Exception as e:
                self.logger.error(f"Error getting job engagement stats: {e}")
                return {"success": False, "message": "Internal server error", "code": 500}

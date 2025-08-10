"""
Job Application Controller with Referral Tracking Integration
"""

from typing import Optional, Dict
from datetime import datetime

from flask import Flask
from sqlalchemy import and_
from sqlalchemy.orm import joinedload

from src.controllers.controller import Controllers, error_handler
from src.database.models import JobApplication, JobApplicationORM
from src.services.referral_tracking import ReferralTrackingService


class JobApplicationsController(Controllers):
    """Controller for job applications with referral tracking"""

    def __init__(self, factory):
        super().__init__(factory)
        self.referral_service = ReferralTrackingService()

    def init_app(self, app: Flask):
        super().init_app(app=app)

    @error_handler
    async def create_application(
            self,
            user_id: str,
            job_id: str,
            application_data: Dict,
            referral_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new job application with optional referral tracking
        
        Args:
            user_id: Applicant user ID
            job_id: Job being applied to
            application_data: Application form data
            referral_code: Optional referral code if application came from a referral
            
        Returns:
            Dict with application result
        """
        with self.get_session() as session:
            # Create application
            application = JobApplicationORM(
                user_id=user_id,
                job_id=job_id,
                **application_data
            )
            session.add(application)
            session.commit()

            # If referral code provided, link to application
            if referral_code:
                await self._link_referral_to_application(referral_code, application.application_id)

            return {
                "success": True,
                "data": {
                    "application_id": application.application_id,
                    "referral_linked": referral_code is not None
                }
            }

    async def _link_referral_to_application(self, referral_code: str, application_id: str) -> None:
        """
        Link a referral to an application if valid
        
        Args:
            referral_code: Referral code from share link
            application_id: ID of new application
            
        Raises:
            ValueError if referral is invalid
        """
        referral = await self.referral_service.get_referral_by_code(referral_code)
        if not referral:
            raise ValueError("Invalid referral code")

        await self.referral_service.update_referral_application(
            str(referral.referral_id),
            application_id
        )

    @error_handler
    async def update_application_status(
            self,
            application_id: str,
            status: str,
            notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update application status and track referral progress if applicable
        
        Args:
            application_id: Application to update
            status: New status
            notes: Optional notes
            
        Returns:
            Dict with update result
        """
        with self.get_session() as session:
            app = session.query(JobApplicationORM) \
                .options(joinedload(JobApplicationORM.referral)) \
                .filter_by(application_id=application_id) \
                .first()

            if not app:
                return {"success": False, "message": "Application not found", "code": 404}

            # Update status
            app.status = status
            if notes:
                app.notes = notes

            # If application has a referral, update referral status
            if app.referral:
                referral_status = self._map_application_status_to_referral_status(status)
                if referral_status:
                    await self.referral_service.update_referral_status(
                        str(app.referral.referral_id),
                        referral_status
                    )

            session.commit()
            return {"success": True}

    def _map_application_status_to_referral_status(self, app_status: str) -> Optional[str]:
        """
        Map application status to corresponding referral status
        
        Args:
            app_status: Application status
            
        Returns:
            Corresponding referral status or None if no mapping
        """
        status_map = {
            "interviewing": "interviewed",
            "hired": "hired",
            "rejected": "rejected"
        }
        return status_map.get(app_status.lower())

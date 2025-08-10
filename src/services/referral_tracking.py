"""
Referral Tracking Service
Handles all referral tracking and bonus calculation logic
"""

from datetime import datetime
from typing import Optional, List, Dict
from uuid import uuid4

import sqlalchemy as sa
from src.database import get_session
from src.database.models import JobReferralORM, JobReferral, ReferralStatus
from src.database.models.jobseeker_profile import JobSeekerProfileORM
from src.utils.route_helpers import get_controller


class ReferralTrackingService:
    """Service for managing job referral tracking"""

    def __init__(self):
        self.job_controller = get_controller('jobs')
        self.profile_controller = get_controller('job_seeker_profile')

    async def create_referral(
            self,
            job_id: str,
            referrer_id: str,
            referred_email: str,
            referral_code: str
    ) -> JobReferral:
        """Create a new job referral record"""
        with get_session() as session:
            referral = JobReferralORM(
                referral_id=uuid4(),
                job_id=job_id,
                referrer_id=referrer_id,
                referred_email=referred_email,
                referral_code=referral_code,
                shared_at=datetime.utcnow()
            )

            session.add(referral)
            session.commit()

            return JobReferral.model_validate(referral)

    async def update_referral_application(
            self,
            referral_id: str,
            application_id: str
    ) -> JobReferral:
        """Update referral with application info when referred candidate applies"""
        with get_session() as session:
            referral = session.query(JobReferralORM).filter_by(referral_id=referral_id).first()
            if not referral:
                raise ValueError("Referral not found")

            referral.application_id = application_id
            referral.application_date = datetime.utcnow()
            referral.status = ReferralStatus.APPLIED

            session.commit()
            return JobReferral.model_validate(referral)

    async def update_referral_status(
            self,
            referral_id: str,
            status: ReferralStatus
    ) -> JobReferral:
        """Update referral status (interviewed, hired, etc)"""
        with get_session() as session:
            referral = session.query(JobReferralORM).filter_by(referral_id=referral_id).first()
            if not referral:
                raise ValueError("Referral not found")

            referral.status = status

            # Award bonus if hired
            if status == ReferralStatus.HIRED:
                referral.bonus_awarded = await self._calculate_referral_bonus(referral.job_id)

                # Update referrer's profile stats
                referrer = session.query(JobSeekerProfileORM).filter_by(user_uid=referral.referrer_id).first()
                if referrer:
                    referrer.referral_count += 1
                    referrer.referral_bonus_earned += referral.bonus_awarded

            session.commit()
            return JobReferral.model_validate(referral)

    async def _calculate_referral_bonus(self, job_id: str) -> float:
        """Calculate referral bonus amount based on job"""
        # TODO: Implement actual bonus calculation logic
        # This could be based on job salary, position level, etc
        return 500.0  # Placeholder flat rate

    async def get_referrals_by_referrer(
            self,
            referrer_id: str,
            status: Optional[ReferralStatus] = None
    ) -> List[JobReferral]:
        """Get all referrals made by a user, optionally filtered by status"""
        with get_session() as session:
            query = session.query(JobReferralORM).filter_by(referrer_id=referrer_id)

            if status:
                query = query.filter_by(status=status)

            referrals = query.all()
            return [JobReferral.model_validate(r) for r in referrals]

    async def get_referral_by_code(self, referral_code: str) -> Optional[JobReferral]:
        """Get referral by its unique code"""
        with get_session() as session:
            referral = session.query(JobReferralORM).filter_by(referral_code=referral_code).first()
            return JobReferral.model_validate(referral) if referral else None

    async def get_referral_stats(self, referrer_id: str) -> Dict[str, int]:
        """Get statistics about a user's referrals"""
        with get_session() as session:
            stats = {
                'total': session.query(JobReferralORM)
                .filter_by(referrer_id=referrer_id)
                .count(),
                'pending': session.query(JobReferralORM)
                .filter_by(referrer_id=referrer_id, status=ReferralStatus.PENDING)
                .count(),
                'applied': session.query(JobReferralORM)
                .filter_by(referrer_id=referrer_id, status=ReferralStatus.APPLIED)
                .count(),
                'hired': session.query(JobReferralORM)
                .filter_by(referrer_id=referrer_id, status=ReferralStatus.HIRED)
                .count(),
                'bonus_earned': session.query(JobReferralORM)
                                .filter_by(referrer_id=referrer_id)
                                .with_entities(sa.func.sum(JobReferralORM.bonus_awarded))
                                .scalar() or 0.0
            }
            return stats

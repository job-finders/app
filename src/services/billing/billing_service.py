import asyncio
from datetime import datetime, timedelta, timezone
from typing import Callable

from src.database.models.billing import CompanyBillingProfile, BillingPlan
from src.database.sql.billing_sql import CompanyBillingProfileORM, BillingPlanORM
from src.services.billing.schemas_interfaces import BillingServiceInterface


class BillingService(BillingServiceInterface):
    """
    Handles all billing plan management: subscription start, stop, trial logic, renewals, grace periods, etc.
    """

    def __init__(self, session_factory, billing_events):
        super().__init__()
        self.session_factory = session_factory
        self.trial_period_days = 14  # Default trial period length
        self.billing_events = billing_events  # Placeholder for billing events service
        self.__interface_map: dict[str, Callable] = {
            "interface_schema": self._interface_schema,
            "describe_actions": self._describe_actions,
            "start_trial": self._start_trial,
            "expire_trial": self._expire_trial,
            "look_up_plan": self._look_up_plan,
            "list_all_billing_plans": self._all_billing_plans,
            "update_subscription_state": self._update_subscription_state,
            "update_all_subscription_states": self._update_all_subscription_states,
            "get_billing_profile": self._get_billing_profile,
            'create_billing_profile': self._create_billing_profile,
            "apply_subscription": self._apply_subscription,
        }

    async def _look_up_plan(self, plan_id: str) -> CompanyBillingProfile | None:
        """Returns the billing plan details for a given plan_id"""
        with self.session_factory() as session:
            plan = session.query(CompanyBillingProfileORM).filter_by(plan_id=plan_id).first()
            if not plan:
                return None
            return CompanyBillingProfile(**plan.to_dict())

    async def _all_billing_plans(self):
        """returns all billing plans"""
        with self.session_factory() as session:
            billing_plams_orm_list = session.query(BillingPlanORM).all()
            return [BillingPlan(**plan_orm.to_dict()) for plan_orm in billing_plams_orm_list]

    async def _expire_trial(self, company_id: str) -> CompanyBillingProfile:
        with self.session_factory() as session:
            profile_orm = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()
            profile = CompanyBillingProfile(**profile_orm.to_dict()) if profile_orm else None
            if profile and profile.is_trial_valid:
                profile_orm.trial_active = False
                await self.billing_events.execute("record_event", company_id=company_id, type="trial_ended",event_metadata={"reason": "expired"})

                session.commit()
            return CompanyBillingProfile(**profile.to_dict())

    async def _start_trial(self, company_id: str) -> CompanyBillingProfile:
        """Start a trial for a company (if not already active)."""
        with self.session_factory() as session:
            profile = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()

            if not profile:
                # If profile doesn't exist, create a fresh one with trial enabled
                profile = CompanyBillingProfileORM(
                    company_id=company_id,
                    trial_active=True,
                    trial_end_date=datetime.now(timezone.utc).date() + timedelta(days=self.trial_period_days),
                )
                await self.billing_events.execute("record_event",
                                                  company_id=company_id,
                                                  type="trial_profile_created",
                                                  metadata={"trigger": "subscription_payment"})
                session.add(profile)

            else:
                # If trial already active or previously used, don't reassign
                if profile.trial_active or profile.trial_end_date:
                    return CompanyBillingProfile(**profile.to_dict())

                profile.trial_active = True
                profile.trial_end_date = datetime.utcnow().date() + timedelta(days=14)
            await self.billing_events.execute("record_event", company_id=company_id, type="trial_started"
                                              ,event_metadata={"duration_days": str(self.trial_period_days)})

            session.commit()
            return CompanyBillingProfile(**profile.to_dict())

    async def _update_all_subscription_states(self):
        """
            cron job to update all company subscriptions
            for all companies with subscriptions update all subscriptions.
        """
        with self.session_factory() as session:
            company_ids = session.query(CompanyBillingProfileORM.company_id).all()
            company_ids = [c[0] for c in company_ids]
            tasks = [self._update_subscription_state(company_id=company_id) for company_id in company_ids]
            return await asyncio.gather(*tasks)

    async def _update_subscription_state(self, company_id: str) -> CompanyBillingProfile | None:
        """
        Updates subscription status:
        - Ends trial if expired
        - Handles subscription expiration
        - Applies grace periods
        - Can be triggered via CRON or login
        """
        today = datetime.now(timezone.utc).date()

        with self.session_factory() as session:
            profile_orm = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()

            if not profile_orm:
                return None

            events_to_add = []
            profile = CompanyBillingProfile(**profile_orm.to_dict())
            # 1. Handle expired trial
            if profile.is_trial_valid:
                profile_orm.trial_active = False
                await self.billing_events.execute("record_event", company_id=company_id, type="trial_ended",
                                                  event_metadata={"reason": "expired", "auto_check": "true"})

            # 2. Check if subscription has ended
            if profile.is_active_subscription:
                # Grace logic (example: 7-day grace period)
                if profile.grace_period_ended:
                    profile_orm.is_payment_overdue = True
                else:
                    profile_orm.is_payment_overdue = True
                    profile.auto_renew = False  # Hard expiry
                    await self.billing_events.execute("record_event", company_id=company_id, type="subscription_cancelled",
                                                      event_metadata={"reason": "grace_period_expired"})

            if events_to_add:
                session.add_all(events_to_add)

            session.commit()
            return CompanyBillingProfile(**profile.to_dict())

    async def _create_billing_profile(self, company_id: str, plan_id: str):
        """

        :param company_id:
        :param plan_id:
        :return:
        """
        with self.session_factory() as session:
            billing_profile_orm = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()
            if billing_profile_orm:
                return None

            billing_plan: BillingPlanORM = session.query(BillingPlanORM).filter_by(plan_id=plan_id).first()
            today = datetime.now(timezone.utc).date()
            subscription_end = today + timedelta(days=billing_plan.duration_days)
            if not billing_plan.is_trial:
                billing_profile_orm = CompanyBillingProfile(company_id=company_id,
                                                        current_plan_id=plan_id,
                                                        subscription_start=today, subscription_end=subscription_end,
                                                        trial_active=False)
                session.add(billing_profile_orm)

                return CompanyBillingProfile(**billing_profile_orm.to_dict())
            else:
                is_trial = await self._start_trial(company_id=company_id)
            return None



    async def _get_billing_profile(self, company_id: str) -> CompanyBillingProfile | None:
        """

        :param company_id:
        :return:
        """
        with self.session_factory() as session:
            profile = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()
            if not profile:
                return None
            return CompanyBillingProfile(**profile.to_dict())

    async def _apply_subscription(self, company_id: str, plan_id: str,
                                  duration_days: int = 30) -> CompanyBillingProfile:
        """
        Apply a new active subscription to the company. Cancels trial if active.

        Args:
            company_id (str): The ID of the company.
            plan_id (str): The ID of the plan to apply.
            duration_days (int): Subscription duration (defaults to 30 days).

        Returns:
            CompanyBillingProfile: The updated company billing profile.

        Raises:
            ValueError: If the company profile or plan is not found.
        """
        now = datetime.now(timezone.utc)
        subscription_end = now.date() + timedelta(days=duration_days)

        with self.session_factory() as session:
            # Fetch the profile and validate
            profile_orm = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()
            if not profile_orm:
                # Create a new profile with subscription defaults
                profile_orm = CompanyBillingProfileORM(
                    company_id=company_id,
                    current_plan_id=plan_id,
                    subscription_start=datetime.now(timezone.utc).date(),
                    subscription_end=(datetime.now(timezone.utc).date() + timedelta(days=duration_days))
                )
                session.add(profile_orm)

                await self.billing_events.execute("record_event", company_id=company_id, type="billing_profile_created",
                                                  metadata={"trigger": "subscription_payment"})



            billing_plan = session.query(BillingPlanORM).filter_by(plan_id=plan_id).first()
            if not billing_plan:
                raise ValueError(f"Subscription plan '{plan_id}' not found.")

            # End trial if active
            if profile_orm.trial_active:
                profile_orm.trial_active = False
                await self.billing_events.execute("record_event", company_id=company_id, type="trial_ended",
                                                  event_metadata={"reason": "replaced_by_subscription"})

            # Apply new subscription
            profile_orm.plan_id = plan_id
            profile_orm.subscription_start =now
            profile_orm.subscription_end = subscription_end
            profile_orm.is_payment_overdue = False
            profile_orm.auto_renew = True

            # Create billing event
            await self.billing_events.execute("record_event", company_id=company_id, type="subscription_created",
                                              event_metadata={"plan_id": plan_id, "duration_days": duration_days, "subscription_end": str(subscription_end)})
            session.commit()

            return CompanyBillingProfile(**profile_orm.to_dict())

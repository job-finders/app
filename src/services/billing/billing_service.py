import asyncio
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional
import inspect
from src.database.models.billing import CompanyBillingProfile, BillingPlan
from src.database.sql.billing_sql import CompanyBillingProfileORM, BillingPlanORM
from src.services.billing.schemas_interfaces import BillingServiceInterface, BillingEventType
from src.utils.route_helpers import get_service


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
            "list_all_companies": self._list_all_companies,  # Added for cron service mock
            "list_all_billing_plans": self._all_billing_plans,
            "update_subscription_state": self._update_subscription_state,
            "update_all_subscription_states": self._update_all_subscription_states,
            "get_billing_profile": self._get_billing_profile,
            'create_billing_profile': self._create_billing_profile,
            "apply_subscription": self._apply_subscription,
            "expire_subscription": self._expire_subscription,  # Added for cron service usage
        }
        self.logger = get_service("logger")()(self.__class__.__name__)

    async def execute(self, action: str, *args, **kwargs):
        """
        Dynamically executes a method based on the provided action name.

        Args:
            action (str): The name of the method to execute (must be present in `_interface_schema`).
            *args: Positional arguments for the method.
            **kwargs: Keyword arguments for the method.

        Returns:
            Any: The result of the invoked method.

        Raises:
            ValueError: If the action does not exist in this service's schema
                        or if the found entry is not a callable method.
            RuntimeError: If an unexpected error occurs during the execution
                          of the target method.
        """
        try:
            method_to_execute = self.__interface_map[action]

            if method_to_execute is None:
                raise ValueError(f"Action '{action}' not found in {self.__class__.__name__}.")

            if inspect.iscoroutinefunction(method_to_execute):
                return await method_to_execute(*args, **kwargs)
            else:
                return method_to_execute(*args, **kwargs)

        # Catch specific exceptions that might be raised by the lookup or the method itself.
        except ValueError as e:
            # Re-raise the ValueError if it's one of the ones we explicitly raised.
            raise e

        except Exception as e:
            # Catch any other unexpected exceptions and wrap them in a RuntimeError.
            # Using 'from e' maintains the original exception's traceback, which is crucial for debugging.
            raise RuntimeError(f"Error executing action '{action}': {str(e)}") from e

    # Mock list_all_companies for cron service
    async def _list_all_companies(self) -> list[CompanyBillingProfile]:
        with self.session_factory() as session:
            companies_orm = session.query(CompanyBillingProfileORM).all()
            return [CompanyBillingProfile(**c.to_dict()) for c in companies_orm]

    async def _look_up_plan(self, plan_id: str) -> CompanyBillingProfile | None:
        """Returns the billing plan details for a given plan_id"""
        with self.session_factory() as session:
            plan = session.query(BillingPlanORM).filter_by(plan_id=plan_id).first()
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
            if profile and profile_orm.is_trial_valid:  # Check ORM's is_trial_valid
                profile_orm.trial_active = False
                await self.billing_events.execute("record_event", company_id=company_id,
                                                  type=BillingEventType.TRIAL_ENDED,
                                                  event_metadata={"reason": "expired"})  # Using Enum

                session.commit()
            return CompanyBillingProfile(**profile_orm.to_dict())  # Return updated ORM as model

    async def _start_trial(self, company_id: str) -> CompanyBillingProfile:
        """Start a trial for a company (if not already active)."""
        with self.session_factory() as session:
            profile_orm = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()

            if not profile_orm:
                # If profile doesn't exist, create a fresh one with trial enabled
                profile_orm = CompanyBillingProfileORM(
                    company_id=company_id,
                    trial_active=True,
                    trial_end_date=datetime.now(timezone.utc).date() + timedelta(days=self.trial_period_days),
                )
                await self.billing_events.execute("record_event",
                                                  company_id=company_id,
                                                  type=BillingEventType.TRIAL_PROFILE_CREATED,  # Using Enum
                                                  event_metadata={"trigger": "subscription_payment"})
                session.add(profile_orm)

            else:
                # If trial already active or previously used, don't reassign
                if profile_orm.trial_active or profile_orm.trial_end_date:  # Check ORM attributes
                    return CompanyBillingProfile(**profile_orm.to_dict())

                profile_orm.trial_active = True
                profile_orm.trial_end_date = datetime.now(timezone.utc).date() + timedelta(days=14)  # Use .date()
            await self.billing_events.execute("record_event", company_id=company_id,
                                              type=BillingEventType.TRIAL_STARTED,  # Using Enum
                                              event_metadata={"duration_days": str(self.trial_period_days)})

            session.commit()
            session.refresh(profile_orm)  # Refresh to get latest state after commit
            return CompanyBillingProfile(**profile_orm.to_dict())

    async def _update_all_subscription_states(self):
        """
            cron job to update all company subscriptions
            for all companies with subscriptions update all subscriptions.
        """
        self.logger.info("Started Update Service")
        with self.session_factory() as session:
            company_ids_orm = session.query(CompanyBillingProfileORM.company_id).all()
            company_ids = [c[0] for c in company_ids_orm] if company_ids_orm else []
            self.logger.info(f"Found {len(company_ids)} Companies to update subscription records for")
            tasks = [self._update_subscription_state(company_id=company_id) for company_id in
                     company_ids] if company_ids else []
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

            profile = CompanyBillingProfile(**profile_orm.to_dict())

            # 1. Handle expired trial - Moved to a dedicated expire_trial or check in cron
            # This logic should be handled by the _expire_trial method or _expire_subscription
            # if profile_orm.is_trial_valid and profile_orm.trial_end_date < today:
            #    profile_orm.trial_active = False
            #    await self.billing_events.execute("record_event", company_id=company_id, type=BillingEventType.TRIAL_ENDED,
            #                                      event_metadata={"reason": "expired", "auto_check": "true"})

            # 2. Check if subscription has ended and apply expiry/grace logic
            if profile.is_active_subscription_plan:
                # If subscription end date has passed, apply grace or expire
                if profile.subscription_end < today:
                    if profile.grace_period_ended:  # This property needs to be managed
                        # Subscription fully expired, no grace left
                        profile_orm.current_plan_id = None  # No active plan
                        profile_orm.subscription_start = None
                        profile_orm.subscription_end = None
                        profile_orm.is_payment_overdue = True  # Mark as overdue if it was for payment.
                        profile_orm.auto_renew = False  # Ensure it doesn't auto-renew
                        await self.billing_events.execute("record_event", company_id=company_id,
                                                          type=BillingEventType.SUBSCRIPTION_EXPIRED,  # Using Enum
                                                          event_metadata={"reason": "grace_period_expired",
                                                                          "auto_check": "true"})
                    else:
                        # Enter grace period (assuming grace_period_ended is set after grace)
                        # This logic needs to be robust, possibly setting a grace_end_date
                        # For simplicity, here we'll just mark as overdue and set auto_renew false if it passes the end date.
                        profile_orm.is_payment_overdue = True
                        profile_orm.auto_renew = False
                        # Consider a specific event for entering grace period if needed

            session.commit()
            session.refresh(profile_orm)
            return CompanyBillingProfile(**profile_orm.to_dict())

    async def _expire_subscription(self, company_id: str) -> CompanyBillingProfile:
        """
        Explicitly expires a company's subscription. This might be called by cron for past-due subscriptions.
        """
        with self.session_factory() as session:
            profile_orm = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()
            if not profile_orm:
                raise ValueError(f"Billing profile for company {company_id} not found.")

            # Assuming the logic means setting the current_plan_id to None
            # and marking it inactive or expired.
            # This method should ensure is_active_subscription_plan becomes False.
            if profile_orm.is_active_subscription_plan:  # Only expire if currently active
                profile_orm.current_plan_id = None
                profile_orm.subscription_start = None
                profile_orm.subscription_end = None
                profile_orm.is_payment_overdue = True  # Typically expired means payment overdue
                profile_orm.auto_renew = False

                # Record event for subscription expiration
                await self.billing_events.execute("record_event", company_id=company_id,
                                                  type=BillingEventType.SUBSCRIPTION_EXPIRED,  # Using Enum
                                                  event_metadata={"reason": "manual_or_cron_expiry"})
            session.commit()
            session.refresh(profile_orm)
            return CompanyBillingProfile(**profile_orm.to_dict())

    async def _create_billing_profile(self, company_id: str, plan_id: str) -> Optional[CompanyBillingProfile]:
        """
        Creates a new billing profile for a company.

        :param company_id: The ID of the company.
        :param plan_id: The ID of the initial billing plan.
        :return: The newly created CompanyBillingProfile, or None if it already exists.
        """
        with self.session_factory() as session:
            billing_profile_orm = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()
            if billing_profile_orm:
                self.logger.info(f"Billing profile for {company_id} already exists. Returning None.")
                return None

            billing_plan: BillingPlanORM = session.query(BillingPlanORM).filter_by(plan_id=plan_id).first()
            if not billing_plan:
                raise ValueError(f"Billing plan '{plan_id}' not found.")

            today = datetime.now(timezone.utc).date()

            # If the plan is a trial, use _start_trial
            if billing_plan.is_trial:
                self.logger.info(f"Creating billing profile for {company_id} with trial plan {plan_id}.")
                return await self._start_trial(company_id=company_id)
            else:
                # Create a non-trial profile
                subscription_end = today + timedelta(days=billing_plan.duration_days)
                billing_profile_orm = CompanyBillingProfileORM(
                    company_id=company_id,
                    current_plan_id=plan_id,
                    subscription_start=datetime.now(timezone.utc),  # Use datetime for consistency
                    subscription_end=datetime(subscription_end.year, subscription_end.month, subscription_end.day, 23,
                                              59, 59, tzinfo=timezone.utc),  # End of day
                    trial_active=False  # Explicitly false for non-trial
                )
                session.add(billing_profile_orm)

                # Record event for billing profile creation
                await self.billing_events.execute("record_event",
                                                  company_id=company_id,
                                                  type=BillingEventType.BILLING_PROFILE_CREATED,  # Using Enum
                                                  event_metadata={"trigger": "create_billing_profile",
                                                                  "plan_id": plan_id})
                session.commit()
                session.refresh(billing_profile_orm)
                self.logger.info(f"Billing profile created for {company_id} with plan {plan_id}.")
                return CompanyBillingProfile(**billing_profile_orm.to_dict())

    async def _get_billing_profile(self, company_id: str) -> CompanyBillingProfile | None:
        """
        Retrieves a company's billing profile.

        :param company_id: The ID of the company.
        :return: The CompanyBillingProfile if found, otherwise None.
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
            profile_orm = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()

            billing_plan = session.query(BillingPlanORM).filter_by(plan_id=plan_id).first()
            if not billing_plan:
                raise ValueError(f"Subscription plan '{plan_id}' not found.")

            if not profile_orm:
                # If profile doesn't exist, create it here with the subscription
                profile_orm = CompanyBillingProfileORM(
                    company_id=company_id,
                    current_plan_id=plan_id,
                    subscription_start=now,
                    subscription_end=datetime(subscription_end.year, subscription_end.month, subscription_end.day, 23,
                                              59, 59, tzinfo=timezone.utc),  # End of day
                    trial_active=False,  # New profile starting with subscription, not trial
                    is_payment_overdue=False,
                    auto_renew=True
                )
                session.add(profile_orm)
                self.logger.info(f"Created new profile for {company_id} while applying subscription.")
                await self.billing_events.execute("record_event", company_id=company_id,
                                                  type=BillingEventType.BILLING_PROFILE_CREATED,  # Using Enum
                                                  event_metadata={"trigger": "apply_subscription_new_profile"})
            else:
                # If profile exists, end trial if active
                if profile_orm.trial_active:
                    profile_orm.trial_active = False
                    self.logger.info(f"Trial ended for {company_id} due to subscription application.")
                    await self.billing_events.execute("record_event", company_id=company_id,
                                                      type=BillingEventType.TRIAL_ENDED,  # Using Enum
                                                      event_metadata={"reason": "replaced_by_subscription"})

                # Apply new subscription details to existing profile
                profile_orm.current_plan_id = plan_id
                profile_orm.subscription_start = now
                profile_orm.subscription_end = datetime(subscription_end.year, subscription_end.month,
                                                        subscription_end.day, 23, 59, 59,
                                                        tzinfo=timezone.utc)  # End of day
                profile_orm.is_payment_overdue = False
                profile_orm.auto_renew = True
                self.logger.info(f"Applied subscription {plan_id} to existing profile for {company_id}.")

            # Record subscription created/applied event
            await self.billing_events.execute("record_event", company_id=company_id,
                                              type=BillingEventType.SUBSCRIPTION_CREATED,  # Using Enum
                                              event_metadata={"plan_id": plan_id, "duration_days": duration_days,
                                                              "subscription_end": str(subscription_end)})
            session.commit()
            session.refresh(profile_orm)

            return CompanyBillingProfile(**profile_orm.to_dict())

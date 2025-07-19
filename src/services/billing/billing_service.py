# Standard Library
import asyncio
import inspect
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
from enum import Enum
from typing import Callable, Optional

# Domain Models
from src.database.models import CompanyBillingProfile, BillingPlan

# SQL Models
from src.database.sql.billing_sql import CompanyBillingProfileORM, BillingPlanORM

# Services
from src.services.billing.schemas_interfaces import BillingServiceInterface, BillingEventType

# Utilities
from src.utils.route_helpers import get_service

# Constants
from src.database.constants import utc_time

class BillingTiersEnum(Enum):
    Trial = "Trial"
    Starter = "Starter"
    Growth = "Growth"
    Professional = "Professional"
    Enterprise = "Enterprise"

    @classmethod
    def billing_iters(cls):
        return {
            "Trial": 0,
            "Starter": 1,
            "Growth": 2,
            "Professional": 3,
            "Enterprise": 4
        }

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
            "init_standard_billing_plans": self._init_standard_billing_plans
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
        """List of all company Billing Profiles"""
        with self.session_factory() as session:
            companies_orm = session.query(CompanyBillingProfileORM).all()
            return [CompanyBillingProfile(**c.to_dict()) for c in companies_orm] if companies_orm else []

    def _init_standard_billing_plans(self) -> list[BillingPlan]:
        """
        Creates a set of standard billing plans for the platform.

        Returns:
            List of BillingPlan instances ready for database insertion
        """
        standard_plans = [
            # Free Trial Plan
            BillingPlan(
                name=BillingTiersEnum.Trial.value,
                description="14-day free trial to test all features",
                price=Decimal("0.00"),
                is_active=True,
                is_trial=True,
                max_open_jobs=2,
                max_users=1,
                max_applicants_per_job=50,
                allow_priority_support=False,
                show_branding=True,
                sort_order=1,
                duration_days=7
            ),

            # Starter Plan
            BillingPlan(
                name=BillingTiersEnum.Starter.value,
                description="Perfect for small businesses and startups",
                price=Decimal("299.00"),
                is_active=True,
                is_featured=False,
                max_open_jobs=5,
                max_users=2,
                max_applicants_per_job=100,
                allow_priority_support=False,
                show_branding=True,
                sort_order=2
            ),

            # Growth Plan
            BillingPlan(
                name=BillingTiersEnum.Growth.value,
                description="Ideal for growing companies with multiple hiring needs",
                price=Decimal("699.00"),
                is_active=True,
                is_featured=True,
                max_open_jobs=15,
                max_users=5,
                max_applicants_per_job=250,
                allow_priority_support=True,
                show_branding=False,
                sort_order=3
            ),

            # Professional Plan
            BillingPlan(
                name=BillingTiersEnum.Professional.value,
                description="Advanced features for established businesses",
                price=Decimal("1299.00"),
                is_active=True,
                is_featured=False,
                max_open_jobs=50,
                max_users=15,
                max_applicants_per_job=500,
                allow_priority_support=True,
                show_branding=False,
                sort_order=4
            ),

            # Enterprise Plan
            BillingPlan(
                name=BillingTiersEnum.Enterprise.value,
                description="Unlimited access for large organizations",
                price=Decimal("2999.00"),
                is_active=True,
                is_featured=False,
                max_open_jobs=None,  # Unlimited
                max_users=None,  # Unlimited
                max_applicants_per_job=None,  # Unlimited
                allow_priority_support=True,
                show_branding=False,
                sort_order=5
            )
        ]
        self.logger.info(f"Started Initializing Standard Billing Plans : {standard_plans}")
        with self.session_factory() as session:
            saved_plans = []

            if standard_plans:
                for s_plan in standard_plans:
                    if not s_plan:
                        continue

                    existing = session.query(BillingPlanORM).filter_by(name=s_plan.name).first()
                    if not existing:
                        orm_plan = BillingPlanORM(**s_plan.model_dump())
                        session.add(orm_plan)
                        session.commit()
                        session.refresh(orm_plan)
                        saved_plans.append(BillingPlan(**orm_plan.to_dict()))
                    else:
                        saved_plans.append(BillingPlan(**existing.to_dict()))

            return saved_plans

    async def _look_up_plan(self, plan_id: str) -> BillingPlan | None:
        """Returns the billing plan details for a given plan_id"""
        if not (isinstance(plan_id, str) and plan_id.strip()):
            self.logger.error("Cannot Look Up Plan as Plan ID is Invalid")
            return None

        with self.session_factory() as session:
            billing_plan_orm = session.query(BillingPlanORM).filter_by(plan_id=plan_id).first()
            if not billing_plan_orm:
                self.logger.info("Billing Plan Not Found")
                return None
            billing_plan = BillingPlan(**billing_plan_orm.to_dict())
            self.logger.info(f"Billing Plan Found : {billing_plan}")
            return billing_plan

    async def _all_billing_plans(self) -> list[BillingPlan]:
        """returns all billing plans"""
        with self.session_factory() as session:
            billing_plams_orm_list = session.query(BillingPlanORM).all()
            billing_plans_list = [BillingPlan(**plan_orm.to_dict()) for plan_orm in billing_plams_orm_list
                                  if plan_orm] if billing_plams_orm_list else []
            return billing_plans_list

    async def _expire_trial(self, company_id: str) -> CompanyBillingProfile | None:
        """Will mark a Trial Billing Plan as Expired then send an event """
        if not (isinstance(company_id, str) and company_id.strip()):
            self.logger.error("Unable to run Expire Trial as Company ID is Invalid")
            return None

        with self.session_factory() as session:
            profile_orm = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()
            profile = CompanyBillingProfile(**profile_orm.to_dict()) if profile_orm else None
            if profile and profile_orm.is_trial_valid:  # Check ORM's is_trial_valid
                profile_orm.trial_active = False
                profile_orm.trial_end_date = utc_time().date()
                profile_orm.auto_renew = False
                await self.billing_events.execute("record_event", company_id=company_id,
                                                  event_type=BillingEventType.TRIAL_ENDED,
                                                  event_metadata={"reason": "expired"})  # Using Enum

                session.commit()
                session.refresh()

            return CompanyBillingProfile(**profile_orm.to_dict())  # Return updated ORM as model

    async def _start_trial(self, company_id: str, plan_id: str) -> CompanyBillingProfile | None:
        """Start a trial for a company (if not already active)."""
        if not (isinstance(company_id, str) and company_id.strip()):
            self.logger.error("Cannot Look Up Plan as Plan ID is Invalid")
            return None
        self.logger.info(f"Starting Trial Billing for : {company_id}")
        with self.session_factory() as session:
            profile_orm = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()
            plan_orm = session.query(BillingPlanORM).filter_by(plan_id=plan_id).first()
            trial_plan = BillingPlan(**plan_orm.to_dict())


            if not profile_orm:
                # If profile doesn't exist, create a fresh one with trial enabled
                trial_end_date: date = datetime.now(timezone.utc).date() + timedelta(days=self.trial_period_days)

                company_profile = CompanyBillingProfile(
                    company_id=company_id, current_plan_id=trial_plan.plan_id,
                    subscription_start=datetime.now(timezone.utc).date(),
                    subscription_end=trial_end_date,
                    trial_end_date=trial_end_date,
                    trial_active=True)
                profile_orm = CompanyBillingProfileORM(
                    **company_profile.model_dump(exclude={'invoices', 'billing_plan'}))

                await self.billing_events.execute("record_event",
                                                  company_id=company_id,
                                                  event_type=BillingEventType.TRIAL_PROFILE_CREATED,  # Using Enum
                                                  event_metadata={"trigger": "subscription_payment"})
                session.add(profile_orm)

            else:
                # If trial already active or previously used, don't reassign
                if profile_orm.trial_active or profile_orm.trial_end_date:  # Check ORM attributes
                    return CompanyBillingProfile(**profile_orm.to_dict())

                profile_orm.trial_active = True
                profile_orm.trial_end_date = datetime.now(timezone.utc).date() + timedelta(days=14)  # Use .date()
            await self.billing_events.execute("record_event", company_id=company_id,
                                              event_type=BillingEventType.TRIAL_STARTED,  # Using Enum
                                              event_metadata={"duration_days": str(self.trial_period_days)})

            session.commit()
            session.refresh(profile_orm)  # Refresh to get latest state after commit
            return CompanyBillingProfile(**profile_orm.to_dict())

    async def _update_all_subscription_states(self) -> list[CompanyBillingProfile]:
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
            results = await asyncio.gather(*tasks)
            self.logger.info(f"Company ID's of all subscriptions : {results}")
            return results

    async def _update_subscription_state(self, company_id: str) -> CompanyBillingProfile | None:
        """
        Updates subscription status:
        - Ends trial if expired
        - Handles subscription expiration
        - Applies grace periods
        - Can be triggered via CRON or login
        """
        if not (isinstance(company_id, str) and company_id.strip()):
            self.logger.error("Cannot Update Subscription Company ID is Invalid")
            return None

        today = datetime.now(timezone.utc).date()

        with self.session_factory() as session:
            profile_orm = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()
            if not profile_orm:
                return None

            profile = CompanyBillingProfile(**profile_orm.to_dict())

            # 2. Check if subscription has ended and apply expiry/grace logic
            if profile.is_active_subscription_plan:
                # If subscription end date has passed, apply grace or expire

                if profile.subscription_end < today:
                    self.logger.info(f"Subscription has ended : {profile}")
                    if profile.grace_period_ended:  # This property needs to be managed
                        self.logger.info(f"Grace Period has Ended : {profile}")
                        # Subscription fully expired, no grace left
                        profile_orm.current_plan_id = None  # No active plan
                        profile_orm.subscription_start = None
                        profile_orm.subscription_end = None
                        profile_orm.is_payment_overdue = True  # Mark as overdue if it was for payment.
                        profile_orm.auto_renew = False  # Ensure it doesn't auto-renew
                        await self.billing_events.execute("record_event", company_id=company_id,
                                                          event_type=BillingEventType.SUBSCRIPTION_EXPIRED,
                                                          # Using Enum
                                                          event_metadata={"reason": "grace_period_expired",
                                                                          "auto_check": "true"})
                        self.logger.info(f" Event Created : {BillingEventType.SUBSCRIPTION_EXPIRED.value}")
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

    async def _expire_subscription(self, company_id: str) -> CompanyBillingProfile | None:
        """
        Explicitly expires a company's subscription. This might be called by cron for past-due subscriptions.
        """
        if not (isinstance(company_id, str) and company_id.strip()):
            self.logger.error("Cannot Expire Subscription Company ID is Invalid")
            return None

        with self.session_factory() as session:
            profile_orm = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()
            if not profile_orm:
                self.logger.info(f"Billing profile for company {company_id} not found.")
                return None


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
                                                  event_type=BillingEventType.SUBSCRIPTION_EXPIRED,  # Using Enum
                                                  event_metadata={"reason": "manual_or_cron_expiry"})
                self.logger.info(f"Created an Event : {BillingEventType.SUBSCRIPTION_EXPIRED.value}")

            session.commit()
            session.refresh(profile_orm)
            billing_profile = CompanyBillingProfile(**profile_orm.to_dict())
            self.logger.info(f"Billing Profile : {billing_profile}")
            return billing_profile

    async def _create_billing_profile(self, company_id: str, plan_id: str) -> CompanyBillingProfile | None:
        """
        Creates a new billing profile for a company.
        :param company_id: The ID of the company.
        :param plan_id: The ID of the initial billing plan.
        :return: The newly created CompanyBillingProfile, or None if it already exists.
        """
        if not (isinstance(company_id, str) and company_id.strip()):
            self.logger.error("Cannot Create Billing Profile : Invalid Company ID")
            return None
        if not (isinstance(plan_id, str) and plan_id.strip()):
            self.logger.error("Cannot Expire Subscription: Billing Plan ID is Invalid")
            return None

        with self.session_factory() as session:
            billing_profile_orm = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()
            if billing_profile_orm:
                self.logger.info(f"Billing profile for {company_id} already exists. Returning None.")
                return None

            billing_plan: BillingPlanORM = session.query(BillingPlanORM).filter_by(plan_id=plan_id).first()
            if not billing_plan:
                self.logger.error(f"Billing Plan : {plan_id} Not Found - creating New Billing Profile")
                return None

            today = datetime.now(timezone.utc).date()

            # If the plan is a trial, use _start_trial
            if billing_plan.is_trial:
                self.logger.info(f"Creating billing profile for {company_id} with trial plan {plan_id}.")
                trial_billing_profile = await self._start_trial(company_id=company_id)
                self.logger.info(f"Created Trial Billing Profile : Plan : {trial_billing_profile}")
                return trial_billing_profile
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
                                                  event_type=BillingEventType.BILLING_PROFILE_CREATED,  # Using Enum
                                                  event_metadata={"trigger": "create_billing_profile",
                                                                  "plan_id": plan_id})
                session.commit()
                session.refresh(billing_profile_orm)
                self.logger.info(f"Billing profile created for {company_id} with plan {plan_id}.")
                billing_profile = CompanyBillingProfile(**billing_profile_orm.to_dict())
                self.logger.ingo(f"Created Billing Profile : {billing_profile}")
                return billing_profile

    async def _get_billing_profile(self, company_id: str) -> CompanyBillingProfile | None:
        """
        Retrieves a company's billing profile.

        :param company_id: The ID of the company.
        :return: The CompanyBillingProfile if found, otherwise None.
        """
        if not (isinstance(company_id, str) and company_id.strip()):
            self.logger.error("Cannot get A Billing Profile : Invalid Company ID")
            return None

        with self.session_factory() as session:
            profile = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()
            if not profile:
                self.logger.error(f"BIlling Profile for Company ID : {company_id} Cannot Be found")
                return None
            billing_profile = CompanyBillingProfile(**profile.to_dict())
            self.logger.info(f"Billing Profile found  : {billing_profile}")
            return billing_profile

    async def _apply_subscription(self, company_id: str, plan_id: str,
                                  duration_days: int = 30) -> CompanyBillingProfile | None:
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
        if not (isinstance(company_id, str) and company_id.strip()):
            self.logger.error("Cannot apply new Subscription as Company ID is Invalid")
            return None

        if not (isinstance(plan_id, str) and plan_id.strip()):
            self.logger.error("Cannot Apply a new Subscription : Invalid Plan ID")
            return None

        if not (isinstance(duration_days, int) and (duration_days >= 30)):
            self.logger.error("Cannot Apply a new Subscription : Invalid Plan Duration")
            return None

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
                                                  event_type=BillingEventType.BILLING_PROFILE_CREATED,  # Using Enum
                                                  event_metadata={"trigger": "apply_subscription_new_profile"})
            else:
                # If profile exists, end trial if active
                if profile_orm.trial_active:
                    profile_orm.trial_active = False
                    self.logger.info(f"Trial ended for {company_id} due to subscription application.")
                    await self.billing_events.execute("record_event", company_id=company_id,
                                                      event_type=BillingEventType.TRIAL_ENDED,  # Using Enum
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
                                              event_type=BillingEventType.SUBSCRIPTION_CREATED,  # Using Enum
                                              event_metadata={"plan_id": plan_id, "duration_days": duration_days,
                                                              "subscription_end": str(subscription_end)})
            session.commit()
            session.refresh(profile_orm)
            new_billing_profile = CompanyBillingProfile(**profile_orm.to_dict())
            self.logger.info(f"Created New Billing Profile : {new_billing_profile}")
            return new_billing_profile

# Standard Library
import asyncio
import inspect
import uuid
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
            "get_plan": self._look_up_plan,  # Alias for backward compatibility
            "list_all_companies": self._list_all_companies,  # Added for cron service mock
            "list_all_billing_plans": self._all_billing_plans,
            "update_subscription_state": self._update_subscription_state,
            "update_all_subscription_states": self._update_all_subscription_states,
            "get_billing_profile": self._get_billing_profile,
            'create_billing_profile': self._create_billing_profile,
            "apply_subscription": self._apply_subscription,
            "expire_subscription": self._expire_subscription,  # Added for cron service usage
            "init_standard_billing_plans": self._init_standard_billing_plans,
            "change_plan": self._change_plan,
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
        # self.logger.info(f"Started Initializing Standard Billing Plans : {standard_plans}")
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

    async def _start_trial(
            self,
            company_id: str,
    ) -> Optional[CompanyBillingProfile]:
        """
        Start a trial for a company if:
          - the company has no active trial yet, and
          - a trial plan exists in the database.
        The trial plan is located automatically (is_trial = True).
        Returns the updated / newly-created CompanyBillingProfile or None on error.
        """

        if not (isinstance(company_id, str) and company_id.strip()):
            self.logger.error("Cannot start trial: invalid company_id")
            return None

        self.logger.info(f"Starting trial for company: {company_id}")

        with self.session_factory() as session:
            # 1. Fetch the unique trial plan
            trial_plan_orm = (
                session.query(BillingPlanORM)
                .filter_by(is_trial=True)
                .one_or_none()
            )
            if not trial_plan_orm:
                self.logger.error("No trial plan found in the database")
                return None

            trial_plan = BillingPlan(**trial_plan_orm.to_dict())

            # 2. Fetch / create company profile
            profile_orm = (
                session.query(CompanyBillingProfileORM)
                .filter_by(company_id=company_id)
                .first()
            )

            now = datetime.now(timezone.utc)

            if not profile_orm:
                # Create a fresh profile with trial enabled
                trial_end = now.date() + timedelta(days=self.trial_period_days)

                profile_orm = CompanyBillingProfileORM(
                    subscription_id=str(uuid.uuid4()),
                    company_id=company_id,
                    current_plan_id=trial_plan.plan_id,
                    subscription_start=now,
                    subscription_end=datetime(
                        trial_end.year,
                        trial_end.month,
                        trial_end.day,
                        23,
                        59,
                        59,
                        tzinfo=timezone.utc,
                    ),
                    trial_active=True,
                    trial_end_date=trial_end,
                )
                session.add(profile_orm)
                event_type = BillingEventType.TRIAL_PROFILE_CREATED
                metadata = {"trigger": "_start_trial"}

            else:
                # Company already has a profile – check for existing trial
                if profile_orm.trial_active or profile_orm.trial_end_date:
                    self.logger.info(
                        f"Trial already active / used for {company_id}; skipping"
                    )
                    return CompanyBillingProfile(**profile_orm.to_dict())

                # Attach trial to existing profile
                trial_end = now.date() + timedelta(days=self.trial_period_days)
                profile_orm.trial_active = True
                profile_orm.trial_end_date = trial_end
                profile_orm.current_plan_id = trial_plan.plan_id
                profile_orm.subscription_start = now
                profile_orm.subscription_end = datetime(
                    trial_end.year,
                    trial_end.month,
                    trial_end.day,
                    23,
                    59,
                    59,
                    tzinfo=timezone.utc,
                )
                event_type = BillingEventType.TRIAL_STARTED
                metadata = {"duration_days": str(self.trial_period_days)}

            # 3. Commit & log event
            session.commit()
            session.refresh(profile_orm)

            await self.billing_events.execute(
                "record_event",
                company_id=company_id,
                event_type=event_type,
                event_metadata=metadata,
            )

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

    # ------------------------------------------------------------------
    #  Public method that your controller will call
    # ------------------------------------------------------------------
    async def _change_plan(
            self,
            company_id: str,
            new_plan_id: Optional[str] = None,
    ) -> Optional[CompanyBillingProfile]:
        """
        Change the billing plan for a company.

        Rules
        -----
        1. If new_plan_id is None, detach any current plan (subscription ends
           immediately, no trial).
        2. If new_plan_id == current_plan_id → no-op.
        3. If target plan is a trial → restart trial (end previous subscription).
        4. Otherwise (paid plan) → swap plan, extend subscription window by
           the new plan’s duration days from today.

        Returns
        -------
        Updated CompanyBillingProfile or None on any blocking error.
        """

        # ---------- Basic validation ----------
        if not (isinstance(company_id, str) and company_id.strip()):
            self.logger.error("change_plan: invalid company_id")
            return None

        with self.session_factory() as session:
            profile: Optional[CompanyBillingProfileORM] = (
                session.query(CompanyBillingProfileORM)
                .filter_by(company_id=company_id)
                .first()
            )
            if not profile:
                self.logger.error(f"change_plan: no billing profile for {company_id}")
                return None

            old_plan_id = profile.current_plan_id
            if new_plan_id == old_plan_id:
                self.logger.info(
                    f"change_plan: {company_id} already on plan {new_plan_id} – no-op"
                )
                return CompanyBillingProfile(**profile.to_dict())

            # ---------- Detach plan ----------
            if new_plan_id is None:
                profile.current_plan_id = None
                profile.subscription_start = None
                profile.subscription_end = None
                profile.trial_active = False
                session.commit()
                session.refresh(profile)

                await self.billing_events.execute(
                    "record_event",
                    company_id=company_id,
                    event_type=BillingEventType.PLAN_CHANGED,
                    event_metadata={
                        "trigger": "change_plan",
                        "old_plan_id": old_plan_id,
                        "new_plan_id": None,
                    },
                )
                return CompanyBillingProfile(**profile.to_dict())

            # ---------- Validate new plan ----------
            new_plan: Optional[BillingPlanORM] = (
                session.query(BillingPlanORM)
                .filter_by(plan_id=new_plan_id)
                .first()
            )
            if not new_plan:
                self.logger.error(
                    f"change_plan: new plan {new_plan_id} not found"
                )
                return None

            # ---------- Trial plan ----------
            if new_plan.is_trial:
                # End any existing subscription window
                profile.current_plan_id = None
                profile.subscription_start = None
                profile.subscription_end = None
                profile.trial_active = False
                session.commit()

                # Kick off a fresh trial
                trial_profile = await self._start_trial(company_id=company_id)
                return trial_profile

            # ---------- Paid plan swap ----------
            today = datetime.now(timezone.utc).date()
            new_end = today + timedelta(days=new_plan.duration_days)

            profile.current_plan_id = new_plan_id
            profile.subscription_start = datetime.now(timezone.utc)
            profile.subscription_end = datetime(
                new_end.year,
                new_end.month,
                new_end.day,
                23,
                59,
                59,
                tzinfo=timezone.utc,
            )
            profile.trial_active = False
            session.commit()
            session.refresh(profile)

            await self.billing_events.execute(
                "record_event",
                company_id=company_id,
                event_type=BillingEventType.PLAN_CHANGED,
                event_metadata={
                    "trigger": "change_plan",
                    "old_plan_id": old_plan_id,
                    "new_plan_id": new_plan_id,
                },
            )

            updated = CompanyBillingProfile(**profile.to_dict())
            self.logger.info(
                f"change_plan success: {company_id} {old_plan_id} → {new_plan_id}"
            )
            return updated

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

    async def _create_billing_profile(
            self,
            company_id: str,
            plan_id: Optional[str] = None,
    ) -> Optional[CompanyBillingProfile]:
        """
        Creates a new billing profile for a company.
        """
        # ------------- Basic validation -------------
        if not (isinstance(company_id, str) and company_id.strip()):
            self.logger.error("Cannot Create Billing Profile: Invalid Company ID")
            return None

        with self.session_factory() as session:
            # ------------- Does it already exist? -------------
            if session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first():
                self.logger.info(f"Billing profile for {company_id} already exists.")
                return None

            # ------------- No plan requested -------------
            if plan_id is None:
                # ✅ Create Pydantic model first
                billing_profile = CompanyBillingProfile(
                    company_id=company_id,
                    current_plan_id=None,
                    subscription_start=None,
                    subscription_end=None,
                    trial_active=False,
                    trial_end_date=None,
                )

                # ✅ Then create ORM from Pydantic
                billing_profile_orm = CompanyBillingProfileORM(**billing_profile.model_dump())
                session.add(billing_profile_orm)
                session.commit()

                await self.billing_events.execute(
                    "record_event",
                    company_id=company_id,
                    event_type=BillingEventType.BILLING_PROFILE_CREATED,
                    event_metadata={"trigger": "create_billing_profile", "plan_id": None},
                )

                self.logger.info(f"Billing profile created for {company_id} without a plan.")
                return billing_profile

            # ------------- Plan supplied -------------
            if not (isinstance(plan_id, str) and plan_id.strip()):
                self.logger.error("Cannot Create Billing Profile: plan_id is invalid.")
                return None

            billing_plan: Optional[BillingPlanORM] = (
                session.query(BillingPlanORM).filter_by(plan_id=plan_id).first()
            )
            if not billing_plan:
                self.logger.error(f"Billing Plan {plan_id} not found.")
                return None

            # ------------- Trial plan -------------
            if billing_plan.is_trial:
                self.logger.info(f"Creating trial billing profile for {company_id}.")
                trial_profile = await self._start_trial(company_id=company_id)
                return trial_profile

            # ------------- Regular (paid) plan -------------
            today = datetime.now(timezone.utc).date()
            subscription_end = today + timedelta(days=billing_plan.duration_days)

            # ✅ Create Pydantic model first
            billing_profile = CompanyBillingProfile(
                company_id=company_id,
                current_plan_id=plan_id,
                subscription_start=datetime.now(timezone.utc).date(),
                subscription_end=subscription_end,
                trial_active=False,
                trial_end_date=None
            )

            # ✅ Then create ORM from Pydantic
            billing_profile_orm = CompanyBillingProfileORM(**billing_profile.model_dump())
            session.add(billing_profile_orm)
            session.commit()

            await self.billing_events.execute(
                "record_event",
                company_id=company_id,
                event_type=BillingEventType.BILLING_PROFILE_CREATED,
                event_metadata={"trigger": "create_billing_profile", "plan_id": plan_id},
            )

            self.logger.info(f"Billing profile created for {company_id} with plan {plan_id}.")
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
                    subscription_id=str(uuid.uuid4()),
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

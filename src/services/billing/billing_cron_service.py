# Standard Library
import inspect
from datetime import date, timedelta

# Domain Models
from src.database.models import InvoiceStatusEnum, CompanyBillingProfile

# Services
from src.services.billing.schemas_interfaces import BillingServiceInterface, BillingEventType

# Utilities
from src.utils.route_helpers import get_service


class BillingCronService(BillingServiceInterface):
    """
    Cron-driven reconciliation and notification service for billing system.

    Responsibilities:
    - Reconcile paid invoices and mark as closed
    - Ensure billing profile consistency
    - Trigger notification emails from billing events
    - Auto-expire subscriptions and warn before expiry
    """

    def __init__(self, session_factory, invoice_service, billing_service, billing_events, email_service):
        super().__init__()
        self.session_factory = session_factory
        self.billing_events = billing_events
        self.invoice_service = invoice_service
        self.billing_service = billing_service
        self.email_service = email_service
        self.logger = get_service("logger")()(self.__class__.__name__)
        self.__interface_map = {
            "run": self.run,
            "renew_subscription": self.renew_subscriptions
        }

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

    async def run(self):
        companies_model_list = await self.billing_service.execute("list_all_companies")
        self.logger.info(f"Companies List : {companies_model_list}")
        for company in companies_model_list:
            company_id = company.company_id
            await self.check_subscription_health(company_id)
            await self.send_billing_notifications()
            await self.reconcile_invoices(company_id)

    async def renew_subscriptions(self):
        """Run Once a Week on a Monday Morning"""
        companies_model_list = await self.billing_service.execute("list_all_companies")
        self.logger.info(f"Companies List : {companies_model_list}")

        for company in companies_model_list:
            company_id = company.company_id
            await self.create_upcoming_auto_renew_subscriptions(company_id)  # Add this line
            await self.send_billing_notifications()

    async def reconcile_invoices(self, company_id: str):
        unpaid_invoices_model_list = await self.invoice_service.execute("get_paid_invoices", company_id=company_id)
        for invoice in unpaid_invoices_model_list:

            if invoice.status == InvoiceStatusEnum.PAID.value:
                self.logger.info(f"BillingCronService: Closing invoice {invoice.invoice_id} for company {company_id}")
                await self.invoice_service.execute("close_invoice", invoice_id=invoice.invoice_id)
                await self.billing_events.execute("record_event",
                                                  company_id=company_id,
                                                  event_type=BillingEventType.INVOICE_CLOSED,
                                                  event_metadata={"invoice_id": invoice.invoice_id})

    async def create_upcoming_auto_renew_subscriptions(self, company_id: str):
        """
        Creates new subscriptions with same terms starting day after current expiry
        for all active subscriptions set to auto-renew
        """
        # Find active subscriptions with auto-renew enabled
        # TODO - this needs to be looked at
        active_subscriptions = await self.get_active_subscriptions(
            company_id, auto_renew=True
        )

        created_subscriptions = []

        for subscription in active_subscriptions:
            # Calculate new start date (day after current expiry)
            new_start_date = subscription.end_date + timedelta(days=1)

            # Create new subscription with same terms
            new_subscription = CompanyBillingProfile(**{
                'company_id': company_id,
                'plan_id': subscription.plan_id,
                'start_date': new_start_date,
                'duration': subscription.duration,
                'price': subscription.price,
                'auto_renew': subscription.auto_renew,
                'parent_subscription_id': subscription.id
            })

            created_subscriptions.append(new_subscription)

        return created_subscriptions

    async def check_subscription_health(self, company_id: str):
        self.logger.info(f"BillingCronService: Checking subscription health for company: {company_id}")
        try:
            billing_profile = await self.billing_service.execute("get_billing_profile", company_id=company_id)
            if not billing_profile:
                raise ValueError("Billing profile not found.")
        except ValueError:
            self.logger.info(f"BillingCronService: Billing profile missing for {company_id}. Recording event.")
            await self.billing_events.execute("record_event",
                                              company_id=company_id,
                                              event_type=BillingEventType.BILLING_PROFILE_MISSING,
                                              event_metadata={'company_id': company_id})
            return None

        if billing_profile.is_about_to_expire:
            self.logger.info(f"BillingCronService: Subscription expiring soon for {company_id}. Recording event.")

            await self.billing_events.execute("record_event",
                                              company_id=company_id,
                                              event_type=BillingEventType.SUBSCRIPTION_EXPIRING_SOON,
                                              metadata={"days_left": billing_profile.days_to_expire})
        elif billing_profile.is_active_subscription_plan:
            # Check if subscription has actually expired or is overdue
            # The logic for 'is_active_subscription_plan' and 'expire_subscription' seems to be
            # inverted or combined here. 'expire_subscription' should make it inactive.
            # Assuming 'is_active_subscription_plan' means it's currently active.
            # If it's active and should now be expired, trigger expiry.

            # This block from original code implies expiring a currently active plan if its end date has passed.
            # The 'expire_subscription' method in BillingService handles this state transition.

            # Simulate calling expire_subscription and getting the updated profile

            expired_billing_profile = await self.billing_service.execute("expire_subscription", company_id=company_id)

            # Verify if subscription was actually been expired
            if not expired_billing_profile.is_active_subscription_plan:
                self.logger.info(f"BillingCronService: Subscription expired for {company_id}. Checking last event.")
                # Check last recorded event before adding another
                last_event = await self.billing_events.execute("get_last_event", company_id=company_id,
                                                               event_type=BillingEventType.SUBSCRIPTION_EXPIRED)

                if not last_event:
                    self.logger.info(f"BillingCronService: Recording subscription expired event for {company_id}.")
                    await self.billing_events.execute("record_event", company_id=company_id,
                                                      event_type=BillingEventType.SUBSCRIPTION_EXPIRED,  # Using Enum
                                                      event_metadata={})
        else:
            self.logger.info(f"BillingCronService: No active subscription or trial for {company_id}.")

        return None

    async def send_billing_notifications(self):
        self.logger.info("BillingCronService: Sending billing notifications (emails)...")
        pending_events = await self.billing_events.execute("list_unsent_email_events")
        for event in pending_events:
            self.logger.info(
                f"BillingCronService: Processing pending email event: {event.event_type} for company {event.company_id}")
            try:
                # Assuming email_service.send takes event_type as a string or Enum value directly
                is_success = await self.email_service.send(
                    event_type=event.event_type,  # event.event_type is already the string value from ORM
                    company_id=event.company_id,
                    metadata=event.metadata
                )
                if event.event_type == BillingEventType.PAYMENT_SUCCESS.value:  # Using Enum for comparison
                    # Reconcile the Invoice after payment success notification is sent.
                    self.logger.info(f"BillingCronService: Reconciling invoices after payment success for {event.company_id}")
                    await self.reconcile_invoices(company_id=event.company_id)

                # This is not entirely true that the email has been sent - its on the queue at this time.
                if is_success:
                    self.logger.info(f"BillingCronService: Marking email sent for event {event.event_id}")
                    await self.billing_events.execute("mark_email_sent", event_id=event.event_id)

            except Exception as e:
                self.logger.info(f"BillingCronService: Error sending email for event {event.event_id}: {e}")
                await self.billing_events.execute("record_event", company_id=event.company_id,
                                                  event_type=BillingEventType.EMAIL_SEND_FAILED,
                                                  event_metadata={"event_id": event.event_id, "error": str(e)})  # Using Enum

    async def send_realtime_notifications(self):
        """
        This method is a placeholder for sending real-time notifications.
        It can be implemented to use WebSockets or any other real-time communication method.
        """
        self.logger.info("BillingCronService: Sending real-time notifications")
        realtime_events = await self.billing_events.execute("list_realtime_notifications")

        for event in realtime_events:
            try:
                is_success = await self.email_service.send(
                    event_type=event["event_type"],
                    company_id=event["company_id"],
                    metadata=event.get("metadata", {})
                )
                # This is not entirely true that the email has been sent - its on the queue at this time.
                if is_success:
                    await self.billing_events.execute("mark_email_sent", event_id=event["event_id"])

            except Exception as e:
                self.logger.info(f"BillingCronService: Error processing real-time event {event['event_id']}: {e}")
                await self.billing_events.execute("record_event", company_id=event["company_id"],
                                                  event_type=BillingEventType.EMAIL_SEND_FAILED,
                                                  event_metadata={"event_id": event["event_id"],
                                                                  "error": str(e)})  # Using Enum

# Event types reference:
# - payment_success
# - invoice_closed
# - subscription_applied
# - subscription_expiring_soon
# - subscription_expired
# - billing_profile_missing
# - email_send_failed

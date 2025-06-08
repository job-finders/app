
from src.services.billing.schemas_interfaces import BillingServiceInterface


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
        self._interface_schema = {
            "run": self.run
        }


    async def run(self):
        companies_model_list = await self.billing_service.execute("list_all_companies")
        for company in companies_model_list:
            company_id = company.company_id
            await self.check_subscription_health(company_id)
            await self.send_billing_notifications()
            # await self.reconcile_invoices(company_id)


    async def reconcile_invoices(self, company_id: str):
        unpaid_invoices_model_list = await self.invoice_service.execute("get_paid_invoices", company_id=company_id)
        for invoice in unpaid_invoices_model_list:
            if invoice.status == "Paid":
                await self.invoice_service.execute("close_invoice", invoice_id=invoice.invoice_id)
                await self.billing_events.execute("record_event",
                                                  company_id=company_id,
                                                  type="invoice_closed",
                                                  metadata={"invoice_id": invoice.invoice_id})

    async def check_subscription_health(self, company_id: str):
        try:
            billing_profile = await self.billing_service.execute("get_billing_profile", company_id=company_id)

        except ValueError:
            await self.billing_events.execute("record_event", company_id=company_id, type="billing_profile_missing", metadata={})
            return

        if billing_profile.is_about_to_expire:
            await self.billing_events.execute("record_event",
                                              company_id=company_id,
                                              type="subscription_expiring_soon",
                                              metadata={"days_left": billing_profile.days_to_expire})

        elif billing_profile.is_active_subscription_plan:

            expired_billing_profile = await self.billing_service.execute("expire_subscription", company_id=company_id)

            # Verify if subscription was actually been expired
            if not expired_billing_profile.is_active_subscription_plan:
                # Check last recorded event before adding another
                last_event = await self.billing_events.execute("get_last_event", company_id=company_id,
                                                               event_type="subscription_expired")
                if not last_event:
                    await self.billing_events.execute("record_event", company_id=company_id, type="subscription_expired",
                                                  metadata={})

    async def send_billing_notifications(self):
        pending_events = await self.billing_events.execute("list_unsent_email_events")
        for event in pending_events:
            try:
                is_success = await self.email_service.send(
                    event_type=event["type"],
                    company_id= event['company_id'],
                    metadata=event.get("metadata", {})
                )
                if event["type"] == "payment_success":
                    # Reconcile the Invoice all notifications where sent.
                    await self.reconcile_invoices(company_id=event["company_id"])
                # This is not entirely true that the email has been sent - its on the queue at this time.
                if is_success:
                    await self.billing_events.execute("mark_email_sent", event_id=event["event_id"])

            except Exception as e:
                await self.billing_events.execute("record_event", company_id=event['company_id'], type="email_send_failed", metadata={"event_id": event["event_id"], "error": str(e)})

    async def send_realtime_notifications(self):
        """
        This method is a placeholder for sending real-time notifications.
        It can be implemented to use WebSockets or any other real-time communication method.
        """
        realtime_events = await self.billing_events.execute("list_realtime_notifications")

        for event in realtime_events:
            try:
                is_success = await self.email_service.send(
                    event_type=event["type"],
                    company_id=event["company_id"],
                    metadata=event.get("metadata", {})
                )
                # This is not entirely true that the email has been sent - its on the queue at this time.
                if is_success:
                    await self.billing_events.execute("mark_email_sent", event_id=event["event_id"])

            except Exception as e:
                await self.billing_events.execute("record_event", company_id=event["company_id"], type="email_send_failed", metadata={"event_id": event["event_id"], "error": str(e)})



# Event types reference:
# - payment_success
# - invoice_closed
# - subscription_applied
# - subscription_expiring_soon
# - subscription_expired
# - billing_profile_missing
# - email_send_failed

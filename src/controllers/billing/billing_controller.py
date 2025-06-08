from flask import Flask, redirect, url_for, flash

from src.config import config_instance
from src.controllers.controller import Controllers, error_handler
from src.database.models.billing import CompanyBillingProfile, BillingPlan
from src.services.billing.billing_cron_service import BillingCronService
from src.services.billing.billing_email_service import BillingEmailerService
from src.services.billing.billing_events import BillingEventService
from src.services.billing.billing_service import BillingService
from src.services.billing.invoice_service import InvoiceService
from src.services.billing.payfact_client import PayFastClient
from src.services.billing.payment_service import PaymentService
from src.utils.route_helpers import get_controller


class BillingController(Controllers):
    def __init__(self, factory):
        super().__init__(factory)
        email_service = BillingEmailerService()
        payfast_client = PayFastClient(settings=config_instance().PAYFAST_SETTINGS)
        self.billing_events = BillingEventService(session_factory=self.get_session)
        self.billing_service: BillingService = BillingService(session_factory=self.get_session, billing_events=self.billing_events)
        self.invoice_service: InvoiceService = InvoiceService(session_factory=self.get_session)
        self.payment_service: PaymentService = PaymentService(session_factory=self.get_session, payment_client=payfast_client)

        self.billing_cron_service: BillingCronService = BillingCronService(
            session_factory=self.get_session,billing_events=self.billing_events,invoice_service=self.invoice_service,
            billing_service=self.billing_service,email_service=email_service)

    def init_app(self, app: Flask):
        super().init_app(app)


    async def create_subscription(self, company_id: str, plan_id: str):
        """

        :param company_id:
        :param plan_id:
        :return:
        """
        billing_plan: BillingPlan = await self.billing_service.execute('look_up_plan', plan_id=plan_id)
        billing_profile: CompanyBillingProfile = await  self.billing_service.execute('get_billing_profile', company_id=company_id)
        if not billing_profile:
            if not billing_plan.is_trial:
                billing_profile: CompanyBillingProfile = await self.billing_service.execute('create_billing_profile', company_id=company_id, plan_id=plan_id)
            else:
                billing_profile: CompanyBillingProfile = await self.billing_service.execute('start_trial',  company_id=company_id, plan_id=plan_id)

        company_controller = get_controller("company")
        company = await company_controller.get_company_by_id(company_id=company_id)
        if not billing_plan.is_trial:
            invoice = await self.invoice_service.execute(action="create_invoice", billing_profile=billing_profile, plan=billing_plan)
            await self.billing_events.execute('record_event',
                                              company_id=billing_profile.company_id,
                                              type='invoice_created', metadata={"invoice_id": invoice.invoice_id})

            return await self.payment_service.execute('generate_payfast_form',invoice=invoice,company=company)
        else:

            flash(message="Your Trial Period has started", category="success")
            return redirect(url_for('company.get_dashboard'))

    async def itn_callback(self, data: dict):
        """
            the itn call back will actually apply the subscription to the company once it verifies payment was made.
        :param data:
        :return:
        """
        result = await self.payment_service.execute("process_itn", data)

        if result['valid']:
            if result['status'] == 'COMPLETE':
                plan = await self.billing_service.execute("look_up_plan", plan_id=result['plan_id'])
                # Mark Invoice as Paid
                paid_invoice = await self.invoice_service.execute("mark_invoice_paid", invoice_id=result['invoice_id'])
                # Apply the subscription to the company
                company_billing_profile = await self.billing_service.execute("apply_subscription",
                                                                       company_id=result['company_id'],
                                                                       plan_id=result['plan_id'],
                                                                       duration_days=plan.duration_days)

                await self.billing_events.execute("record_event", company_id=result['company_id'], type='payment_success', metadata=result)
            else:
                await self.billing_events.execute("record_event", company_id=result['company_id'],
                                                  type='payment_failed', metadata=result)
        return result

    async def get_billing_dashboard(self, company_id: str):
        billing_profile = await self.billing_service.execute("get_billing_profile", company_id)
        list_invoices = await self.invoice_service.execute("list_invoices", company_id, limit=5)
        billing_events = await self.billing_events.execute('list_events', company_id)

        return {
            'billing_profile': billing_profile,
            'list_invoices': list_invoices,
            'recent_events': billing_events}

    @error_handler
    async def handle_trial_expiry(self, company_id: str):
        return await self.billing_service.execute("expire_trial", company_id)

    @error_handler
    async def generate_invoice(self, company_id: str):
        return await self.billing_service.execute("create_invoice", company_id)

    @error_handler
    async def process_payment(self, invoice_id: str):
        return await self.payment_service.execute("process_payment", invoice_id)

    @error_handler
    async def sync_subscription_status(self, company_id: str):
        return await self.billing_service.execute("update_subscription_state", company_id)


    @error_handler
    async def cron_update_subscription_states(self):
        """
            cron jobs to update all company subscriptions.
        :return:
        """
        return await self.billing_service.execute("update_all_subscription_states")

    @error_handler
    async def cron_billing(self):
        """
            cron job to run billing tasks
        :return:
        """
        return await self.billing_cron_service.execute("run")


    async def get_billing_plan_from_slug(self, plan_slug: str):
        """
        :param plan_slug:
        :return:
        """
        billing_plans = await self.billing_service.execute('list_all_billing_plans')
        for plan in billing_plans:
            if plan.plan_slug == plan_slug:
                return plan
        return None


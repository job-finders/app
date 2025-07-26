import asyncio
from decimal import Decimal

from flask import Flask, redirect, url_for, flash


from src.services.billing.schemas_interfaces import BillingEventType
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
from src.tasks.celery.workers.email_queue import enqueue_email
from src.utils.route_helpers import get_controller


class BillingController(Controllers):
    def __init__(self, factory):
        super().__init__(factory)
        # Initializing Controllers and Services
        company_repo  = get_controller('company')
        email_service = BillingEmailerService(company_repo=company_repo,email_queue=enqueue_email)
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
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._safe_execute())
        else:
            loop.create_task(self._safe_execute())

    async def _safe_execute(self):
        await self.billing_service.execute("init_standard_billing_plans")


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

        if not billing_plan.is_trial:
            invoice = await self.invoice_service.execute(action="create_invoice", billing_profile=billing_profile, plan=billing_plan)
            await self.billing_events.execute('record_event', company_id=billing_profile.company_id, event_type=BillingEventType.INVOICE_CREATED,
            metadata={"invoice_id": invoice.invoice_id})

            company_controller = get_controller("company")
            company = await company_controller.get_company_by_id(company_id=company_id)
            # This will create the payment request and send to the user via the web - if the user pays then we will mark the invoice as paid
            # This will ensure that endpoints that needs to be accessed through a billing plan are not accessible to the user
            return await self.payment_service.execute('generate_payfast_form',invoice=invoice,company=company)
        else:
            flash(message="Your Trial Period has started", category="success")
            return redirect(url_for('company.get_dashboard'))

    async def get_trial_billing_plan(self) -> BillingPlan | None:
        """

        :return:
        """
        all_billing_plans = await self.billing_service.execute('list_all_billing_plans')
        for billing_plan in all_billing_plans:
            if billing_plan.is_trial:
                return billing_plan
        return None

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
                                                  event_type='payment_failed', metadata=result)
        return result

    async def get_billing_dashboard(self, company_id: str):
        billing_profile = await self.billing_service.execute("get_billing_profile", company_id)
        list_invoices = await self.invoice_service.execute("list_company_invoices", company_id, limit=5)
        billing_events = await self.billing_events.execute('list_events', company_id)
        if not billing_profile:
            self.logger.warning(f"No billing profile found for company_id: {company_id}")
            return {}

        billing_plan = await self.billing_service.execute('look_up_plan', plan_id=billing_profile.current_plan_id)
        return {
            'billing': billing_profile,
            'current_plan': billing_plan,
            'list_invoices': list_invoices,
            'recent_events': billing_events}

    @error_handler
    async def has_billing_profile(self, company_id: str) -> bool:
        billing_profile = await self.billing_service.execute("get_billing_profile", company_id=company_id)
        return billing_profile.is_active_subscription_plan if billing_profile else False

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
        self.logger.info("Scheduler Started Service : cron_update_subscription_states")
        return await self.billing_service.execute("update_all_subscription_states")

    @error_handler
    async def cron_billing(self):
        """
            cron job to run billing tasks
        :return:
        """
        self.logger.info("Scheduler Started Task : Billing Cron Service")
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

    async def get_all_billing_plans(self):
        """
        :return: List of all billing plans
        """
        return await self.billing_service.execute('list_all_billing_plans')

    async def get_create_billing_profile(self, company_id: str, plan_id: str):
        """
        Create a billing profile for the company if it does not exist.
        :param company_id:
        :param plan_id:
        :return: BillingProfile
        """
        billing_profile: CompanyBillingProfile = await  self.billing_service.execute('get_billing_profile', company_id=company_id)
        if not billing_profile:
            billing_profile: CompanyBillingProfile = await self.billing_service.execute('create_billing_profile', company_id=company_id, plan_id=plan_id)
        return billing_profile

    async def get_billing_profile(self, company_id: str):
        """
        Get the billing profile for the company.
        :param company_id:
        :return: BillingProfile
        """
        return await self.billing_service.execute('get_billing_profile', company_id=company_id)

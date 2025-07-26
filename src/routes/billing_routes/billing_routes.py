from flask import Blueprint, request, render_template, flash, redirect, url_for

from src.authentication import employer_login,company_access_required
from src.database.models import User
from src.routes import flask_error_handler
from src.utils.route_helpers import get_controller, get_service

billing_route = Blueprint('billing', __name__, url_prefix="/company/billing")
billing_logger = get_service("logger")()("billing_route")

@billing_route.post("/ipn/payfast")
async def payfast_ipn():
    """
        Handle Notifications from payfast
    :return:
    """

    billing_controller = get_controller("billing")
    return await billing_controller.itn_callback(data=request.form)


@billing_route.route("/manage/<string:company_id>", methods=["GET", "POST"])
@flask_error_handler
@employer_login
async def manage_billing(user: User, company_id: str):
    """
    GET  – show plans, current subscription, unpaid invoices
    POST – change plan (upgrade / downgrade) or start trial
    """
    billing_ctl   = get_controller("billing")
    company_ctl   = get_controller("company")
    company       = await company_ctl.get_company_by_id(company_id)

    # current state
    profile       = await billing_ctl.get_billing_profile(company_id)
    all_plans     = await billing_ctl.get_all_billing_plans()
    unpaid        = await billing_ctl.invoice_service.execute(
        "list_company_invoices", company_id=company_id)

    if request.method == "POST":
        plan_id = request.form.get("plan_id")
        action  = request.form.get("action")          # upgrade | downgrade | trial
        if not plan_id:
            flash("Please select a plan", "warning")
            return redirect(request.url)

        # 1.  trial start
        if action == "trial":
            await billing_ctl.billing_service.execute(
                "start_trial", company_id=company_id, plan_id=plan_id)
            flash("Trial activated 🎉", "success")
            return redirect(url_for("company.get_dashboard"))

        # 2.  upgrade / downgrade
        await billing_ctl.billing_service.execute("change_plan", company_id=company_id, new_plan_id=plan_id)
        flash("Plan updated successfully", "success")

        # 3.  outstanding invoice?
        if unpaid:
            invoice = unpaid[0]
            return redirect(url_for("billing.checkout", invoice_id=invoice.invoice_id))

        return redirect(url_for("company.get_dashboard"))
    else:
        # GET request - show plans and current subscription
        if not profile:
            profile = await billing_ctl.billing_service.execute("create_billing_profile", company_id=company_id)

    return render_template(
        "company/billing/plan_management.html",
        company       = company,
        profile       = profile,
        plans         = [p for p in all_plans if p.is_active],
        unpaid_invoices = unpaid,
    )


@billing_route.get("/dashboard")
@flask_error_handler
@employer_login
async def get_dashboard(user: User):
    """
    :param user:
    :return:
    """
    billing_controller = get_controller("billing")
    company_controller = get_controller('company')

    employer_profile = await company_controller.get_employer_by_uid(user_id=user.uid)
    if not employer_profile:
        flash(message="Something has gone wrong if this error persists please inform admin", category="danger")
        return redirect(url_for("company.get_dashboard"))

    company_profile = await company_controller.get_company_by_id(company_id=employer_profile.company_id)
    if not company_profile:
        flash(message="Something has gone wrong if this error persists please inform admin", category="danger")
        return redirect(url_for("company.get_dashboard"))

    billing_logger.info("trying to fetch billing profile")

    has_billing_profile = await billing_controller.has_billing_profile(company_id=company_profile.company_id)
    billing_logger.info(f"Billing profile found : {str(has_billing_profile)}")

    if has_billing_profile:
        billing_logger.info(f"Company Profile : {company_profile}")
        billing_context = await billing_controller.get_billing_dashboard(company_id=employer_profile.company_id)
        billing_logger.info(f"Billing Dashboard Context : {billing_context}")
        billing_context.update(current_user=user, employer_profile=employer_profile, company_profile=company_profile)
        billing_logger.info("==============================================================================")
        billing_logger.info(f"Billing Context : {billing_context}")
        return render_template('company/billing/billing.html', **billing_context)

    flash(message="You do not have a billing profile, please create one to continue", category="danger")
    return redirect(url_for("billing.manage_billing", company_id=company_profile.company_id))



@billing_route.get("/subscribe/<string:plan_slug>")
@flask_error_handler
@employer_login
async def subscribe(user: User, plan_slug: str):
    """
    :param plan_slug:
    :param user:
    :return:
    """

    billing_controller = get_controller("billing")
    company_controller = get_controller('company')

    billing_plan = await billing_controller.get_billing_plan_from_slug(plan_slug=plan_slug)
    if not billing_plan:
        flash(message="Something has gone wrong if this error persists please inform admin", category="danger")
        return redirect(url_for("company.get_dashboard"))

    employer_profile = await company_controller.get_employer_by_uid(user_id=user.uid)
    if not employer_profile:
        flash(message="Something has gone wrong if this error persists please inform admin", category="danger")
        return redirect(url_for("company.get_dashboard"))

    return await billing_controller.create_subscription(company_id=employer_profile.company_id, plan_id=billing_plan.plan_id)



@billing_route.route("/checkout/<string:invoice_id>", methods=["GET"])
@flask_error_handler
@employer_login
async def checkout(user: User, invoice_id: str):
    """
    GET – display invoice summary & PayFast payment button
    PayFast will POST the ITN to /billing/itn when payment is complete
    """
    billing_ctl = get_controller("billing")
    invoice     = await billing_ctl.invoice_service.execute("get_invoice", invoice_id=invoice_id)

    if not invoice:
        flash("Invoice not found", "danger")
        return redirect(url_for("company.get_dashboard"))

    if invoice.status == "Paid":
        flash("This invoice has already been paid", "info")
        return redirect(url_for("company.get_dashboard"))

    company = await get_controller("company").get_company_by_id(invoice.company_id)
    pay_url = await billing_ctl.payment_service.execute(
        "generate_payfast_form", invoice=invoice, company=company
    )

    return render_template(
        "company/billing/checkout.html",
        invoice=invoice,
        company=company,
        pay_url=pay_url,
    )
    
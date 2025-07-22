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

@billing_route.route("/create-billing-profile/<string:company_id>", methods=["GET", "POST"])
@flask_error_handler
@employer_login
async def create_billing_profile(user: User, company_id: str):
    """
    GET  – display the plan-selection / profile-creation form.
    POST – validate the form, create the billing profile, then redirect
           to the billing dashboard.
    """
    billing_controller = get_controller("billing")

    if request.method == "POST":
        # Extract submitted data (e.g. selected plan, card token, etc.)
        plan_id = request.form.get("plan_id")
        # …other fields…

        response = await billing_controller.create_subscription(company_id=company_profile.company_id, plan_id=plan_id)
        flash(f"{company_profile.name}, your billing plan is active. You’re all set!", category="success")
        return response

    # GET ---------------------------------------------------------------
    billing_profile = await billing_controller.get(
        user=user, company_id=company_id
    )
    
    billing_plans = await billing_controller.get_all_billing_plans()

    return render_template(
        "company/billing/plan_management.html",
        billing_plans=billing_plans,
        current_user=user,
        billing_profile=billing_profile,
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
    return redirect(url_for("billing.create_billing_profile")), 400



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



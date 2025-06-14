from flask import Blueprint, request, render_template, flash, redirect, url_for

from src.authentication import employer_login
from src.database.models.users import User
from src.routes import flask_error_handler
from src.utils.route_helpers import get_controller

billing_route = Blueprint('billing', __name__, url_prefix="/company/billing")


@billing_route.post("/ipn/payfast")
async def payfast_ipn():
    """
        Handle Notifications from payfast
    :return:
    """

    billing_controller = get_controller("billing")
    return await billing_controller.itn_callback(data=request.form)



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

    billing_dashboard = await billing_controller.get_billing_dashboard(company_id=employer_profile.company_id)

    context = dict(user=user, employer_profile=employer_profile,company_profile=company_profile,  **billing_dashboard)
    return render_template('company/billing/billing.html', **context)


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



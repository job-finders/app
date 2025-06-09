from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, send_file
from pydantic import ValidationError

from src.firewall.rate_limiting import rate_limit
from src.authentication import user_details
from src.database.models.notifications import CreateNotifications
from src.database.models.seo import create_tags
from src.database.models.users import User
from src.logger import init_logger
from src.routes import flask_error_handler
from src.routes.utils import (fetch_and_cache_logo, create_context, not_found)
from src.utils import format_title
from src.utils.route_helpers import get_service

from src.cache.cache_redis import cached

home_route = Blueprint('home', __name__)
home_logger = init_logger("home_logger")


# Route definitions

@home_route.get("/media/logos/<job_ref>.png")
@rate_limit("120 per minute")
@flask_error_handler
@cached
async def serve_logo(job_ref: str):
    """Serve a job logo that is cached or fetch it if not present."""
    job = get_service('scraper').jobs.get(job_ref)
    if not job:
        home_logger.error(f"Job not found: {job_ref}")
        abort(404)

    file_path = fetch_and_cache_logo(job)
    if not file_path or not file_path.exists():
        home_logger.error(f"File not found or invalid: {file_path}")
        abort(404)
    return send_file(file_path, mimetype="image/png")


@home_route.get('/')
@rate_limit("250 per minute")
@flask_error_handler
@user_details
@cached
async def get_home(user: User):
    """Render home page with a default search term."""
    search_term = "home"
    home_logger.info(f"User Details: {user}")
    response = await create_context(user=user, search_term=search_term)
    if response is None:
        return await not_found(search_term)
    return response

@home_route.get('/about')
@rate_limit("250 per minute")
@flask_error_handler
@user_details
@cached
async def about(user: User):
    """Render the about page.
    Note that Cache Handler Must Be first. then other handlers can follow on like this. 

@route.get("/feature")
@roles_required("admin", "manager")  # Sets g.user
@require_billing_role_from_trial    # Requires g.user
@cached                             # Can now use g.user in cache keys
async def premium_feature(user: User):
    # user comes from roles_required decorator
    # g.user is also available
    return render_template(...)

    """
    seo = await create_tags(search_term="about")
    context = dict(current_user=user,seo=seo,term='About')
    return render_template('about.html', **context)


@home_route.get('/contact')
@rate_limit("250 per minute")
@flask_error_handler
@user_details
@cached
async def contact(user: User):
    """Render the contact page."""
    seo = await create_tags(search_term="contact")
    context = dict(current_user=user, seo=seo, term='Contact Us')
    return render_template('contact.html', **context)


@home_route.get('/terms')
@rate_limit("250 per minute")
@flask_error_handler
@user_details
@cached
async def terms(user: User):
    """Render the terms page."""
    seo = await create_tags(search_term="terms")
    context = dict(current_user=user, seo=seo, term='Privacy Policy | Terms & Conditions')
    return render_template('terms.html', **context)

@home_route.get('/privacy')
@flask_error_handler
@user_details
@cached
async def privacy(user: User):
    """Render the terms page."""
    seo = await create_tags(search_term="terms")
    context = dict(current_user=user, seo=seo, term='Privacy Policy | Terms & Conditions')
    # TODO - include separate privacy statement
    return render_template('terms.html', **context)

@home_route.get('/documentation')
@rate_limit("250 per minute")
@flask_error_handler
@user_details
@cached
async def documentation(user: User):
    """Render the terms page."""
    seo = await create_tags(search_term="terms")
    context = dict(current_user=user, seo=seo, term='Privacy Policy | Terms & Conditions')
    # TODO - include separate privacy statement
    return render_template('documentation.html', **context)


@home_route.get('/sister-sites')
@rate_limit("250 per minute")
@flask_error_handler
@user_details
@cached
async def sister_sites(user: User):
    """Render the sister sites page."""
    seo = await create_tags(search_term="sister-sites")
    context = dict(current_user=user, seo=seo, term='Sister Websites')
    return render_template('sisters.html', **context)


@home_route.get('/faq')
@rate_limit("250 per minute")
@flask_error_handler
@user_details
@cached
async def faq(user: User):
    """Render the FAQ page."""
    seo = await create_tags(search_term="FAQ")
    context = dict(current_user=user, seo=seo, term='FAQ| Frequently Asked Questions')
    return render_template('faq.html', **context)


@home_route.get('/linkedin-learning')
@rate_limit("250 per minute")
@flask_error_handler
@user_details
@cached
async def linkedin_learning(user: User):
    """Render the LinkedIn Learning page."""
    seo = await create_tags(search_term="LinkedIn Learning")
    context = dict(current_user=user, seo=seo, term='LinkedIn Learning')
    return render_template('linkedin.html', **context)


@home_route.post('/job-notifications/<string:search_term>')
@rate_limit("250 per minute")
@flask_error_handler
@user_details
async def email_me(user: User, search_term: str):
    """Process job notification email subscription."""
    page = int(request.args.get('page', 1))
    try:
        notifications = CreateNotifications(**request.form)
        notifications.topic = search_term
        notifications_controller = get_service('notifications')
        created_notification = await notifications_controller.create_notification_email(notification=notifications)
        if not created_notification:
            flash("There was a problem adding you to the email list; you may already be added or cannot be on more than one list at a time", "danger")
            return redirect(url_for('home.get_home'), code=302)

        await notifications_controller.send_notification_verification_email(notification=created_notification)
    except ValidationError:
        flash("There was a problem creating your email alert please try again later", "danger")
        return redirect(url_for('home.get_home'), code=302)
    except Exception:
        flash("There was a problem creating your email alert please try again later", "danger")
        return redirect(url_for('home.get_home'), code=302)

    flash(f"Please check your email for our verification message so we can send you jobs about {format_title(search_term)}", "success")
    response = await create_context(search_term=search_term, page=page)
    if response is None:
        return await not_found(search_term)
    return response


@home_route.get('/email-verification/<string:verification_id>')
@rate_limit("250 per minute")
@flask_error_handler
@user_details
async def verify_email(user: User, verification_id: str):
    """Verify email for job notifications."""
    email = request.args.get("email")
    if not email:
        flash("Unable to verify Email Address", "danger")
        return redirect(url_for('home.get_home'), code=302)
    notifications_controller = get_service('notifications')
    if await notifications_controller.check_verification(verification_id=verification_id, email=email):
        flash("You have successfully been added to our job alerts service", "success")
        return redirect(url_for('home.get_home'), code=302)

    flash("Unfortunately we could not verify your email address; please try again", "danger")
    return redirect(url_for('home.get_home'), code=302)



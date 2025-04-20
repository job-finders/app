from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, send_file
from pydantic import ValidationError

from src.routes import flask_error_handler
from src.database.models.notifications import CreateNotifications
from src.database.models.seo import create_tags
from src.logger import init_logger
from src.main import scrapper, notifications_controller
from src.routes.utils import (fetch_and_cache_logo, create_context, not_found, redirect_apply_page)
from src.utils import format_title

home_route = Blueprint('home', __name__)
home_logger = init_logger("home_logger")


# Route definitions

@home_route.get("/media/logos/<job_ref>.png")
async def serve_logo(job_ref: str):
    """Serve a job logo that is cached or fetch it if not present."""
    job = scrapper.jobs.get(job_ref)
    if not job:
        home_logger.error(f"Job not found: {job_ref}")
        abort(404)

    file_path = fetch_and_cache_logo(job)
    if not file_path or not file_path.exists():
        home_logger.error(f"File not found or invalid: {file_path}")
        abort(404)

    return send_file(file_path, mimetype="image/png")


@home_route.get('/')
@flask_error_handler
async def get_home():
    """Render home page with a default search term."""
    search_term = "home"
    response = await create_context(search_term)
    if response is None:
        return await not_found(search_term)
    return response

@home_route.get('/about')
@flask_error_handler
async def about():
    """Render the about page."""
    seo = await create_tags(search_term="about")
    return render_template('about.html', seo=seo, term="about")


@home_route.get('/contact')
@flask_error_handler
async def contact():
    """Render the contact page."""
    seo = await create_tags(search_term="contact")
    return render_template('contact.html', seo=seo, term="contact")


@home_route.get('/terms')
@flask_error_handler
async def terms():
    """Render the terms page."""
    seo = await create_tags(search_term="terms")
    return render_template('terms.html', seo=seo, term="terms")


@home_route.get('/sister-sites')
@flask_error_handler
async def sister_sites():
    """Render the sister sites page."""
    seo = await create_tags(search_term="sister-sites")
    return render_template('sisters.html', seo=seo, term="sister-sites")


@home_route.get('/faq')
@flask_error_handler
async def faq():
    """Render the FAQ page."""
    seo = await create_tags(search_term="FAQ")
    return render_template('faq.html', seo=seo, term="FAQ")


@home_route.get('/linkedin-learning')
@flask_error_handler
async def linkedin_learning():
    """Render the LinkedIn Learning page."""
    seo = await create_tags(search_term="LinkedIn Learning")
    return render_template('linkedin.html', seo=seo, term="LinkedIn Learning")


@home_route.post('/job-notifications/<string:search_term>')
@flask_error_handler
async def email_me(search_term: str):
    """Process job notification email subscription."""
    page = int(request.args.get('page', 1))
    try:
        notifications = CreateNotifications(**request.form)
        notifications.topic = search_term
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
@flask_error_handler
async def verify_email(verification_id: str):
    """Verify email for job notifications."""
    email = request.args.get("email")
    if not email:
        flash("Unable to verify Email Address", "danger")
        return redirect(url_for('home.get_home'), code=302)

    if await notifications_controller.check_verification(verification_id=verification_id, email=email):
        flash("You have successfully been added to our job alerts service", "success")
        return redirect(url_for('home.get_home'), code=302)

    flash("Unfortunately we could not verify your email address; please try again", "danger")
    return redirect(url_for('home.get_home'), code=302)


@home_route.get('/apply/<string:job_ref>')
@flask_error_handler
async def apply_for_job(job_ref: str):
    """Redirect to external job application page."""
    job = scrapper.jobs.get(job_ref)
    return redirect_apply_page(job)

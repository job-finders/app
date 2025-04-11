import math
import random
from pathlib import Path

import requests
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, send_file
from pydantic import ValidationError

from src.database.models import Job
from src.database.models.notifications import CreateNotifications
from src.database.models.seo import create_tags
from src.database.sql.notifications import NotificationsORM
from src.logger import init_logger
from src.main import scrapper, notifications_controller
from src.utils import format_title

home_route = Blueprint('home', __name__)
home_logger = init_logger("home_logger")

# Setup media directory for logo caching using pathlib
CURRENT_FILE = Path(__file__).resolve()
MEDIA_DIR = CURRENT_FILE.parents[2] / "media" / "logos"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_and_cache_logo(job: Job) -> Path | None:
    """Fetches the job logo and caches it locally.

    :param job: The job instance containing logo_link and job_ref.
    :return: The Path object to the logo file if available, otherwise None.
    """
    if not job.logo_link:
        return None

    file_path = MEDIA_DIR / f"{job.job_ref}.png"
    if file_path.exists():
        home_logger.info(f"Logo already exists: {file_path}")
        return file_path

    try:
        response = requests.get(job.logo_link, timeout=5)
        response.raise_for_status()
        file_path.parent.mkdir(exist_ok=True, parents=True)
        file_path.write_bytes(response.content)
        home_logger.info(f"Logo fetched and saved: {file_path}")
        return file_path
    except requests.RequestException as e:
        home_logger.error(f"Failed to fetch logo: {e}")
    except Exception as e:
        home_logger.error(f"An unexpected error occurred: {e}")
    return None


def load_affiliate_templates(directory: str = "template/affiliates/amazon") -> list[str]:
    """Load affiliate HTML templates from a specific directory.

    :param directory: Directory containing affiliate HTML templates.
    :return: A list of relative template paths.
    """
    templates = []
    template_dir = Path(directory)
    if not template_dir.exists():
        home_logger.warning(f"Directory '{directory}' not found.")
        return templates

    for file in template_dir.iterdir():
        if file.is_file() and file.suffix == ".html":
            # Generate relative path from the 'template' directory
            relative_path = file.relative_to(Path("template"))
            templates.append(str(relative_path))
    return templates


def search_term_matches_any_field(job: Job, search_term: str) -> bool:
    """Check whether the search term is present in any of the job's string fields.

    :param job: A Job instance.
    :param search_term: The term to search for.
    :return: True if found in any field, otherwise False.
    """
    fields = [
        job.location,
        job.search_term,
        job.title,
        job.job_link,
        job.description,
        job.company_name,
        job.desired_skills,
    ]
    return any(field_contains_search_term(field, search_term) for field in fields)


def field_contains_search_term(field: str | list[str] | None, search_term: str) -> bool:
    """Check if a field (string or list of strings) contains the search term.

    :param field: A string or list of strings.
    :param search_term: The term to search for.
    :return: True if found, otherwise False.
    """
    if field is None:
        return False
    search_term_lower = search_term.lower()
    if isinstance(field, list):
        return any(search_term_lower in term.lower() for term in field if isinstance(term, str))
    if isinstance(field, str):
        return search_term_lower in field.lower()
    return False


async def create_common_context(search_term: str, job_list: list[Job], page: int, per_page: int) -> dict:
    """Create a base context dictionary for templates.

    :param search_term: The search term used.
    :param job_list: The full list of matching jobs.
    :param page: The current page number.
    :param per_page: Jobs per page.
    :return: A context dictionary for the template.
    """
    # Get paginated results
    start_idx = (page - 1) * per_page
    jobs_paginated = job_list[start_idx: start_idx + per_page]

    search_terms: list[str] = scrapper.search_terms
    seo = await create_tags(search_term=search_term)

    try:
        current_index = search_terms.index(search_term)
        previous_term = search_terms[current_index - 1] if current_index > 0 else search_terms[-1]
        next_term = search_terms[current_index + 1] if current_index < len(search_terms) - 1 else search_terms[0]
    except ValueError:
        # Fallback if search_term is not found in scrapper.search_terms
        previous_term = "programming"
        next_term = "information-technology"

    affiliate_templates = load_affiliate_templates()
    affiliate_template = random.choice(affiliate_templates) if affiliate_templates else None

    return dict(
        term=search_term,
        previous_term=previous_term,
        next_term=next_term,
        job_list=jobs_paginated,
        search_terms=search_terms,
        seo=seo,
        current_page=page,
        total_pages=math.ceil(len(job_list) / per_page),
        affiliate_template=affiliate_template,
    )


async def create_context(search_term: str, page: int = 1, per_page: int = 10):
    """
    Create context for jobs strictly matching the search term in the job record.

    :param search_term: The search term.
    :param page: Page number.
    :param per_page: Number of jobs per page.
    :return: Rendered template response.
    """
    # Validate search term before filtering
    if search_term not in scrapper.search_terms:
        return None

    jobs_filtered = [job for job in scrapper.jobs.values() if job.search_term.casefold() == search_term.casefold()]
    context = await create_common_context(search_term, jobs_filtered, page, per_page)
    return render_template('index.html', **context)


async def create_search_context(search_term: str, page: int = 1, per_page: int = 10):
    """
    Create context for jobs where the search term can match any field.

    :param search_term: The search term.
    :param page: Page number.
    :param per_page: Number of jobs per page.
    :return: Rendered template response.
    """
    jobs_filtered = [job for job in scrapper.jobs.values() if search_term_matches_any_field(job, search_term)]
    context = await create_common_context(search_term, jobs_filtered, page, per_page)
    return render_template('index.html', **context)


async def not_found(search_term: str):
    """Render a 404 error page when job listings could not be found.

    :param search_term: The search term used.
    :return: (rendered error page, status code)
    """
    error = dict(message=f"Unable to retrieve job listings for: {search_term}", title="404 Not Found")
    return render_template('error.html', error=error), 404


def redirect_apply_page(job: Job):
    """Redirects to the job's apply page if available.

    :param job: A Job instance.
    :return: A redirect response.
    """
    if not job.job_link:
        return redirect(url_for('home.get_home'), code=302)
    return redirect(job.job_link, code=200)


# Route definitions

@home_route.get("/media/logos/<job_ref>.png")
def serve_logo(job_ref: str):
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
async def get_home():
    """Render home page with a default search term."""
    search_term = "information-technology"
    response = await create_context(search_term)
    if response is None:
        return await not_found(search_term)
    return response


@home_route.get('/jobs/<string:search_term>')
async def job_search(search_term: str):
    """Render job search results by search term."""
    page = int(request.args.get('page', 1))
    response = await create_search_context(search_term=search_term, page=page)
    if response is None:
        return await not_found(search_term)
    return response


@home_route.get('/search')
async def search_bar():
    """Render search results from a query submitted via search bar."""
    search_term = request.args.get('search_term')
    if not search_term:
        return redirect(url_for('home.get_home'), code=302)
    page = int(request.args.get('page', 1))
    response = await create_search_context(search_term=search_term, page=page)
    if response is None:
        return await not_found(search_term)
    return response


async def sub_job_detail(job: Job):
    """Render detailed job view with SEO tags and similar jobs."""
    seo = await create_tags(search_term=job.title)
    similar_jobs = await scrapper.similar_jobs(search_term=job.search_term, title=job.title)
    home_logger.info(f"Similar Jobs: {similar_jobs}")
    affiliate_template = random.choice(load_affiliate_templates())
    context = dict(term=job.title, job=job, search_terms=scrapper.search_terms, similar_jobs=similar_jobs,
                   seo=seo, affiliate_template=affiliate_template)

    return render_template('job.html', **context)


@home_route.get('/job/<string:reference>')
async def job_detail(reference: str):
    """Display job details identified by job reference."""
    job: Job = await scrapper.job_search(job_reference=reference)
    if isinstance(job, Job) and job.title.strip():
        return await sub_job_detail(job)
    return redirect(url_for('home.get_home'))

@home_route.get('/search/job/<string:slug>')
async def job_slug(slug: str):
    """Display job details identified by its slug."""
    job: Job = await scrapper.search_by_slug(slug=slug)
    return await sub_job_detail(job)


@home_route.get('/about')
async def about():
    """Render the about page."""
    seo = await create_tags(search_term="about")
    return render_template('about.html', seo=seo, term="about")


@home_route.get('/contact')
async def contact():
    """Render the contact page."""
    seo = await create_tags(search_term="contact")
    return render_template('contact.html', seo=seo, term="contact")


@home_route.get('/terms')
async def terms():
    """Render the terms page."""
    seo = await create_tags(search_term="terms")
    return render_template('terms.html', seo=seo, term="terms")


@home_route.get('/sister-sites')
async def sister_sites():
    """Render the sister sites page."""
    seo = await create_tags(search_term="sister-sites")
    return render_template('sisters.html', seo=seo, term="sister-sites")


@home_route.get('/faq')
async def faq():
    """Render the FAQ page."""
    seo = await create_tags(search_term="FAQ")
    return render_template('faq.html', seo=seo, term="FAQ")


@home_route.get('/linkedin-learning')
async def linkedin_learning():
    """Render the LinkedIn Learning page."""
    seo = await create_tags(search_term="LinkedIn Learning")
    return render_template('linkedin.html', seo=seo, term="LinkedIn Learning")


@home_route.post('/job-notifications/<string:search_term>')
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
async def apply_for_job(job_ref: str):
    """Redirect to external job application page."""
    job = scrapper.jobs.get(job_ref)
    return redirect_apply_page(job)

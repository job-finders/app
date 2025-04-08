import math
import os
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

# 获取当前文件的绝对路径
current_file = Path(__file__).resolve()

# 定义媒体文件的根目录（相对于当前文件）
MEDIA_DIR = current_file.parent.parent.parent / "media" / "logos"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
# os.makedirs(MEDIA_DIR, exist_ok=True)



def fetch_and_cache_logo(job):
    if not job.logo_link:
        return None

    file_path = MEDIA_DIR / f"{job.job_ref}.png"
    normalized_path = os.path.normpath(str(file_path))
    if os.path.exists(normalized_path):
        print(f"Logo already exists: {normalized_path}")
        return Path(normalized_path)  # 返回 Path 对象

    try:
        response = requests.get(job.logo_link, timeout=5)
        response.raise_for_status()

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(response.content)
        print(f"Logo fetched and saved: {file_path}")
        return file_path  # 返回 Path 对象
    except requests.RequestException as e:
        print(f"Failed to fetch logo: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

async def create_context(search_term: str, page: int = 1, per_page: int = 10):
    """
    Create common context for jobs with paged results.

    :param search_term: The search term for job listings.
    :param page: The page number of results to display (default is 1).
    :param per_page: The number of job listings per page (default is 10).
    :return: The context for rendering the template.
    """
    if search_term not in scrapper.search_terms:
        # TODO - return an error here preferably with an error page
        return None

    # Filter jobs based on the search term
    job_list = [job for job in scrapper.jobs.values() if job.search_term.casefold() == search_term.casefold()]

    # Calculate the start and end indices for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    # Slice the job list to get the jobs for the current page
    job_list_page = job_list[start_idx:end_idx]

    search_terms: list[str] = scrapper.search_terms

    seo = await create_tags(search_term=search_term)
    current_index: int = search_terms.index(search_term)
    previous_term: str = search_terms[current_index - 1] if current_index > 0 else search_terms[len(search_terms) - 1]
    next_term: str = search_terms[current_index + 1] if current_index < len(search_terms) - 1 else search_terms[0]

    context = dict(
        term=search_term,
        previous_term=previous_term,
        next_term=next_term,
        job_list=job_list_page,  # Use the sliced job list for the current page
        search_terms=search_terms,
        seo=seo,
        current_page=page,  # Include the current page number in the context
        total_pages=math.ceil(len(job_list) / per_page)  # Calculate the total number of pages
    )

    return render_template('index.html', **context)


async def create_search_context(search_term: str, page: int = 1, per_page: int = 10):
    """
    Create common context for jobs with paged results.

    :param search_term: The search term for job listings.
    :param page: The page number of results to display (default is 1).
    :param per_page: The number of job listings per page (default is 10).
    :return: The context for rendering the template.
    """
    AFFILIATE_TEMPLATES = [
        "affiliates/amazon/how_to_get_a_job_in_it.html",
        "affiliates/amazon/2_hour_job_search.html",
        "affiliates/amazon/it_career_jumpstart.html",
    ]

    # Filter jobs based on the search term matching any string field
    job_list = [job for job in scrapper.jobs.values() if
                search_term_matches_any_field(job, search_term)]

    # Calculate the start and end indices for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    # Slice the job list to get the jobs for the current page
    job_list_page = job_list[start_idx:end_idx]

    search_terms: list[str] = scrapper.search_terms

    seo = await create_tags(search_term=search_term)
    if search_term in search_terms:
        current_index: int = search_terms.index(search_term)
        previous_term: str = search_terms[current_index - 1] if current_index > 0 else search_terms[
            len(search_terms) - 1]
        next_term: str = search_terms[current_index + 1] if current_index < len(search_terms) - 1 else search_terms[0]
    else:
        current_index = 0
        previous_term = "programming"
        next_term = "information-technolodgy"

    context = dict(
        term=search_term,
        previous_term=previous_term,
        next_term=next_term,
        job_list=job_list_page,  # Use the sliced job list for the current page
        search_terms=search_terms,
        seo=seo,
        current_page=page,  # Include the current page number in the context
        total_pages=math.ceil(len(job_list) / per_page),  # Calculate the total number of pages
        affiliate_template=random.choice(AFFILIATE_TEMPLATES)
    )

    return render_template('index.html', **context)


def search_term_matches_any_field(job: Job, search_term: str):
    # Check if the search term matches any string field of the job
    if field_contains_search_term(field=job.location, search_term=search_term):
        return True
    if field_contains_search_term(field=job.search_term, search_term=search_term):
        return True
    if field_contains_search_term(field=job.title, search_term=search_term):
        return True
    if field_contains_search_term(field=job.job_link, search_term=search_term):
        return True
    if field_contains_search_term(field=job.description, search_term=search_term):
        return True
    if field_contains_search_term(field=job.company_name, search_term=search_term):
        return True
    if field_contains_search_term(field=job.desired_skills, search_term=search_term):
        return True
    return False


def field_contains_search_term(field: str | list, search_term: str):
    # Check if the field contains the search term
    if isinstance(field, list):
        for term in field:
            if search_term.lower() in term.lower():
                return True

    if isinstance(field, str):
        return search_term.lower() in field.lower()
    return False


async def not_found(search_term: str):
    error_message = f"Unable to retrieve job listings for :  {search_term}"
    status = "404 Not Found"
    error = dict(message=error_message, title=status)
    return render_template('error.html', error=error), 404

@home_route.get("/media/logos/<job_ref>.png")
def serve_logo(job_ref):
    # 您需要一种方法来通过引用获取 Job 实例
    job = scrapper.jobs.get(job_ref)

    if not job:
        print(f"Job not found: {job_ref}")
        abort(404)

    file_path = fetch_and_cache_logo(job)
    if not file_path or not isinstance(file_path, Path) or not file_path.exists():
        print(f"File not found: {file_path}")
        abort(404)

    return send_file(file_path, mimetype="image/png")


@home_route.get('/')
async def get_home():
    """
        home directory will start with information tech jobs
    :return:
    """
    search_term = "information-technology"
    response = await create_context(search_term)
    if response is None:
        return await not_found(search_term=search_term)

    return response


@home_route.get('/jobs/<string:search_term>')
async def job_search(search_term: str):
    page = int(request.args.get('page', 1))
    response = await create_search_context(search_term=search_term, page=page)
    if response is None:
        return await not_found(search_term=search_term)

    return response


@home_route.get('/search')
async def search_bar():
    """
        allows the front page to display a search bar
        which enables our clients to search for jobs using any term
        the results will search on any field
    :return:
    """
    search_term = request.args.get('search_term')
    if search_term is None:
        return redirect(url_for('home.get_home'), code=302)

    page = int(request.args.get('page', 1))
    response = await create_search_context(search_term=search_term, page=page)
    if response is None:
        return await not_found(search_term=search_term)

    return response


async def sub_job_detail(job):
    term = job.title
    seo = await create_tags(search_term=term)
    similar_jobs = await scrapper.similar_jobs(search_term=job.search_term, title=job.title)
    home_logger.info(f"Similar Jobs : {similar_jobs}")
    context = dict(term=term, job=job, search_terms=scrapper.search_terms, similar_jobs=similar_jobs, seo=seo)
    return render_template('job.html', **context)


@home_route.get('/job/<string:reference>')
async def job_detail(reference: str):
    job: Job = await scrapper.job_search(job_reference=reference)

    return await sub_job_detail(job)


@home_route.get('/search/job/<string:slug>')
async def job_slug(slug: str):
    job: Job = await scrapper.search_by_slug(slug=slug)

    return await sub_job_detail(job)


@home_route.get('/about')
async def about():
    """
    :return:
    """
    seo = await create_tags(search_term="about")
    context = dict(seo=seo, term="about")
    return render_template('about.html', **context)


@home_route.get('/contact')
async def contact():
    """
    :return:
    """
    seo = await create_tags(search_term="contact")
    context = dict(seo=seo, term="contact")
    return render_template('contact.html', **context)


@home_route.get('/terms')
async def terms():
    """
    :return:
    """
    seo = await create_tags(search_term="terms")
    context = dict(seo=seo, term="terms")
    return render_template('terms.html', **context)


@home_route.get('/sister-sites')
async def sister_sites():
    """
    :return:
    """
    seo = await create_tags(search_term="sister-sites")
    context = dict(seo=seo, term="sister-sites")
    return render_template('sisters.html', **context)


@home_route.get('/faq')
async def faq():
    """
    :return:
    """
    seo = await create_tags(search_term="FAQ")
    context = dict(seo=seo, term="FAQ")
    return render_template('faq.html', **context)


@home_route.get('/linkedin-learning')
async def linkedin_learning():
    """
    :return:
    """
    seo = await create_tags(search_term="LinkedIn Learning")
    context = dict(seo=seo, term="LinkedIn Learning")
    return render_template('linkedin.html', **context)


@home_route.post('/job-notifications/<string:search_term>')
async def email_me(search_term: str):
    page = int(request.args.get('page', 1))
    try:
        notifications = CreateNotifications(**request.form)
        notifications.topic = search_term
        created_notification = await notifications_controller.create_notification_email(notification=notifications)

        if not created_notification:
            flash(
                message="There was a problem adding you to the email list you may already be added please verify your email - also note that we cannot add you to more than one list at a time",
                category="danger")
            return redirect(url_for('home.get_home'), code=302)

        email_sent = await notifications_controller.send_notification_verification_email(
            notification=created_notification)

    except ValidationError as e:
        flash(message="There was a problem creating your email alert please try again later", category="danger")
        return redirect(url_for('home.get_home'), code=302)
    except Exception as e:
        flash(message="There was a problem creating your email alert please try again later", category="danger")
        return redirect(url_for('home.get_home'), code=302)

    flash(f"Please check your email address for our verification email, "
          f"verify your email so we can send you jobs about {format_title(search_term)}", category="success")

    response = await create_context(search_term=search_term, page=page)
    if response is None:
        return await not_found(search_term=search_term)

    return response


@home_route.get('/email-verification/<string:verification_id>')
async def verify_email(verification_id: str):
    """

    :param verification_id:
    :return:
    """
    email = request.args.get("email")
    if not email:
        flash(message="Unable to verify Email Address", category="danger")
        return redirect(url_for('home.get_home'), code=302)

    is_verified = await notifications_controller.check_verification(verification_id=verification_id, email=email)
    if is_verified:
        flash(message="You have successfully been added into our job alerts services", category="success")
        return redirect(url_for('home.get_home'), code=302)

    flash(message="Unfortunately we could not verify your email address please try again", category="danger")
    return redirect(url_for('home.get_home'), code=302)



def redirect_apply_page(job: Job):
    if not job.job_link:
        return redirect(url_for('home.get_home'), code=302)

    return redirect(job.job_link, code=200)

@home_route.get('/apply/<string:job_ref>')
async def apply_for_job(job_ref: str):
    """

    :return:
    """
    job = scrapper.jobs.get(job_ref)
    return redirect_apply_page(job=job)

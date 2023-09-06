import math

from flask import Blueprint, render_template, send_from_directory, request, flash, redirect, url_for
from pydantic import ValidationError

from src.database.models.notifications import Notifications, CreateNotifications
from src.database.models import Job, SEO
from src.logger import init_logger
from src.main import scrapper, notifications_controller
from src.utils import static_folder, format_title

home_route = Blueprint('home', __name__)
home_logger = init_logger("home_logger")


async def create_tags(search_term: str) -> SEO:
    """

    :param search_term:
    :return:
    """
    title = f"{search_term} Jobs"
    description = f"jobfinders.site {search_term} Jobs"
    term_words = ",".join(format_title(search_term).split(" "))
    keywords = f"JobFinders, {term_words}"
    seo_dict = dict(title=title, description=description, keywords=keywords)
    return SEO(**seo_dict)


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


async def not_found(search_term: str):
    error_message = f"Unable to retrieve job listings for :  {search_term}"
    status = "404 Not Found"
    error = dict(message=error_message, title=status)
    return render_template('error.html', error=error), 404


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
    response = await create_context(search_term=search_term, page=page)
    if response is None:
        return await not_found(search_term=search_term)

    return response


@home_route.get('/job-search/<string:search_term>')
async def search_bar(search_term: str):
    """
        allows the front page to display a search bar
        which enables our clients to search for jobs using any term
        the results will search on any field
    :param search_term:
    :return:
    """
    pass


@home_route.get('/job/<string:reference>')
async def job_detail(reference: str):
    job: Job = await scrapper.job_search(job_reference=reference)

    term = job.title
    seo = await create_tags(search_term=term)
    similar_jobs = await scrapper.similar_jobs(search_term=job.search_term, title=job.title)
    home_logger.info(f"Similar Jobs : {similar_jobs}")
    context = dict(term=term, job=job, search_terms=scrapper.search_terms, similar_jobs=similar_jobs, seo=seo)
    return render_template('job.html', **context)


# @home_route.get('/sw-check-permissions-a0d20.js')
# async def get_pro_push_code():
#     """
#         will serve pro push code from static folder
#     :return:
#     """
#     return send_from_directory(static_folder(), 'js/sw-check-permissions-a0d20.js')


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
        created_notification = await notifications_controller.create_notification_email(notification=notifications)
        email_sent = await notifications_controller.send_notification_verification_email(notification=created_notification)
    except ValidationError as e:
        pass

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


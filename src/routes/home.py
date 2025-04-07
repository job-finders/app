import math

from flask import Blueprint, render_template, send_from_directory, request, flash, redirect, url_for
from pydantic import ValidationError

from src.database.models.seo import create_tags
from src.database.models.notifications import Notifications, CreateNotifications
from src.database.models import Job, SEO
from src.logger import init_logger
from src.main import scrapper, notifications_controller
from src.utils import static_folder, format_title

home_route = Blueprint('home', __name__)
home_logger = init_logger("home_logger")


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
        total_pages=math.ceil(len(job_list) / per_page)  # Calculate the total number of pages
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


@home_route.get('/send-job-notifications')
async def send_job_notifications():
    """
    This route sends job alerts to verified users based on their topic of interest.
    Intended to be triggered by a scheduled job.
    """
    from src.main import scrapper  # Ensure scrapper is accessible

    try:
        with notifications_controller.get_session() as session:
            notifications = session.query(NotificationsORM).filter(NotificationsORM.is_verified == True).all()

        if not notifications:
            home_logger.info("No verified notifications found.")
            return {"status": "ok", "message": "No verified users to notify."}

        for n in notifications:
            topic = n.topic
            jobs = [
                job for job in scrapper.jobs.values()
                if job.search_term.casefold() == topic.casefold()
            ][:5]  # Limit to 5 jobs

            if not jobs:
                home_logger.info(f"No jobs found for topic: {topic}")
                continue

            # Create context and render email
            job_links = [
                {
                    "title": job.title,
                    "company": job.company_name,
                    "location": job.location,
                    "link": url_for('home.job_detail', reference=job.reference, _external=True)
                }
                for job in jobs
            ]

            email_html = render_template("email/job_alert.html", topic=topic, job_links=job_links)
            subject = f"JobFinders.site - New {format_title(topic)} Job Opportunities"
            msg = EmailModel(subject_=subject, to_=n.email, html_=email_html)

            home_logger.info(f"Sending job alert to: {n.email}")
            await send_mail.send_mail_resend(email=msg)

        return {"status": "ok", "message": "Job alerts sent to verified users."}

    except Exception as e:
        home_logger.error(f"Failed to send job notifications: {e}")
        return {"status": "error", "message": "Failed to send job notifications."}

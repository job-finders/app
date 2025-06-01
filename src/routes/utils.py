import math
import random
from datetime import datetime
from pathlib import Path

import requests
from flask import render_template, redirect, url_for

from src.database.models.users import User
from src.database.models import Job
from src.database.models.seo import create_seo_tags_for_job, create_tags
from src.logger import init_logger
from src.main import junction_scrapper, job_search_controller

utils_logger = init_logger("utils_logger")

CURRENT_FILE = Path(__file__).resolve()
MEDIA_DIR = CURRENT_FILE.parents[2] / "media" / "logos"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
SOUTH_AFRICA_PROVINCES = {
    "Eastern Cape": sorted([
        "Bhisho", "East London", "Grahamstown", "King William’s Town", "Mthatha", "Port Alfred", "Port Elizabeth", "Queenstown"
    ]),
    "Free State": sorted([
        "Bethlehem", "Bloemfontein", "Harrismith", "Kroonstad", "Parys", "Welkom"
    ]),
    "Gauteng": sorted([
        "Alberton", "Benoni", "Boksburg", "Brakpan", "Centurion", "Germiston", "Johannesburg", "Krugersdorp", "Midrand", "Pretoria", "Randburg", "Roodepoort", "Sandton", "Soweto", "Springs", "Vanderbijlpark", "Vereeniging"
    ]),
    "KwaZulu-Natal": sorted([
        "Durban", "Empangeni", "Eshowe", "Ladysmith", "Newcastle", "Pietermaritzburg", "Port Shepstone", "Richards Bay", "Stanger", "Ulundi", "Umlazi"
    ]),
    "Limpopo": sorted([
        "Giyani", "Lebowakgomo", "Louis Trichardt", "Modimolle", "Mokopane", "Musina", "Phalaborwa", "Polokwane", "Thabazimbi", "Tzaneen"
    ]),
    "Mpumalanga": sorted([
        "Barberton", "Bethal", "Ermelo", "Lydenburg", "Middelburg", "Nelspruit", "Secunda", "Standerton", "Witbank"
    ]),
    "North West": sorted([
        "Brits", "Klerksdorp", "Lichtenburg", "Mahikeng", "Potchefstroom", "Rustenburg", "Vryburg", "Zeerust"
    ]),
    "Northern Cape": sorted([
        "De Aar", "Douglas", "Kimberley", "Kuruman", "Port Nolloth", "Springbok", "Upington"
    ]),
    "Western Cape": sorted([
        "Bellville", "Cape Town", "George", "Knysna", "Mossel Bay", "Paarl", "Stellenbosch", "Worcester"
    ])
}

TOWN_TO_PROVINCE = {
    town.lower(): province
    for province, towns in SOUTH_AFRICA_PROVINCES.items()
    for town in towns
}
categories = [
    {
        "name": "Information Technology",
        "slug": "information-technology",
        "description": "Opportunities in software development, network administration, technical support, and more in IT."
    },
    {
        "name": "Office Admin",
        "slug": "office-admin",
        "description": "Job opportunities in administrative support, secretarial roles, and office management."
    },
    {
        "name": "Agriculture",
        "slug": "agriculture",
        "description": "Positions in farming, agri-business, agricultural management, and related industries."
    },
    {
        "name": "Engineering",
        "slug": "engineering",
        "description": "Careers across various engineering disciplines including mechanical, electrical, and civil engineering."
    },
    {
        "name": "Building Construction",
        "slug": "building-construction",
        "description": "Jobs in the construction industry, covering roles from project management to skilled trades."
    },
    {
        "name": "Business Management",
        "slug": "business-management",
        "description": "Roles in corporate leadership, operations management, and strategic planning."
    },
    {
        "name": "Cleaning Maintenance",
        "slug": "cleaning-maintenance",
        "description": "Opportunities in facility management, cleaning services, and general maintenance."
    },
    {
        "name": "Community Social Welfare",
        "slug": "community-social-welfare",
        "description": "Jobs in non-profit organizations, social work, and community development initiatives."
    },
    {
        "name": "Education",
        "slug": "education",
        "description": "Teaching positions, academic support roles, and jobs in educational administration."
    },
    {
        "name": "Nursing",
        "slug": "nursing",
        "description": "Healthcare roles focused on nursing services, patient care, and clinical support."
    },
    {
        "name": "Finance",
        "slug": "finance",
        "description": "Positions in banking, accounting, financial analysis, and financial management."
    },
    {
        "name": "Programming",
        "slug": "programming",
        "description": "Opportunities in software engineering, web development, coding, and application development."
    }
]

def create_homepage_tags() -> dict:
    return {
        "title": "Find Jobs in South Africa - JobFinders.site",
        "description": "Explore thousands of the latest job listings across South Africa. Apply now with JobFinders.site and land your dream job today!",
        "keywords": "jobs in South Africa, job listings, careers, employment, JobFinders",
        "canonical": "https://jobfinders.site/",
        "og_title": "Find Jobs in South Africa - JobFinders.site",
        "og_description": "Your one-stop job search engine. Discover new opportunities near you.",
        "og_url": "https://jobfinders.site/",
        "og_type": "website",
    }


def fetch_and_cache_logo(job: Job) -> Path | None:
    """Fetches the job logo and caches it locally.

    :param job: The job instance containing logo_link and job_ref.
    :return: The Path object to the logo file if available, otherwise None.
    """
    if not job.logo_link:
        return None

    file_path = MEDIA_DIR / f"{job.job_ref}.png"
    if file_path.exists():
        utils_logger.info(f"Logo already exists: {file_path}")
        return file_path

    try:
        response = requests.get(job.logo_link, timeout=5)
        response.raise_for_status()
        file_path.parent.mkdir(exist_ok=True, parents=True)
        file_path.write_bytes(response.content)
        utils_logger.info(f"Logo fetched and saved: {file_path}")
        return file_path
    except requests.RequestException as e:
        utils_logger.error(f"Failed to fetch logo: {e}")
    except Exception as e:
        utils_logger.error(f"An unexpected error occurred: {e}")
    return None

def load_affiliate_templates(directory: str = "template/affiliates/amazon") -> list[str]:
    """Load affiliate HTML templates from a specific directory.

    :param directory: Directory containing affiliate HTML templates.
    :return: A list of relative template paths.
    """
    templates = []
    template_dir = Path(directory)
    if not template_dir.exists():
        utils_logger.warning(f"Directory '{directory}' not found.")
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

def count_jobs_per_category(jobs: list[Job]) -> dict:
    """Count how many jobs are in each category slug."""
    counts = {}
    for job in jobs:
        slug = job.search_term.lower().strip()  # or use job.category if available
        counts[slug] = counts.get(slug, 0) + 1
    return counts



async def create_search_context(user: User, search_term: str, page: int = 1, per_page: int = 10):
    """
    Create context for jobs where the search term can match any field.

    :param search_term: The search term.
    :param page: Page number.
    :param per_page: Number of jobs per page.
    :return: Rendered template response.
    """
    jobs_filtered = [job for job in junction_scrapper.job_cache.values() if search_term_matches_any_field(job, search_term)]
    context = await create_common_context(search_term, jobs_filtered, page, per_page)
    context.update(current_user=user)
    return render_template('job_listing.html', **context)



async def create_common_context(search_term: str, job_list: list[Job], page: int, per_page: int) -> dict:
    start_idx = (page - 1) * per_page
    jobs_paginated = job_list[start_idx: start_idx + per_page]
    provinces = list(SOUTH_AFRICA_PROVINCES.keys())
    search_terms: list[str] = junction_scrapper.search_terms

    # Count job postings by category
    job_counts = count_jobs_per_category(list(junction_scrapper.job_cache.values()))

    # Enrich categories with job_count
    enriched_categories = []
    for cat in categories:
        slug = cat["slug"].lower().strip()
        cat["job_count"] = str(job_counts.get(slug, 0))
        enriched_categories.append(cat)

    # SEO
    if not search_term or search_term.lower() in ["", "home", "homepage"]:
        seo = create_homepage_tags()
    else:
        seo = await create_tags(search_term=search_term)

    try:
        current_index = search_terms.index(search_term)
        previous_term = search_terms[current_index - 1] if current_index > 0 else search_terms[-1]
        next_term = search_terms[current_index + 1] if current_index < len(search_terms) - 1 else search_terms[0]
    except ValueError:
        previous_term = "programming"
        next_term = "information-technology"

    affiliate_templates = load_affiliate_templates()
    affiliate_template = random.choice(affiliate_templates) if affiliate_templates else None
    current_year = str(datetime.now().year)
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
        provinces=provinces,
        categories=enriched_categories,  # ✅ Pass the enriched list
        current_year=current_year
    )

async def create_context(user:User, search_term: str, page: int = 1, per_page: int = 10):
    """
    Create context for jobs strictly matching the search term in the job record.

    :param user:
    :param search_term: The search term.
    :param page: Page number.
    :param per_page: Number of jobs per page.
    :return: Rendered template response.
    """
    # Validate search term before filtering
    if search_term not in junction_scrapper.search_terms and search_term is not "home":
        return None

    category_search = await job_search_controller.search_jobs_by_category(category=search_term, page=page, page_size=per_page)
    jobs_list = category_search.get('jobs') if category_search else []
    context = await create_common_context(search_term=search_term, job_list=jobs_list,
                                          page=page, per_page=per_page)
    if user:
        context.update(current_user=user)
    else:
        context.update(current_user=None)

    if search_term == "home":
        return render_template('index.html', **context)
    elif search_term in junction_scrapper.search_terms:
        return render_template('job_listing.html', **context)
    return None


async def not_found(search_term: str):
    """Render a 404 error page when job listings could not be found.

    :param search_term: The search term used.
    :return: (rendered error page, status code)
    """
    message = f"Unable to retrieve job listings for: {search_term}"
    utils_logger.error(message)

    context = {
        "message": message,
        "title": "404 Not Found",
        "seo": {
            "title": f"No Jobs Found - {search_term}",
            "description": f"We couldn’t find any job listings for {search_term}. Try searching again.",
            "keywords": "jobs, careers, not found, job search"
        }
    }
    return render_template("error.html", **context), 404


async def gone(user:User, search_term: str):
    """Render a 410 Gone page for permanently removed job listings."""
    message = f"The page for '{search_term}' has been permanently removed."
    utils_logger.info(message)

    context = {

        "current_user": user,
        "message": message,
        "title": "410 Gone",
        "seo": {
            "title": f"Job Page Removed - {search_term}",
            "description": f"The job listing or page for {search_term} is no longer available.",
            "keywords": "job removed, expired job, job no longer available"
        }
    }

    return render_template("error.html", **context), 410


async def sub_job_detail(user: User, job: Job):
    """Render detailed job view with SEO tags and similar jobs."""
    seo = await create_seo_tags_for_job(job=job)
    similar_jobs = await junction_scrapper.similar_jobs(search_term=job.search_term, title=job.title)
    # utils_logger.info(f"Similar Jobs: {similar_jobs}")
    affiliate_template = random.choice(load_affiliate_templates())

    context = dict(term=job.title, job=job, search_terms=junction_scrapper.search_terms, similar_jobs=similar_jobs,
                   seo=seo, affiliate_template=affiliate_template, current_user=user)

    return render_template('job.html', **context)

def redirect_apply_page(job: Job):
    """Redirects to the job's apply page if available.

    :param job: A Job instance.
    :return: A redirect response.
    """
    if not job.job_link:
        return redirect(url_for('home.get_home'), code=302)
    return redirect(job.job_link, code=200)

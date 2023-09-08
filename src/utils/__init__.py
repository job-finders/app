from os import path
import re
from datetime import date
from bs4 import BeautifulSoup


def static_folder() -> str:
    return path.join(path.dirname(path.abspath(__file__)), '../../static')


def template_folder() -> str:
    return path.join(path.dirname(path.abspath(__file__)), '../../template')


def format_title(title: str):
    if not title:
        return "-"
    return title.replace("-", " ").title()


def format_description(description: str):
    """
    Parse the input description and create paragraphs using HTML based on headings.

    :param description: The input job description text.
    :return: Formatted HTML representation of the description.
    """
    headings = [
        "ABOUT THE POSITION",
        "Job brief",
        "Job responsibilities",
        "Standards",
        "Performance Qualification",
        "Responsibilities",
        "Client Details",
        "Role Responsibilities",
        "Relevant Qualifications",
        "Experience",
        "Your Expertise",
        "Required Qualifications",
        "Personal Attributes",
        "Why work for us",
        "Responsibilities and work outputs",
        "Minimum requirements",
        "Skills",
        "Desired Skills",
        "Requirements",
        "Qualifications",
        "Knowledge and Experience",
        "About The Employer",
        "Desired Work Experience",
        "Desired Qualification Level"
    ]

    paragraphs = []
    current_heading = None

    for line in description.splitlines():
        line = line.strip()

        # Check if the line matches any of the headings
        if line.casefold() in headings:
            current_heading = line
        elif current_heading:
            # If there's a current heading, treat the line as content
            if line:
                paragraphs.append((current_heading, line))
        else:
            # If there's no current heading, treat the line as a regular paragraph
            if line:
                paragraphs.append(("paragraph", line))

    # Generate HTML paragraphs based on the parsed content
    html = ""
    for heading, content in paragraphs:
        if heading == "paragraph":
            html += f"<p>{content}</p>\n"
        else:
            html += f"<h2 class='card-title font-weight-bold'>{heading}</h2>\n<p>{content}</p>\n"

    return html


def _format_description(description: str):
    soup = BeautifulSoup(description, 'html.parser')
    headings = [
        "ABOUT THE POSITION",
        "Job brief",
        "Responsibilities",
        "Client Details",
        "Role Responsibilities",
        "Relevant Qualifications",
        "Experience",
        "Your Expertise",
        "Required Qualifications",
        "Personal Attributes",
        "Why work for us",
        "Responsibilities and work outputs",
        "Minimum requirements",
        "Skills",
        "Desired Skills",
        "Requirements",
        "Qualifications",
        "Knowledge and Experience",
        "About The Employer",
        "Desired Work Experience",
        "Desired Qualification Level"
    ]
    paragraphs = soup.find_all(['p', 'h2'])
    formatted_paragraphs = []

    for elem in paragraphs:
        if elem.name == 'h2':
            heading = elem.get_text(strip=True)
            if heading in headings:
                formatted_paragraphs.append(f"<h2 class='card-title font-weight-bold'>{heading}</h2>")
        elif elem.name == 'p':
            content = elem.get_text(strip=True)
            formatted_paragraphs.append(f"<p>{content}</p>")

    formatted_html = '\n'.join(formatted_paragraphs)
    return formatted_html


def format_reference(ref: str) -> str:
    """
    :param ref: The input reference string.
    :return: The formatted reference string with special characters removed.
    """
    special_chars = r'[!@#$%^&*()+=\[\]{}|;:",<>/`~]'

    ref_without_special = re.sub(special_chars, '', ref.replace(" ", "").lower())
    return ref_without_special


def number_days_to_expiry(updated_time: str, date_expires: date):
    """

    :param updated_time:
    :param date_expires:
    :return:
    """
    pass


def bootstrap_database():
    from src.database.sql.jobs import JobsORM
    from src.database.sql.notifications import NotificationsORM

    JobsORM.create_if_not_table()
    NotificationsORM.create_if_not_table()


def sanitize_filename(filename):
    # Remove or replace characters that are not suitable for filenames
    charset = "[\/:*?'<>|]{},. "
    for char in charset:
        filename = filename.replace(char, "")
    return filename.lower().strip()


def generate_cache_key(f, *args, **kwargs):
    # Construct the cache key using function name, args, and kwargs
    cache_key = f"{f.__name__}{kwargs}"
    return sanitize_filename(cache_key)



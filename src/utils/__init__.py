from os import path
import re
from datetime import date
from bs4 import BeautifulSoup
import os
from pathlib import Path

from pydantic import AwareDatetime
from werkzeug.utils import secure_filename
from datetime import datetime
from markupsafe import Markup
# Define the base directory for user data (for profile images and other files)
CURRENT_FILE = Path(__file__).resolve()
USERDATA_DIR = CURRENT_FILE.parents[2] / "userdata"
USERDATA_DIR.mkdir(parents=True, exist_ok=True)


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def save_file_to_storage(file, filename: str, allowed_extensions: set = None, subfolder: str = None) -> str:
    """
    Save the uploaded file to the userdata directory (or a subfolder) and return the file URL.

    - Validates the file extension based on provided allowed extensions.
    - Generates a unique filename using a timestamp to avoid conflicts.
    - Saves the file to the userdata directory (or the specified subfolder).
    - Returns the file path or URL.
    """
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}  # Default allowed extensions

    if not allowed_file(filename, allowed_extensions):
        raise ValueError(f"Invalid file format. Allowed formats are {', '.join(allowed_extensions)}.")

    # Determine the final folder path (userdata or a subfolder)
    folder_path = USERDATA_DIR
    if subfolder:
        folder_path = folder_path / subfolder
    folder_path.mkdir(exist_ok=True, parents=True)

    # Generate a unique filename using timestamp
    unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(filename)}"
    file_path = folder_path / unique_filename

    # Save the file to the defined path
    file.save(file_path)

    # Return the file URL or relative path
    return str(file_path)  # Or a URL, depending on your application structure


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



def sanitize_filename(filename):
    # Remove or replace characters that are not suitable for filenames
    charset = "[\/:*?'<>|]{},. "
    for char in charset:
        filename = filename.replace(char, "")
    return filename.lower().strip()




# app/template_filters.py
def intcomma(value):
    """
    Format a number with commas as thousands separators.

    Args:
        value: Number to format (int, float, or string representation of a number)

    Returns:
        Formatted string with commas, or original value if not a number
    """
    try:
        # Convert to float first to handle both ints and floats
        num = float(value)

        # Check if it's an integer (whole number)
        if num.is_integer():
            return "{:,}".format(int(num))
        else:
            # Format float with commas and 2 decimal places
            return "{:,.2f}".format(num)
    except (TypeError, ValueError):
        # Return original value if it can't be converted to a number
        return value

def datetimeformat(value: datetime):
    return value.isoformat()


def current_year() -> int:
    return datetime.now().year


# utils/filters.py
def number_format(value):
    """
    Jinja filter: 1234567 → '1 234 567'
    """
    if value is None:
        return ""
    try:
        value = int(value)
    except (ValueError, TypeError):
        return str(value)
    return f"{value:,.0f}".replace(",", " ")


from datetime import datetime, timezone


def parse_date_to_aware(date_str: str) -> AwareDatetime:
    return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)


def split_csv(field: str) -> list[str]:
    return [i.strip() for i in field.split(',') if i.strip()]


def icon(name):
    # return the HTML for the requested icon
    return Markup(f'<i class="bi bi-{name}"></i>')

from enum import Enum
from os import path


def static_folder() -> str:
    return path.join(path.dirname(path.abspath(__file__)), '../../static')


def template_folder() -> str:
    return path.join(path.dirname(path.abspath(__file__)), '../../template')


def format_title(title: str):
    if not title:
        return "-"
    return title.replace("-", " ").title()


def format_reference(ref: str) -> str:
    """
    :param ref: The input reference string.
    :return: The formatted reference string with special characters removed.
    """
    special_chars = r'[!@#$%^&*()+=\[\]{}|;:",<>/`~]'

    ref_without_special = re.sub(special_chars, '', ref.replace(" ", "").lower())
    return ref_without_special

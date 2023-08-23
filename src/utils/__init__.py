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

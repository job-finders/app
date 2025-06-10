from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.config import config_instance

settings = config_instance().MYSQL_SETTINGS

engine = create_engine(settings.DEVELOPMENT_DB)
Session = sessionmaker(bind=engine)
session = Session()


Base = declarative_base()

def escape_like(string: str, escape_char: str = '\\') -> str:
    return (
        string
        .replace(escape_char, escape_char * 2)  # Escape the escape char itself
        .replace('%', escape_char + '%')
        .replace('_', escape_char + '_')
    )
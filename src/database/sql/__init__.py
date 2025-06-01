from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from src.config import config_instance

settings = config_instance().MYSQL_SETTINGS
# Replace 'your_username', 'your_password', 'your_host', and 'your_database' with your MySQL database credentials
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
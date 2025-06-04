# src/database/security.py
from sqlalchemy.sql import text
from src.logger import init_logger

logger = init_logger("db_security")


def safe_query(session, query, params=None):
    """Execute SQL queries safely with parameterization"""
    try:
        # Use SQLAlchemy text() with parameters
        stmt = text(query)
        if params:
            result = session.execute(stmt, params)
        else:
            result = session.execute(stmt)

        # Log potential injection attempts
        if ';' in query or '--' in query or '/*' in query:
            logger.warning(f"Potential SQL injection attempt: {query}")

        return result
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise
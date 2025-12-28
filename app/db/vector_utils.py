import logging
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def create_vector_extension(session: Session):
    """
    Ensures the pgvector extension exists in the database.
    Logs the result for debugging/auditing.
    """
    try:
        session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create pgvector extension. Ensure the DB user has superuser privileges. Error: {e}")
        raise e
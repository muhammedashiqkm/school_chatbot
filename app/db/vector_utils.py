from sqlalchemy import text
from sqlalchemy.orm import Session

def create_vector_extension(session: Session):
    """
    Ensures the pgvector extension exists in the database.
    This is typically run during application startup or migration.
    """
    try:
        session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
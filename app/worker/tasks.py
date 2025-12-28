import logging
from celery import Celery
from app.config import settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.services.ingestion import IngestionService

logger = logging.getLogger(__name__)

celery_app = Celery("worker", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
)

@celery_app.task(bind=True, max_retries=3)
def ingest_pdf_task(self, doc_id_str: str):
    """
    Background task to process a document.
    
    Design Note:
    We delegate the entire lifecycle (Status updates, Error handling, Embedding)
    to IngestionService.process_document(). 
    This avoids code duplication and ensures logic is consistent 
    whether run via Celery or a standalone script.
    """
    logger.info(f"Task started for Document ID: {doc_id_str}")
    
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id_str).first()
        
        if not doc:
            logger.warning(f"Document {doc_id_str} not found in DB. Aborting task.")
            return

        IngestionService.process_document(db, doc)
        
    except Exception as e:
        logger.error(f"Critical Worker Failure for {doc_id_str}: {e}", exc_info=True)
    finally:
        db.close()
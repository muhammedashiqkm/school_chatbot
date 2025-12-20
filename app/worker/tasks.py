import traceback
from celery import Celery
from app.config import settings
from app.db.session import SessionLocal
from app.models.document import Document, DocStatus
from app.services.ingestion import IngestionService

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
    Background task to process a document:
    1. Update status to PROCESSING.
    2. Delegate logic to IngestionService (Download -> Chunk -> Embed -> Save).
    3. Update status to COMPLETED (or FAILED).
    """
    db = SessionLocal()
    doc = db.query(Document).filter(Document.id == doc_id_str).first()
    
    if not doc:
        db.close()
        return

    try:
        doc.status = DocStatus.PROCESSING
        db.commit()
        
        IngestionService.process_document(db, doc)
    
        doc.status = DocStatus.COMPLETED
        db.commit()

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Task Failed: {error_trace}")
        
        doc.status = DocStatus.FAILED
        doc.error = f"{str(e)}\n\n{error_trace}"
        db.commit()
    
        
    finally:
        db.close()
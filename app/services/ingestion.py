import os
import requests
import logging
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.llm_factory import LLMFactory
from app.models.document import Chunk
from app.config import settings

logger = logging.getLogger(__name__)

class IngestionService:
    @staticmethod
    def download_file(url: str, dest_path: str):
        logger.info(f"Downloading file from {url}")
        try:
            with requests.Session() as session:
                response = session.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                with open(dest_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise

    @staticmethod
    def extract_text(file_path: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        try:
            reader = PdfReader(file_path)
            text = []
            for page in reader.pages:
                extract = page.extract_text()
                if extract:
                    text.append(extract)
            return "\n".join(text)
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise

    @staticmethod
    def process_document(db_session, doc_obj):
        try:
            logger.info(f"Starting ingestion for Document {doc_obj.id}...")
            
            doc_obj.status = "PROCESSING"
            doc_obj.error = None 
            db_session.add(doc_obj)
            db_session.commit()

            if not doc_obj.file_path and doc_obj.source_url:
                file_name = f"{doc_obj.id}.pdf"
                save_path = os.path.join(settings.UPLOAD_FOLDER, file_name)
                IngestionService.download_file(doc_obj.source_url, save_path)
                doc_obj.file_path = save_path

            full_text = IngestionService.extract_text(doc_obj.file_path)
            if not full_text.strip():
                raise ValueError("No text extracted from document.")

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000, 
                chunk_overlap=200,
                separators=["\n\n", "\n", ".", " ", ""]
            )
            chunks_text = splitter.split_text(full_text)
            
            db_session.query(Chunk).filter(Chunk.document_id == doc_obj.id).delete()
            db_session.commit()
            
            BATCH_SIZE = 20
            total_chunks = len(chunks_text)
            
            for i in range(0, total_chunks, BATCH_SIZE):
                batch_texts = chunks_text[i : i + BATCH_SIZE]
                
                embeddings = LLMFactory.get_batch_embeddings_sync(batch_texts)
                
                for j, text in enumerate(batch_texts):
                    chunk = Chunk(
                        document_id=doc_obj.id,
                        chunk_index=i + j,
                        text=text,
                        embedding=embeddings[j]
                    )
                    db_session.add(chunk)
                
                db_session.commit()
                db_session.expire_all() 
            
            doc_obj.status = "COMPLETED"
            doc_obj.error = None 
            db_session.add(doc_obj)
            db_session.commit()
            logger.info(f"Ingestion for {doc_obj.id} completed successfully.")
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            db_session.rollback()
            
            doc_obj.status = "FAILED"
            doc_obj.error = str(e)[:500] 
            db_session.add(doc_obj)
            db_session.commit()
            raise
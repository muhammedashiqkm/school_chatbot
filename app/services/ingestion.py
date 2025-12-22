import os
import requests
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.llm_factory import LLMFactory
from app.models.document import Chunk
import logging

logger = logging.getLogger(__name__)

class IngestionService:
    @staticmethod
    def download_file(url: str, dest_path: str):
        logger.info(f"Downloading file from {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    @staticmethod
    def extract_text(file_path: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            extract = page.extract_text()
            if extract:
                text += extract + "\n"
        return text

    @staticmethod
    def process_document(db_session, doc_obj):
        """
        1. Download -> 2. Text -> 3. Chunk -> 4. Embed (Sync) -> 5. Save
        """
        try:
            if not doc_obj.file_path and doc_obj.source_url:
                file_name = f"{doc_obj.id}.pdf"
                save_path = os.path.join("uploads", file_name)
                IngestionService.download_file(doc_obj.source_url, save_path)
                doc_obj.file_path = save_path

            full_text = IngestionService.extract_text(doc_obj.file_path)
            if not full_text.strip():
                raise ValueError("No text extracted. Document might be empty or scanned.")

            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            chunks_text = splitter.split_text(full_text)

            # Clear old chunks before adding new ones
            db_session.query(Chunk).filter(Chunk.document_id == doc_obj.id).delete()
            
            logger.info(f"Generating embeddings for {len(chunks_text)} chunks...")
            
            for idx, text in enumerate(chunks_text):
                # ✅ Direct Sync Call - No event loop hacks needed
                embedding_vector = LLMFactory.get_embedding_sync(text)
                
                chunk = Chunk(
                    document_id=doc_obj.id,
                    chunk_index=idx,
                    text=text,
                    embedding=embedding_vector
                )
                db_session.add(chunk)
            
            logger.info("Ingestion completed successfully.")
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            raise
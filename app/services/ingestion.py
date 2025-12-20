import os
import requests
import asyncio
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.llm_factory import LLMFactory
from app.models.document import Chunk

def run_sync(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

class IngestionService:
    @staticmethod
    def download_file(url: str, dest_path: str):
        """Downloads a file from a URL to a local destination."""
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extracts full text from a PDF file."""
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
        Orchestrates the ingestion process:
        1. Download (if needed)
        2. Extract Text
        3. Chunk Text
        4. Generate Embeddings
        5. Save Chunks to DB
        """
        
        if not doc_obj.file_path and doc_obj.source_url:
            file_name = f"{doc_obj.id}.pdf"
            save_path = os.path.join("uploads", file_name)
            IngestionService.download_file(doc_obj.source_url, save_path)
            doc_obj.file_path = save_path

        full_text = IngestionService.extract_text(doc_obj.file_path)
        if not full_text.strip():
            raise ValueError("No text extracted from document. It might be empty or scanned images.")

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks_text = splitter.split_text(full_text)

        db_session.query(Chunk).filter(Chunk.document_id == doc_obj.id).delete()
        
        for idx, text in enumerate(chunks_text):
            embedding_vector = run_sync(LLMFactory.get_embedding(text))
            
            chunk = Chunk(
                document_id=doc_obj.id,
                chunk_index=idx,
                text=text,
                embedding=embedding_vector
            )
            db_session.add(chunk)
import asyncio
import threading
from google.genai import Client, types
from app.config import settings


_client_instance = None
_client_lock = threading.Lock()

def get_client():
    global _client_instance
    if _client_instance is None:
        with _client_lock:
            if _client_instance is None:
                if not settings.GEMINI_API_KEY:
                    raise ValueError("GEMINI_API_KEY is missing.")
                _client_instance = Client(api_key=settings.GEMINI_API_KEY)
    return _client_instance

class LLMFactory:
    @staticmethod
    def get_embedding_sync(text: str) -> list[float]:
        """Single text embedding (Blocking)"""
        client = get_client()
        result = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL_NAME,
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        return result.embeddings[0].values

    @staticmethod
    def get_batch_embeddings_sync(texts: list[str]) -> list[list[float]]:
        """Batch embedding generation (Blocking)"""
        if not texts:
            return []
            
        client = get_client()
        result = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL_NAME,
            contents=texts,
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        return [e.values for e in result.embeddings] if result.embeddings else []

    @staticmethod
    async def get_embedding(text: str) -> list[float]:
        """Async wrapper for the sync method"""
        return await asyncio.to_thread(LLMFactory.get_embedding_sync, text)
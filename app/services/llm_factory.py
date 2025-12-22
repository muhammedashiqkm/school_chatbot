from app.config import settings
from google.genai import Client
import asyncio

# Global Singleton Instance
_client_instance = None

def get_client():
    """Returns a singleton instance of the Google GenAI Client."""
    global _client_instance
    if _client_instance is None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing.")
        _client_instance = Client(api_key=settings.GEMINI_API_KEY)
    return _client_instance

class LLMFactory:
    @staticmethod
    def get_embedding_sync(text: str) -> list[float]:
        """
        Synchronous version of embedding generation.
        Uses singleton client for better performance.
        """
        client = get_client()
        result = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL_NAME,
            contents=text,
        )
        return result.embeddings[0].values

    @staticmethod
    async def get_embedding(text: str) -> list[float]:
        """Async version wrapper for non-tool usage."""
        return await asyncio.to_thread(LLMFactory.get_embedding_sync, text)
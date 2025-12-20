from app.config import settings
import openai
import google.generativeai as genai
import asyncio

class LLMFactory:
    @staticmethod
    async def get_embedding(text: str) -> list[float]:
        """
        Generates vector embeddings using Google Gemini.
        Target Model: models/text-embedding-005
        Dimensions: 768 (Ensure this matches your DB schema)
        """
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing in environment variables.")

        genai.configure(api_key=settings.GEMINI_API_KEY)

        def _run_sync():
            result = genai.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL_NAME,
                content=text,
                task_type="retrieval_document",
            )
            return result['embedding']

        return await asyncio.to_thread(_run_sync)

    @staticmethod
    async def generate_response(provider: str, context: str, question: str, history: list) -> str:
        """
        Generates a chat response using the specified provider.
        """
        prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer based on context:"
        
        if provider == "gemini":
            if not settings.GEMINI_API_KEY:
                return "Error: GEMINI_API_KEY not configured."
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
            response = await model.generate_content_async(prompt)
            return response.text
            
        elif provider == "openai":
            if not settings.OPENAI_API_KEY:
                return "Error: OPENAI_API_KEY not configured."
                
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a helpful academic tutor."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content

        elif provider == "deepseek":
            if not settings.DEEPSEEK_API_KEY:
                return "Error: DEEPSEEK_API_KEY not configured."
                
            client = openai.AsyncOpenAI(
                api_key=settings.DEEPSEEK_API_KEY, 
                base_url="https://api.deepseek.com"
            )
            response = await client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
            
        return f"Provider '{provider}' is not supported."
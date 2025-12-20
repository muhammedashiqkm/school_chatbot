from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Chunk, Document
from app.services.llm_factory import LLMFactory

async def perform_rag(
    db: AsyncSession, 
    question: str, 
    filters: dict, 
    model: str, 
    history: list
):
    """
    Performs Retrieval-Augmented Generation:
    1. Embeds the user question.
    2. Searches the database for similar chunks (Vector Search).
    3. Filters chunks by metadata (Syllabus, Class, Subject).
    4. Sends context + question + history to the LLM.
    """
    
    query_vec = await LLMFactory.get_embedding(question)
    
    stmt = select(Chunk).join(Document).where(
        Document.syllabus == filters['syllabus'],
        Document.class_name == filters['class_name'],
        Document.subject == filters['subject']
    ).order_by(
        Chunk.embedding.cosine_distance(query_vec)
    ).limit(5)
    
    result = await db.execute(stmt)
    chunks = result.scalars().all()
    
    if not chunks:
        return "I couldn't find any relevant documents in the syllabus matching your criteria.", []

    context_text = "\n\n".join([f"Source {i+1}: {c.text}" for i, c in enumerate(chunks)])
    sources = [str(c.document_id) for c in chunks]
    
    answer = await LLMFactory.generate_response(model, context_text, question, history)
    
    return answer, sources
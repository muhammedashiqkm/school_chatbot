import logging
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.document import Chunk, Document
from app.services.llm_factory import LLMFactory
from google.adk.tools import ToolContext, FunctionTool
from app.config import settings

logger = logging.getLogger(__name__)

def search_syllabus(query: str, tool_context: ToolContext) -> dict:
    """
    Searches the school syllabus for a specific topic.
    Returns the most relevant text chunks.
    """
    logger.info(f"Tool executing. Query: '{query}'")
    
    try:
        state = tool_context.state
        filters = {
            "syllabus": state.get("syllabus"),
            "class_name": state.get("class_name"),
            "subject": state.get("subject")
        }
        
        if not all(filters.values()):
            logger.warning("Tool called with incomplete context (missing filters).")
            
    except Exception as e:
        logger.error(f"Failed to read tool context: {e}")
        return {"status": "error", "message": "Context error."}

    with SessionLocal() as db:
        try:
            query_vec = LLMFactory.get_embedding_sync(query)
            
            conditions = []
            if filters.get('syllabus'): 
                conditions.append(Document.syllabus == filters['syllabus'])
            if filters.get('class_name'): 
                conditions.append(Document.class_name == filters['class_name'])
            if filters.get('subject'): 
                conditions.append(Document.subject == filters['subject'])
            
            stmt = select(Chunk).join(Document)
            if conditions:
                stmt = stmt.where(*conditions)
            
            limit = getattr(settings, 'SEARCH_LIMIT', 6)
            stmt = stmt.order_by(Chunk.embedding.cosine_distance(query_vec)).limit(limit)
            
            chunks = db.execute(stmt).scalars().all()
            
            if not chunks:
                return {
                    "status": "completed", 
                    "found": False, 
                    "message": "No relevant documents found in the uploaded textbooks."
                }

            context_text = "\n\n".join([f"[Source: Doc {c.document_id}]\n{c.text}" for c in chunks])
            
            return {
                "status": "success", 
                "found": True, 
                "context": context_text
            }
            
        except Exception as e:
            logger.error(f"Database search tool failed: {e}", exc_info=True)
            return {"status": "error", "message": "Internal search error."}

syllabus_tool = FunctionTool(func=search_syllabus)
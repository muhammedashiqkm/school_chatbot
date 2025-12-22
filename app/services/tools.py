import logging
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.document import Chunk, Document
from app.services.llm_factory import LLMFactory
from google.adk.tools import ToolContext, FunctionTool
from app.config import settings

logger = logging.getLogger(__name__)

def search_syllabus(query: str, tool_context: ToolContext) -> dict:
    """Searches the school syllabus for a specific topic."""
    logger.info(f"Tool started. Query: '{query}'")
    
    try:
        state = tool_context.state
        filters = {
            "syllabus": state.get("syllabus"),
            "class_name": state.get("class_name"),
            "subject": state.get("subject")
        }
        logger.debug(f"Filters: {filters}")
    except Exception as e:
        logger.error(f"Failed to read tool context: {e}", exc_info=True)
        return {"status": "error", "message": "Invalid session state."}

    db = SessionLocal()
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
            
        limit = getattr(settings, 'SEARCH_LIMIT', 5)
        stmt = stmt.order_by(Chunk.embedding.cosine_distance(query_vec)).limit(limit)
        
        chunks = db.execute(stmt).scalars().all()
        
        if not chunks:
            logger.info("No chunks found.")
            return {
                "status": "completed", 
                "found": False, 
                "message": "No relevant documents found."
            }

        context_text = "\n---\n".join([f"{c.text}" for c in chunks])
        logger.info(f"Found {len(chunks)} chunks.")
        
        return {
            "status": "success", 
            "found": True, 
            "context": context_text
        }
        
    except Exception as e:
        logger.error(f"Database search failed: {e}", exc_info=True)
        return {
            "status": "error", 
            "message": "An internal error occurred while searching the database."
        }
    finally:
        db.close()

syllabus_tool = FunctionTool(func=search_syllabus)
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.adk.sessions import DatabaseSessionService
from google.adk.runners import Runner
from google.genai import types

from app.config import settings
from app.schemas.chat import ChatRequest, ChatResponse, ClearSessionRequest
from app.services.agent import get_agent 
from app.models.document import Document
from app.api.deps import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

session_service = DatabaseSessionService(db_url=settings.DATABASE_URL)

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db) 
):
    """
    Chat endpoint with strict validation.
    Returns 404 if no relevant documents exist in the database.
    """
    
    stmt = select(Document).where(
        Document.syllabus == req.syllabus,
        Document.class_name == req.class_name,
        Document.subject == req.subject,
        Document.status == "COMPLETED"
    ).limit(1)
    
    result = await db.execute(stmt)
    existing_doc = result.scalars().first()
    
    if not existing_doc:
        logger.warning(f"Chat rejected: No documents found for {req.syllabus}/{req.class_name}/{req.subject}")
        raise HTTPException(
            status_code=404, 
            detail=f"No study materials found for {req.syllabus} {req.class_name} {req.subject}. Please upload a document first."
        )

    user_id = "authenticated_user_placeholder" 
    session_id = req.chatbot_user_id

    if not req.model:
        raise HTTPException(status_code=400, detail="Model provider must be specified")

    try:
        session = await session_service.get_session(
            app_name=settings.PROJECT_NAME,
            user_id=user_id,
            session_id=session_id
        )
        
        if not session:
            session = await session_service.create_session(
                app_name=settings.PROJECT_NAME,
                user_id=user_id,
                session_id=session_id
            )

        session.state["syllabus"] = req.syllabus
        session.state["class_name"] = req.class_name
        session.state["subject"] = req.subject
        
        agent = get_agent(model_provider=req.model)
        
        runner = Runner(
            agent=agent, 
            app_name=settings.PROJECT_NAME, 
            session_service=session_service
        )
        
        user_msg = types.Content(role='user', parts=[types.Part(text=req.question)])
        final_text = "Error generating response."

        async for event in runner.run_async(
            user_id=user_id, 
            session_id=session_id, 
            new_message=user_msg
        ):
            if event.is_final_response():
                final_text = event.content.parts[0].text

        return ChatResponse(answer=final_text, sources=[])
        
    except Exception as e:
        logger.error(f"Agent execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred while processing your request.")

@router.post("/clear_session")
async def clear_session(req: ClearSessionRequest):
    user_id = "authenticated_user_placeholder"
    await session_service.delete_session(
        app_name=settings.PROJECT_NAME,
        user_id=user_id,
        session_id=req.chatbot_user_id
    )
    return {"status": "cleared"}
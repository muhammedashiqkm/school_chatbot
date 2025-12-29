import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, and_
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
    Chat endpoint with smart status checking.
    Validates document existence based on College + Syllabus + Class + Subject.
    """
    
    stmt_success = select(exists().where(
        and_(
            Document.school_name == req.college,
            Document.syllabus == req.syllabus,
            Document.class_name == req.class_name,
            Document.subject == req.subject,
            Document.status == "COMPLETED"
        )
    ))
    result_success = await db.execute(stmt_success)
    
    if not result_success.scalar():
        stmt_any = select(Document.status).where(
            and_(
                Document.school_name == req.college,
                Document.syllabus == req.syllabus,
                Document.class_name == req.class_name,
                Document.subject == req.subject
            )
        ).limit(1)
        
        result_any = await db.execute(stmt_any)
        status_found = result_any.scalar()

        if status_found == "FAILED":
            raise HTTPException(
                status_code=400, 
                detail=f"The textbook for {req.subject} (College: {req.college}) failed to process. Please delete and re-upload it."
            )
        elif status_found in ["PENDING", "PROCESSING"]:
            raise HTTPException(
                status_code=409,
                detail=f"The textbook for {req.subject} is still processing. Please wait a moment."
            )
        else:
            logger.warning(f"Chat rejected: No document for {req.college}/{req.syllabus}/{req.class_name}/{req.subject}")
            raise HTTPException(
                status_code=404, 
                detail=f"No textbook found for {req.college} / {req.syllabus} / {req.class_name} / {req.subject}. Please upload documents first."
            )

    session_id = req.chatbot_user_id

    if not req.model:
        raise HTTPException(status_code=400, detail="Model provider must be specified")

    try:
        session = await session_service.get_session(
            app_name=settings.PROJECT_NAME,
            user_id=settings.USER_ID,
            session_id=session_id
        )
        
        if not session:
            session = await session_service.create_session(
                app_name=settings.PROJECT_NAME,
                user_id=settings.USER_ID,
                session_id=session_id
            )

        session.state["college"] = req.college
        session.state["syllabus"] = req.syllabus
        session.state["class_name"] = req.class_name
        session.state["subject"] = req.subject
        
        agent = get_agent(model_provider=req.model)
        runner = Runner(
            agent=agent, 
            app_name=settings.PROJECT_NAME, 
            session_service=session_service
        )
        
        dynamic_context_header = (
            f"[System Context]\n"
            f"College: {req.college}\n"
            f"Syllabus: {req.syllabus}\n"
            f"Class: {req.class_name}\n"
            f"Subject: {req.subject}\n"
            f"--------------------\n"
        )
        
        full_prompt = f"{dynamic_context_header}\nUser Question: {req.question}"
        
        user_msg = types.Content(role='user', parts=[types.Part(text=full_prompt)])
        final_text = "Error generating response."

        async for event in runner.run_async(
            user_id=settings.USER_ID, 
            session_id=session_id, 
            new_message=user_msg
        ):
            if event.is_final_response():
                final_text = event.content.parts[0].text

        return ChatResponse(answer=final_text)
        
    except Exception as e:
        logger.error(f"Agent execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred while processing your request.")

@router.post("/clear_session")
async def clear_session(req: ClearSessionRequest):
    """
    Clears the chat session history.
    Returns 404 if the session ID does not exist.
    """
    session = await session_service.get_session(
        app_name=settings.PROJECT_NAME,
        user_id=settings.USER_ID,
        session_id=req.chatbot_user_id
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await session_service.delete_session(
        app_name=settings.PROJECT_NAME,
        user_id=settings.USER_ID,
        session_id=req.chatbot_user_id
    )
    return {"status": "cleared"}
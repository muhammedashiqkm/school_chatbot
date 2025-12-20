import os
import uuid
import json
import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, get_current_user
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentUrlRequest
from app.worker.tasks import ingest_pdf_task
from app.config import settings

router = APIRouter()

@router.post("/document", response_model=DocumentResponse)
async def create_document(
    file: UploadFile = File(None),
    body: str = Form(None),
    json_body: DocumentUrlRequest = Body(None),
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    data = None
    if json_body:
        data = json_body
    elif body:
        try:
            raw = json.loads(body)
            data = DocumentUrlRequest(**raw)
        except json.JSONDecodeError:
             raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    if not data:
         raise HTTPException(status_code=400, detail="Missing document data")

    doc_id = uuid.uuid4()
    file_path = None
    
    if file:
        filename_parts = file.filename.split(".")
        ext = filename_parts[-1] if len(filename_parts) > 1 else "pdf"
        
        if not os.path.exists(settings.UPLOAD_FOLDER):
            os.makedirs(settings.UPLOAD_FOLDER)
            
        file_path = os.path.join(settings.UPLOAD_FOLDER, f"{doc_id}.{ext}")
        
        try:
            async with aiofiles.open(file_path, 'wb') as out_file:
                while content := await file.read(1024 * 1024):
                    await out_file.write(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
            
    new_doc = Document(
        id=doc_id,
        display_name=data.display_name or (file.filename if file else "URL Document"),
        source_url=data.url if not file else None,
        file_path=file_path,
        school_name=data.school,
        syllabus=data.syllabus,
        class_name=data.class_name,
        subject=data.subject,
        status="PENDING"
    )
    
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    
    ingest_pdf_task.delay(str(new_doc.id))
    
    return new_doc

@router.get("/document_details/{school_name}", response_model=list[DocumentResponse])
async def list_docs(school_name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.school_name == school_name))
    return result.scalars().all()

@router.delete("/document/{doc_id}")
async def delete_doc(doc_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError as e:
            print(f"Error deleting file {doc.file_path}: {e}")
            
    await db.delete(doc)
    await db.commit()
    
    return {"message": "Deleted"}
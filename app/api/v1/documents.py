import os
import uuid
import json
import aiofiles
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, get_current_user
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentUrlRequest, SubjectSearchRequest, DocumentListRequest
from app.worker.tasks import ingest_pdf_task
from app.config import settings

router = APIRouter()





async def save_new_document(db: AsyncSession, doc_id: uuid.UUID, data: DocumentUrlRequest, file_path: str = None):
    new_doc = Document(
        id=doc_id,
        display_name=data.display_name,
        source_url=data.url if not file_path else None,
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

async def update_existing_document(db: AsyncSession, doc: Document, file_path: str = None, source_url: str = None, meta_data: DocumentUrlRequest = None):
    if meta_data:
        if meta_data.display_name: doc.display_name = meta_data.display_name
        if meta_data.school: doc.school_name = meta_data.school
        if meta_data.syllabus: doc.syllabus = meta_data.syllabus
        if meta_data.class_name: doc.class_name = meta_data.class_name
        if meta_data.subject: doc.subject = meta_data.subject

    if file_path:
        doc.file_path = file_path
        doc.source_url = None 
    elif source_url:
        doc.source_url = source_url
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except OSError:
                pass
        doc.file_path = None

    doc.status = "PENDING"
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    ingest_pdf_task.delay(str(doc.id))
    return doc


@router.post("/document/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...), body: str = Form(...), db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    try:
        raw = json.loads(body)
        data = DocumentUrlRequest(**raw)
    except json.JSONDecodeError:
         raise HTTPException(status_code=400, detail="Invalid JSON format in 'body'")

    doc_id = uuid.uuid4()
    if not os.path.exists(settings.UPLOAD_FOLDER):
        os.makedirs(settings.UPLOAD_FOLDER)
    ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    file_path = os.path.join(settings.UPLOAD_FOLDER, f"{doc_id}.{ext}")
    
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):
                await out_file.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    if not data.display_name:
        data.display_name = file.filename
    return await save_new_document(db, doc_id, data, file_path)

@router.post("/document/url", response_model=DocumentResponse)
async def add_document_url(data: DocumentUrlRequest, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    doc_id = uuid.uuid4()
    if not data.display_name:
        data.display_name = "URL Document"
    return await save_new_document(db, doc_id, data, file_path=None)

@router.put("/document/{doc_id}/upload", response_model=DocumentResponse)
async def update_document_file(doc_id: str, file: UploadFile = File(...), body: str = Form(None), db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    meta_data = None
    if body:
        try:
            raw = json.loads(body)
            meta_data = DocumentUrlRequest(**raw)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")

    if not os.path.exists(settings.UPLOAD_FOLDER):
        os.makedirs(settings.UPLOAD_FOLDER)
    ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    file_path = os.path.join(settings.UPLOAD_FOLDER, f"{doc_id}.{ext}")
    
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):
                await out_file.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    return await update_existing_document(db, doc, file_path=file_path, meta_data=meta_data)

@router.put("/document/{doc_id}/url", response_model=DocumentResponse)
async def update_document_url(doc_id: str, data: DocumentUrlRequest, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return await update_existing_document(db, doc, source_url=data.url, meta_data=data)


@router.post("/document/subject/search", response_model=list[str])
async def search_subjects(req: SubjectSearchRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Document.subject).where(
        Document.school_name == req.school,
        Document.syllabus == req.syllabus,
        Document.class_name == req.class_name,
        Document.status == "COMPLETED"
    ).distinct()
    result = await db.execute(stmt)
    return result.scalars().all()



@router.post("/document_details", response_model=list[DocumentResponse])
async def list_docs_filtered(
    req: DocumentListRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    List documents filtered by College, Syllabus, Class, or Subject.
    All fields are optional.
    """
    stmt = select(Document)
    
    if req.college:
        stmt = stmt.where(Document.school_name == req.college)
    if req.syllabus:
        stmt = stmt.where(Document.syllabus == req.syllabus)
    if req.class_name:
        stmt = stmt.where(Document.class_name == req.class_name)
    if req.subject:
        stmt = stmt.where(Document.subject == req.subject)

    stmt = stmt.order_by(Document.created_at.desc())

    result = await db.execute(stmt)
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
        except OSError:
            pass
    await db.delete(doc)
    await db.commit()
    return {"message": "Deleted"}
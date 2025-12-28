import os
import uuid
import json
import aiofiles
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, get_current_user
from app.models.document import Document
from app.models.school import School, Syllabus, Class, Subject 
from app.schemas.document import DocumentResponse, DocumentUrlRequest, SubjectSearchRequest, DocumentListRequest
from app.worker.tasks import ingest_pdf_task
from app.config import settings

router = APIRouter()


def validate_uuid(doc_id: str):
    """
    Validates that the provided doc_id string is a valid UUID.
    If invalid, raises 404 immediately to prevent Database 500 errors.
    """
    try:
        uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Document not found")

async def validate_hierarchy(db: AsyncSession, school_name: str, syllabus_name: str, class_name: str, subject_name: str):
    """
    Checks if the School -> Syllabus -> Class -> Subject relationship exists in the DB.
    """
    stmt = (
        select(Subject)
        .select_from(School)
        .join(Syllabus)
        .join(Class)
        .join(Subject)
        .where(
            School.name == school_name,
            Syllabus.name == syllabus_name,
            Class.name == class_name,
            Subject.name == subject_name
        )
    )
    result = await db.execute(stmt)
    if not result.scalars().first():
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid Hierarchy: Subject '{subject_name}' not found under College '{school_name}' > Syllabus '{syllabus_name}' > Class '{class_name}'."
        )

async def handle_file_upload(doc_id: str, file: UploadFile) -> str:
    if not os.path.exists(settings.UPLOAD_FOLDER):
        os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
        
    ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    file_path = os.path.join(settings.UPLOAD_FOLDER, f"{doc_id}.{ext}")
    
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):  
                await out_file.write(content)
        return file_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

async def update_document_logic(db: AsyncSession, doc: Document, file_path: str = None, source_url: str = None, meta: dict = None):
    should_ingest = False

    if meta:
        if any(k in meta for k in ['school', 'syllabus', 'class_name', 'subject']):
            s_school = meta.get('school') or doc.school_name
            s_syll = meta.get('syllabus') or doc.syllabus
            s_class = meta.get('class_name') or doc.class_name
            s_sub = meta.get('subject') or doc.subject
            await validate_hierarchy(db, s_school, s_syll, s_class, s_sub)

        if 'display_name' in meta: doc.display_name = meta['display_name']
        if 'school' in meta: doc.school_name = meta['school']
        if 'syllabus' in meta: doc.syllabus = meta['syllabus']
        if 'class_name' in meta: doc.class_name = meta['class_name']
        if 'subject' in meta: doc.subject = meta['subject']

    if file_path:
        if doc.file_path and doc.file_path != file_path and os.path.exists(doc.file_path):
            try: os.remove(doc.file_path)
            except OSError: pass
        doc.file_path = file_path
        doc.source_url = None
        should_ingest = True
    
    elif source_url is not None: 
        if doc.source_url != source_url:
            doc.source_url = source_url
            if doc.file_path and os.path.exists(doc.file_path):
                try: os.remove(doc.file_path)
                except OSError: pass
            doc.file_path = None
            should_ingest = True
            
    if should_ingest:
        doc.status = "PENDING"
        doc.error = None 
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        ingest_pdf_task.delay(str(doc.id))
    else:
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

    return doc



@router.post("/document/url", response_model=DocumentResponse)
async def create_document_url(data: DocumentUrlRequest, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    await validate_hierarchy(db, data.school, data.syllabus, data.class_name, data.subject)
    new_id = uuid.uuid4()
    new_doc = Document(id=new_id, display_name=data.display_name, source_url=data.url, file_path=None, school_name=data.school, syllabus=data.syllabus, class_name=data.class_name, subject=data.subject, status="PENDING")
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    ingest_pdf_task.delay(str(new_doc.id))
    return new_doc

@router.post("/document/upload", response_model=DocumentResponse)
async def create_document_upload(file: UploadFile = File(...), body: str = Form(...), db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    try: data = json.loads(body)
    except json.JSONDecodeError: raise HTTPException(status_code=400, detail="Invalid JSON in 'body' field")
    
    if not all([data.get("display_name"), data.get("school"), data.get("syllabus"), data.get("class_name"), data.get("subject")]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    await validate_hierarchy(db, data.get("school"), data.get("syllabus"), data.get("class_name"), data.get("subject"))

    new_id = uuid.uuid4()
    file_path = await handle_file_upload(str(new_id), file)
    
    new_doc = Document(id=new_id, display_name=data.get("display_name"), source_url=None, file_path=file_path, school_name=data.get("school"), syllabus=data.get("syllabus"), class_name=data.get("class_name"), subject=data.get("subject"), status="PENDING")
    
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    ingest_pdf_task.delay(str(new_doc.id))
    return new_doc


@router.get("/document/{doc_id}/view")
async def view_document_file(doc_id: str, db: AsyncSession = Depends(get_db)):
    validate_uuid(doc_id)

    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File resource not found (Document might be URL-based)")
    
    return FileResponse(path=doc.file_path, media_type='application/pdf', filename=os.path.basename(doc.file_path))


@router.put("/document/{doc_id}/upload", response_model=DocumentResponse)
async def update_document_file(doc_id: str, file: UploadFile = File(...), body: str = Form(None), db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    validate_uuid(doc_id)

    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    meta_data = {}
    if body:
        try: meta_data = json.loads(body)
        except json.JSONDecodeError: raise HTTPException(status_code=400, detail="Invalid JSON")

    file_path = await handle_file_upload(doc_id, file)
    return await update_document_logic(db, doc, file_path=file_path, meta=meta_data)


@router.put("/document/{doc_id}/url", response_model=DocumentResponse)
async def update_document_url(doc_id: str, data: DocumentUrlRequest, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    validate_uuid(doc_id)

    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return await update_document_logic(db, doc, source_url=data.url, meta=data.dict())

@router.delete("/document/{doc_id}")
async def delete_doc(doc_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    validate_uuid(doc_id)

    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.file_path and os.path.exists(doc.file_path):
        try: os.remove(doc.file_path)
        except OSError: pass
            
    await db.delete(doc)
    await db.commit()
    return {"message": "Deleted"}

@router.post("/document/subject/search", response_model=List[str])
async def search_subjects(req: SubjectSearchRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Document.subject).where(
        Document.school_name == req.school, 
        Document.syllabus == req.syllabus, 
        Document.class_name == req.class_name, 
        Document.status == "COMPLETED"
    ).distinct()
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/document_details", response_model=List[DocumentResponse])
async def list_docs_filtered(req: DocumentListRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Document)
    if req.college: stmt = stmt.where(Document.school_name == req.college)
    if req.syllabus: stmt = stmt.where(Document.syllabus == req.syllabus)
    if req.class_name: stmt = stmt.where(Document.class_name == req.class_name)
    if req.subject: stmt = stmt.where(Document.subject == req.subject)
    stmt = stmt.order_by(Document.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, get_current_user
from app.models.school import School, Syllabus, Class, Subject
from app.schemas.school import SchoolSetupRequest

router = APIRouter()

@router.post("/schools")
async def setup_school(
    req: SchoolSetupRequest, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user) 
):
    
    res = await db.execute(select(School).where(School.name == req.school_name))
    school = res.scalars().first()
    
    if not school:
        school = School(name=req.school_name)
        db.add(school)
        await db.commit()
        await db.refresh(school)
    
    async def process_items(model, item_list):
        if not item_list: 
            return
        
        stmt = select(model.name).where(
            model.school_id == school.id, 
            model.name.in_(item_list)
        )
        result = await db.execute(stmt)
        existing_names = set(result.scalars().all())
        
        new_items = [
            model(name=name, school_id=school.id) 
            for name in item_list if name not in existing_names
        ]
        
        if new_items:
            db.add_all(new_items)

    try:
        await process_items(Syllabus, req.syllabus)
        await process_items(Class, req.class_)
        await process_items(Subject, req.subject)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Setup failed: {str(e)}")

    return {"message": "School setup completed"}
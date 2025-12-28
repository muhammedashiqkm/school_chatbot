from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, get_current_user
from app.models.school import School, Syllabus, Class, Subject
from app.schemas.school import SchoolSetupRequest

# ✅ Ensure this variable exists!
router = APIRouter()

@router.post("/schools")
async def setup_school(
    req: SchoolSetupRequest, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user) 
):
    # Check if school exists
    res = await db.execute(select(School).where(School.name == req.school_name))
    school = res.scalars().first()
    
    if not school:
        school = School(name=req.school_name)
        db.add(school)
        await db.commit()
        await db.refresh(school)
    
    # Helper to process lists
    async def process_items(model, item_list):
        if not item_list: 
            return
        
        # Find duplicates
        stmt = select(model.name).where(
            model.school_id == school.id, 
            model.name.in_(item_list)
        )
        result = await db.execute(stmt)
        existing_names = set(result.scalars().all())
        
        # Add only new items
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


@router.get("/schools/options")
async def get_school_options(
    school_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns valid Syllabi, Classes, and Subjects for a given School Name.
    Used by the Admin Panel JS to filter dropdowns.
    """
    res = await db.execute(select(School).where(School.name == school_name))
    school = res.scalars().first()
    
    if not school:
        return {"syllabi": [], "classes": [], "subjects": []}

    async def get_names(model):
        result = await db.execute(
            select(model.name)
            .where(model.school_id == school.id)
            .distinct()
            .order_by(model.name)
        )
        return result.scalars().all()

    return {
        "syllabi": await get_names(Syllabus),
        "classes": await get_names(Class),
        "subjects": await get_names(Subject)
    }
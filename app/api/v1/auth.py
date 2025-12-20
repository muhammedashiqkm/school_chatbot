from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import LoginRequest, Token
from app.models.user import User

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalars().first()
 
    if not user or not AuthService.verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token = AuthService.create_access_token(subject=user.username)
    return {"access_token": access_token, "token_type": "bearer"}
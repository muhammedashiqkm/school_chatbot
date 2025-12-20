import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.auth_service import AuthService

async def create_superuser():
    async with AsyncSessionLocal() as db:
        username = input("Enter Superuser Username: ")
        email = input("Enter Superuser Email (optional): ")
        password = input("Enter Superuser Password: ")

        result = await db.execute(select(User).where(User.username == username))
        if result.scalars().first():
            print(f"User '{username}' already exists.")
            return
        
        hashed_pw = AuthService.get_password_hash(password)
        user = User(
            username=username,
            email=email,
            password_hash=hashed_pw,
            is_superuser=True,
            is_active=True
        )
        
        db.add(user)
        await db.commit()
        print(f"Superuser '{username}' created successfully.")

if __name__ == "__main__":
    asyncio.run(create_superuser())
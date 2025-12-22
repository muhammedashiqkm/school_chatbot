import asyncio
import sys
import os

# 1. PATH FIX: Ensure the project root is in Python's path
#    This prevents "ModuleNotFoundError: No module named 'app'"
sys.path.append(os.getcwd())

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
# Ensure app/models/user.py is importing Base from app.db.base_class!
from app.models.user import User 
from app.services.auth_service import AuthService

async def create_superuser():
    print("--- Create Superuser ---")
    async with AsyncSessionLocal() as db:
        try:
            username = input("Enter Superuser Username: ")
            email = input("Enter Superuser Email (optional): ")
            password = input("Enter Superuser Password: ")
        except EOFError:
            print("\nError: Input failed. Are you running with '-it'? (Interactive Mode)")
            return

        # Check if user exists
        result = await db.execute(select(User).where(User.username == username))
        if result.scalars().first():
            print(f"Error: User '{username}' already exists.")
            return
        
        # Hash Password
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
        print(f"Success: Superuser '{username}' created!")

if __name__ == "__main__":
    asyncio.run(create_superuser())
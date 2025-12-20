from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware  # Import CORS
from sqlalchemy import text
from app.api.v1 import auth, schools, documents, chat
from app.config import settings
from app.core.logger import setup_logging
from app.admin.app import flask_app
from app.db.base import Base
from app.db.session import async_engine

# 1. Initialize Logging
setup_logging()

# 2. Create FastAPI App
app = FastAPI(title=settings.PROJECT_NAME)

# 3. Add CORS Middleware (Security: Adjust allow_origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # Allow all origins (Change to specific domains in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# 4. Register Routers
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["Auth"])
app.include_router(schools.router, prefix=settings.API_V1_STR, tags=["Schools"])
app.include_router(documents.router, prefix=settings.API_V1_STR, tags=["Documents"])
app.include_router(chat.router, prefix=settings.API_V1_STR, tags=["Chat"])

# 5. Mount Admin Panel (Flask)
app.mount("/admin", WSGIMiddleware(flask_app))

# 6. Startup Event: Initialize Database Tables
@app.on_event("startup")
async def init_tables():
    async with async_engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Create Tables
        await conn.run_sync(Base.metadata.create_all)
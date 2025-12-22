from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.api.v1 import auth, schools, documents, chat
from app.config import settings
from app.core.logger import setup_logging
from app.admin.app import flask_app
from app.db.base import Base
from app.db.session import async_engine, SessionLocal

setup_logging()

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)


app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["Auth"])
app.include_router(schools.router, prefix=settings.API_V1_STR, tags=["Schools"])
app.include_router(documents.router, prefix=settings.API_V1_STR, tags=["Documents"])
app.include_router(chat.router, prefix=settings.API_V1_STR, tags=["Chat"])


app.mount("/admin", WSGIMiddleware(flask_app))

@app.on_event("startup")
async def init_db():
    """
    Runs on application startup.
    1. Enables pgvector extension (Sync).
    2. Creates database tables if they don't exist (Async).
    """
    

    try:
        with SessionLocal() as session:
            session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            session.commit()
    except Exception as e:
        print(f"WARNING: Could not enable vector extension: {e}")

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
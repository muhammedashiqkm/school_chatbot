import os
import logging
import flask_admin
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from a2wsgi import WSGIMiddleware 

from app.api.v1.auth import router as auth_router
from app.api.v1.school_routes import router as schools_router
from app.api.v1.documents import router as documents_router
from app.api.v1.chat import router as chat_router

from app.config import settings
from app.core.logger import setup_logging
from app.admin.app import create_admin_app

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)

app.include_router(auth_router, prefix=settings.API_V1_STR, tags=["Auth"])
app.include_router(schools_router, prefix=settings.API_V1_STR, tags=["Schools"])
app.include_router(documents_router, prefix=settings.API_V1_STR, tags=["Documents"])
app.include_router(chat_router, prefix=settings.API_V1_STR, tags=["Chat"])


try:
    flask_admin_app = create_admin_app()

    admin_static_path = os.path.join(os.path.dirname(flask_admin.__file__), 'static')

    app.mount("/admin/static", StaticFiles(directory=admin_static_path), name="admin_static")
    
    app.mount("/admin/admin/static", StaticFiles(directory=admin_static_path), name="admin_static_nested")

    app.mount("/admin", WSGIMiddleware(flask_admin_app))
    
    logger.info("✅ Flask Admin mounted successfully (Dual Static Bypass Enabled)")
except Exception as e:
    logger.critical(f"❌ Failed to mount Admin Panel: {e}")

@app.get("/")
async def root():
    return RedirectResponse(url="/admin")
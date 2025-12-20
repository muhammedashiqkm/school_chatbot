from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
import logging

logger = logging.getLogger("app")

class CustomException(Exception):
    """Base class for custom application exceptions."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Overrides the default HTTPException handler to ensure consistent JSON structure.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches all unhandled exceptions to prevent the server from crashing 
    and exposes a generic error message to the client while logging the trace.
    """
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact support."},
    )

async def custom_exception_handler(request: Request, exc: CustomException):
    """
    Handles our custom defined exceptions.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
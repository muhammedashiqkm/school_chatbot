import logging
from fastapi import Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR

logger = logging.getLogger("app")

class CustomException(Exception):
    """Base class for custom application logic errors."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handles explicit HTTP exceptions thrown by the app.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    NORMALIZATION: Converts Pydantic validation errors (complex arrays)
    into the same simple format as other errors.
    """
    error_msg = f"Validation Error: {exc.errors()[0].get('msg')} in {exc.errors()[0].get('loc')}"
    logger.warning(f"Validation error: {error_msg}")
    
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": error_msg}, 
    )

async def custom_exception_handler(request: Request, exc: CustomException):
    """Handles business logic exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )

async def global_exception_handler(request: Request, exc: Exception):
    """
    Safety net for crashes (IndexError, ValueError, Database connection fail).
    Hides internal details in production to prevent leaking stack traces to hackers.
    """
    logger.error(f"Global Exception Handler caught: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )
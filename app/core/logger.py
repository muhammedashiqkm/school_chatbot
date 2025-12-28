import logging
import sys
from logging.config import dictConfig
from app.config import settings

def setup_logging():
    """
    Configures application logging using dictConfig.
    - Captures 'uvicorn' and 'fastapi' logs.
    - Sets logical levels based on environment.
    - Uses a standard format for readability.
    """
    
    log_level = "DEBUG" if settings.DEBUG else "INFO"
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
                "level": log_level,
            },
        },
        "loggers": {
            "app": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO", 
                "propagate": False,
            },
            "passlib": {"handlers": ["console"], "level": "WARNING"},
            "urllib3": {"handlers": ["console"], "level": "WARNING"},
        },
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
    }

    dictConfig(logging_config)
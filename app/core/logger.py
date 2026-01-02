import logging
import sys
import os
from logging.config import dictConfig
from app.config import settings

def setup_logging():
    """
    Configures application logging using dictConfig.
    - Captures 'uvicorn' and 'fastapi' logs.
    - Sets logical levels based on environment.
    - Uses a standard format for readability.
    - Writes logs to a rotating file in /app/logs/
    """
    
    log_level = "DEBUG" if settings.DEBUG else "INFO"
    log_dir = "logs" 
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "app.log")

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
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": log_file_path,
                "mode": "a",
                "maxBytes": 10 * 1024 * 1024, 
                "backupCount": 5,           
                "formatter": "default",
                "level": log_level,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "app": {
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": "INFO", 
                "propagate": False,
            },
            "passlib": {"handlers": ["console"], "level": "WARNING"},
            "urllib3": {"handlers": ["console"], "level": "WARNING"},
        },
        "root": {
            "handlers": ["console", "file"],
            "level": log_level,
        },
    }

    dictConfig(logging_config)
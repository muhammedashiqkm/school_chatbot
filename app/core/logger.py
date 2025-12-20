import logging
import sys
from app.config import settings

def setup_logging():
    """
    Configures the logging system.
    In production (Docker/K8s), we log to stdout so the container runtime handles it.
    """
    log_level = logging.INFO
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if root_logger.handlers:
        root_logger.handlers = []
    
    root_logger.addHandler(console_handler)

    logging.getLogger("passlib").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)
    app_logger.addHandler(console_handler)
    app_logger.propagate = False
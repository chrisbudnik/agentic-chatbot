import logging
import sys
from logging.handlers import RotatingFileHandler
from app.core.config import settings
import os


def setup_logging():
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler("logs/app.log", maxBytes=10*1024*1024, backupCount=5)
        ]
    )

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

# Initialize logging on import
setup_logging()
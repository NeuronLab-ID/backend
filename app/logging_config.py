"""
Logging Configuration - Centralized loguru setup for the entire application.

Configure via .env:
    LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL (default: INFO)
    LOG_FORMAT=json|pretty (default: pretty)
    LOG_FILE=path/to/file.log (optional, enables file logging)
"""
import os
import sys
from loguru import logger

# Remove default handler
logger.remove()

# Configuration from environment
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "pretty").lower()
LOG_FILE = os.getenv("LOG_FILE", "")

# Format configurations
PRETTY_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

SIMPLE_FORMAT = (
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan> - "
    "<level>{message}</level>"
)

JSON_FORMAT = "{message}"


def setup_logger():
    """
    Configure loguru logger based on environment variables.
    
    Call this once at application startup (in main.py).
    """
    # Select format
    if LOG_FORMAT == "json":
        fmt = JSON_FORMAT
        serialize = True
    else:
        fmt = SIMPLE_FORMAT
        serialize = False
    
    # Add console handler
    logger.add(
        sys.stderr,
        format=fmt,
        level=LOG_LEVEL,
        colorize=True,
        serialize=serialize,
        backtrace=True,
        diagnose=LOG_LEVEL == "DEBUG",
    )
    
    # Add file handler if configured
    if LOG_FILE:
        logger.add(
            LOG_FILE,
            format=PRETTY_FORMAT,
            level=LOG_LEVEL,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            serialize=False,
        )
        logger.info(f"File logging enabled: {LOG_FILE}")
    
    logger.info(f"Logger configured: level={LOG_LEVEL}, format={LOG_FORMAT}")
    
    return logger


def get_logger(name: str = None):
    """
    Get a logger instance with optional context binding.
    
    Usage:
        from app.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Hello!")
    """
    if name:
        return logger.bind(name=name)
    return logger


# Export configured logger
__all__ = ["logger", "setup_logger", "get_logger", "LOG_LEVEL"]

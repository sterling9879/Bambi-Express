"""
Logging utilities for the video generator.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> None:
    """
    Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        format_string: Custom format string for log messages
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Get numeric level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create handlers
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format=format_string,
        handlers=handlers
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter with job context."""

    def __init__(self, logger: logging.Logger, job_id: str):
        super().__init__(logger, {"job_id": job_id})

    def process(self, msg, kwargs):
        return f"[Job {self.extra['job_id']}] {msg}", kwargs


def get_job_logger(name: str, job_id: str) -> LoggerAdapter:
    """
    Get a logger instance with job context.

    Args:
        name: Logger name
        job_id: Job ID to include in log messages

    Returns:
        LoggerAdapter with job context
    """
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, job_id)

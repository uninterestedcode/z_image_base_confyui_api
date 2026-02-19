"""Logging configuration for RunPod serverless handler."""

import logging
import sys
import os
from pythonjsonlogger import jsonlogger
from typing import Optional


def get_log_level() -> int:
    """Get log level from environment variable."""
    level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_str, logging.INFO)


def get_log_format() -> str:
    """Get log format from environment variable."""
    return os.getenv("LOG_FORMAT", "json").lower()


def setup_logger(
    name: str,
    level: Optional[int] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Set up a structured logger.
    
    Args:
        name: Logger name
        level: Logging level (defaults to LOG_LEVEL env var)
        log_format: "json" or "text" (defaults to LOG_FORMAT env var)
        
    Returns:
        Configured logger instance
    """
    if level is None:
        level = get_log_level()
    
    if log_format is None:
        log_format = get_log_format()
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Set formatter
    if log_format == "json":
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s',
            timestamp=True
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Add context filter
    logger.addFilter(ContextFilter())
    
    return logger


class ContextFilter(logging.Filter):
    """Add context information to log records."""
    
    def __init__(self):
        super().__init__()
        self.job_id = None
    
    def set_job_id(self, job_id: str):
        """Set the current job ID for context."""
        self.job_id = job_id
    
    def filter(self, record):
        """Add job_id to log record."""
        if self.job_id:
            record.job_id = self.job_id
        return True


# Global context filter instance
context_filter = ContextFilter()


def set_job_context(job_id: str):
    """Set the job ID context for all loggers."""
    context_filter.set_job_id(job_id)

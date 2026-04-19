"""Structured logging for SS-Crawler."""
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class StructuredFormatter(logging.Formatter):
    """Custom formatter with timestamp, level, and context."""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def format(self, record: logging.LogRecord) -> str:
        # Add extra context if present
        if hasattr(record, 'context'):
            record.msg = f"[{record.context}] {record.msg}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True,
    max_bytes: int = 10485760,
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up structured logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (with {date} placeholder)
        console: Whether to log to console
        max_bytes: Max bytes per log file before rotation
        backup_count: Number of backup files to keep
    """
    logger = logging.getLogger("ss_crawler")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    formatter = StructuredFormatter()
    
    # File handler with rotation
    if log_file:
        # Replace {date} placeholder
        log_path = log_file.format(date=datetime.now().strftime("%Y-%m-%d"))
        
        # Ensure directory exists
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


class ScrapeLogger:
    """Context-aware logger for scraping operations."""
    
    def __init__(self, logger: logging.Logger, context: str = ""):
        self.logger = logger
        self.context = context
    
    def _log(self, level: int, msg: str, *args, **kwargs):
        """Log with context."""
        extra = kwargs.pop('extra', {})
        extra['context'] = self.context
        self.logger.log(level, msg, *args, extra=extra, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self._log(logging.CRITICAL, msg, *args, **kwargs)
    
    def with_context(self, context: str) -> "ScrapeLogger":
        """Create new logger with additional context."""
        new_context = f"{self.context}>{context}" if self.context else context
        return ScrapeLogger(self.logger, new_context)


# Convenience function for quick setup
def get_logger(name: str = "ss_crawler", config=None) -> ScrapeLogger:
    """Get or create logger with optional config."""
    from src.utils.config import AppConfig
    
    if config is None:
        config = AppConfig()
    
    base_logger = setup_logging(
        level=config.logging.level,
        log_file=config.logging.file,
        console=config.logging.console,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count
    )
    
    return ScrapeLogger(base_logger, name)

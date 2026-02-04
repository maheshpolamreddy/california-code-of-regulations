"""
Centralized logging configuration for CCR Compliance Agent.
Provides structured logging with file and console handlers.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
import config

def setup_logger(name: str, log_file: str = None, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with both file and console handlers.
    
    Args:
        name: Logger name (typically module name)
        log_file: Optional log file name (stored in LOGS_DIR)
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log_file specified) - Wrap in try/except for Vercel read-only FS
    if log_file:
        try:
            log_path = config.LOGS_DIR / log_file
            # Ensure log directory exists
            if not config.LOGS_DIR.exists():
                try:
                    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
                except OSError:
                    # Read-only filesystem (Vercel), skip file logging
                    return logger
            
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # Fallback to console only if file access fails
            print(f"Notice: File logging disabled (Read-only filesystem?): {e}")
    
    return logger

# Create default loggers for different components
crawler_logger = setup_logger('crawler', 'crawler.log')
extraction_logger = setup_logger('extraction', 'extraction.log')
vectordb_logger = setup_logger('vectordb', 'vectordb.log')
agent_logger = setup_logger('agent', 'agent.log')

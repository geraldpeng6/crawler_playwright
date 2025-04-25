#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logging module for the web interaction element crawler.

This module provides logging functionality for the crawler.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger as loguru_logger

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Generate log filename with timestamp
log_filename = f"crawler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_path = logs_dir / log_filename

def setup_logger():
    """
    Set up and configure the logger.
    
    Returns:
        Configured logger instance
    """
    # Remove default handler
    loguru_logger.remove()
    
    # Add console handler
    loguru_logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # Add file handler
    loguru_logger.add(
        log_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="1 week"
    )
    
    return loguru_logger

def get_logger():
    """
    Get the logger instance.
    
    Returns:
        Logger instance
    """
    return loguru_logger

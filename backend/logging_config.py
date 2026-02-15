"""Logging configuration for ClawChat server.

This module provides structured logging setup with support for
file rotation and console output.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def setup_logging(config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """Configure and return the root logger for ClawChat.

    Args:
        config: Logging configuration dictionary. If None, uses defaults.

    Returns:
        Configured logger instance.
    """
    # Default configuration
    default_config = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'date_format': '%Y-%m-%d %H:%M:%S',
        'file': None,
        'max_bytes': 10 * 1024 * 1024,  # 10 MB
        'backup_count': 5,
        'console_output': True
    }

    # Merge with provided config
    if config:
        default_config.update(config)

    # Get the logger
    logger = logging.getLogger('clawchat')
    logger.setLevel(getattr(logging, default_config['level'].upper()))

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        default_config['format'],
        datefmt=default_config['date_format']
    )

    # Console handler
    if default_config.get('console_output', True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logger.level)
        logger.addHandler(console_handler)

    # File handler with rotation
    log_file = default_config.get('file')
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=default_config['max_bytes'],
            backupCount=default_config['backup_count'],
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logger.level)
        logger.addHandler(file_handler)

    # Suppress overly verbose loggers
    logging.getLogger('websockets.server').setLevel(logging.WARNING)
    logging.getLogger('websockets.protocol').setLevel(logging.WARNING)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance for the specified name.

    Args:
        name: Logger name. If None, returns the root ClawChat logger.

    Returns:
        Logger instance.
    """
    if name:
        return logging.getLogger(f'clawchat.{name}')
    return logging.getLogger('clawchat')

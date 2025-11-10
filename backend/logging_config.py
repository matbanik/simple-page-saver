"""
Logging configuration for Simple Page Saver
Handles file logging with configurable levels and API key masking
"""

import logging
import re
from pathlib import Path
from datetime import datetime


class APIKeyMaskingFilter(logging.Filter):
    """Filter to mask API keys in log output"""

    def __init__(self):
        super().__init__()
        # Pattern to match API keys (typical format: sk-xxxxx or similar)
        self.api_key_pattern = re.compile(r'(sk-[a-zA-Z0-9]{20,}|[a-zA-Z0-9]{32,})')

    def filter(self, record):
        # Mask API keys in the log message
        if isinstance(record.msg, str):
            record.msg = self.api_key_pattern.sub('***MASKED_API_KEY***', record.msg)

        # Also mask in args if present
        if record.args:
            record.args = tuple(
                self.api_key_pattern.sub('***MASKED_API_KEY***', str(arg))
                if isinstance(arg, str) else arg
                for arg in record.args
            )

        return True


def setup_logging(log_level: str = 'INFO', log_file: str = None):
    """
    Set up logging configuration

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (default: logs/app.log)

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # Default log file with timestamp
    if log_file is None:
        timestamp = datetime.now().strftime('%Y%m%d')
        log_file = log_dir / f'simple_page_saver_{timestamp}.log'
    else:
        log_file = Path(log_file)

    # Configure logging level
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger('simple_page_saver')
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create file handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Create formatter (no unicode characters for PowerShell compatibility)
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add API key masking filter
    api_key_filter = APIKeyMaskingFilter()
    file_handler.addFilter(api_key_filter)
    console_handler.addFilter(api_key_filter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f'Logging initialized - Level: {log_level}, File: {log_file}')

    return logger


def log_ai_request(logger, model: str, prompt_size: int, request_data: dict):
    """Log AI API request details"""
    logger.info(f'[AI Request] Model: {model}, Prompt size: {prompt_size} chars')
    logger.debug(f'[AI Request] Full data: {request_data}')


def log_ai_response(logger, model: str, response_size: int, used_ai: bool, error: str = None):
    """Log AI API response details"""
    if error:
        logger.error(f'[AI Response] Model: {model}, Error: {error}')
    else:
        status = 'AI' if used_ai else 'Fallback'
        logger.info(f'[AI Response] Model: {model}, Status: {status}, Response size: {response_size} chars')

"""
Logging configuration for Simple Page Saver
Implements non-blocking async-safe logging using QueueHandler and QueueListener
Best practice for FastAPI/async applications to avoid blocking the event loop
"""

import logging
import logging.handlers
import queue
import re
from pathlib import Path
from datetime import datetime
from typing import Optional


# Global queue listener instance (managed by lifespan)
_queue_listener: Optional[logging.handlers.QueueListener] = None


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
    Set up non-blocking async-safe logging configuration
    Uses QueueHandler + QueueListener for async compatibility

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (default: logs/simple_page_saver_YYYYMMDD.log)

    Returns:
        Configured logger instance

    Note:
        Must call start_queue_listener() after setup and stop_queue_listener() on shutdown
    """
    global _queue_listener

    # Create logs directory if it doesn't exist (CRITICAL: must exist before FileHandler creation)
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)

    # Default log file with timestamp
    if log_file is None:
        timestamp = datetime.now().strftime('%Y%m%d')
        log_file = log_dir / f'simple_page_saver_{timestamp}.log'
    else:
        log_file = Path(log_file)

    # Configure logging level
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Create root logger
    logger = logging.getLogger('simple_page_saver')
    logger.setLevel(level)
    logger.propagate = False  # Don't propagate to root logger

    # Remove existing handlers
    logger.handlers.clear()

    # ============================================================================
    # BLOCKING HANDLERS (will run in QueueListener's background thread)
    # ============================================================================

    # Create file handler (BLOCKING - but will run in background thread)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)

    # Create console handler (BLOCKING - but will run in background thread)
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

    # ============================================================================
    # NON-BLOCKING QUEUE-BASED LOGGING
    # ============================================================================

    # Create queue for non-blocking logging
    log_queue = queue.Queue(-1)  # Unbounded queue

    # Create QueueHandler (NON-BLOCKING - just puts messages in queue)
    queue_handler = logging.handlers.QueueHandler(log_queue)
    queue_handler.setLevel(level)

    # Add queue handler to logger (this is what the app will use)
    logger.addHandler(queue_handler)

    # Create QueueListener (will run blocking handlers in background thread)
    # IMPORTANT: This processes messages from queue in separate thread
    _queue_listener = logging.handlers.QueueListener(
        log_queue,
        file_handler,
        console_handler,
        respect_handler_level=True
    )

    # Log setup completion (will be async/non-blocking)
    logger.info(f'Non-blocking logging initialized - Level: {log_level}, File: {log_file}')
    logger.info(f'QueueHandler + QueueListener running in background thread')

    return logger


def start_queue_listener():
    """
    Start the queue listener background thread
    Call this during application startup (FastAPI lifespan startup)
    """
    global _queue_listener
    if _queue_listener:
        _queue_listener.start()
        print("[Logging] QueueListener started - non-blocking logging active")
    else:
        print("[Logging WARNING] QueueListener not initialized - call setup_logging() first")


def stop_queue_listener():
    """
    Stop the queue listener background thread
    Call this during application shutdown (FastAPI lifespan shutdown)
    Ensures all queued log messages are written before exit
    """
    global _queue_listener
    if _queue_listener:
        _queue_listener.stop()
        print("[Logging] QueueListener stopped - all queued messages flushed")
    else:
        print("[Logging WARNING] QueueListener not initialized")


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

"""
AI Converter using OpenRouter API
Converts preprocessed HTML to clean markdown
Falls back to Trafilatura (intelligent extraction) or html2text
"""

import os
import time
import html2text
import trafilatura
from typing import Optional, Tuple
import requests
from dotenv import load_dotenv
import logging
import concurrent.futures
import threading

load_dotenv()

# Setup optional standalone logging for conversion debugging
# IMPORTANT: Logging is DISABLED by default to avoid blocking I/O
# Set environment variable ENABLE_CONVERSION_LOGGING=true to enable detailed logs
def setup_conversion_logger():
    """Create optional independent logger for conversion debugging"""
    import os

    # Check if conversion logging is enabled
    if os.getenv('ENABLE_CONVERSION_LOGGING', 'false').lower() != 'true':
        return None

    try:
        from pathlib import Path
        from datetime import datetime
        import logging.handlers

        # Create logs directory if it doesn't exist
        log_dir = Path(__file__).parent / 'logs'
        log_dir.mkdir(exist_ok=True)

        # Create dedicated conversion log file
        timestamp = datetime.now().strftime('%Y%m%d')
        log_file = log_dir / f'conversion_debug_{timestamp}.log'

        # Create independent logger
        conv_logger = logging.getLogger('conversion_debug')
        conv_logger.setLevel(logging.INFO)
        conv_logger.propagate = False  # Don't propagate to parent loggers

        # Remove any existing handlers to avoid duplicates
        conv_logger.handlers.clear()

        # Use QueueHandler for non-blocking logging
        queue_handler = logging.handlers.QueueHandler(logging.handlers.queue.Queue(-1))
        conv_logger.addHandler(queue_handler)

        # Create file handler in background thread via QueueListener
        file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
        file_handler.setLevel(logging.INFO)

        # Simple formatter without unicode
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        # Start queue listener in background thread
        listener = logging.handlers.QueueListener(
            queue_handler.queue,
            file_handler,
            respect_handler_level=True
        )
        listener.start()

        # Store listener for cleanup
        conv_logger._listener = listener

        # Log initialization
        conv_logger.info(f"="*80)
        conv_logger.info(f"Conversion Debug Logger Initialized")
        conv_logger.info(f"Log file: {log_file}")
        conv_logger.info(f"="*80)

        return conv_logger
    except Exception as e:
        # If logging setup fails, don't block the application
        print(f"[WARNING] Failed to setup conversion logger: {e}")
        return None

logger = setup_conversion_logger()

# Safe logging wrapper
def log_info(message):
    """Safely log a message (no-op if logger disabled)"""
    if logger:
        try:
            logger.info(message)
        except Exception:
            pass  # Never let logging break the application

def log_warning(message):
    """Safely log a warning (no-op if logger disabled)"""
    if logger:
        try:
            logger.warning(message)
        except Exception:
            pass

def log_error(message, exc_info=False):
    """Safely log an error (no-op if logger disabled)"""
    if logger:
        try:
            logger.error(message, exc_info=exc_info)
        except Exception:
            pass


class AIConverter:
    """Converts HTML to Markdown using OpenRouter API with fallback"""

    # Model configurations with approximate costs
    MODELS = {
        'gpt-3.5-turbo': 'openai/gpt-3.5-turbo',
        'gpt-4-turbo': 'openai/gpt-4-turbo',
        'claude-sonnet': 'anthropic/claude-3-sonnet',
        'claude-haiku': 'anthropic/claude-3-haiku',
        'deepseek': 'deepseek/deepseek-chat'  # Very cost-effective
    }

    SYSTEM_PROMPT = """You are a content extraction specialist. Convert the provided HTML to clean, readable markdown.

Guidelines:
- Preserve all links with context using markdown syntax [text](url)
- Maintain heading hierarchy (# for h1, ## for h2, etc.)
- Extract tables accurately using markdown table syntax
- Include image alt text as markdown image syntax: ![alt](url)
- Remove navigation, footer, advertisements
- Focus only on main content
- Preserve code blocks with proper syntax
- Keep lists and formatting intact
- Output ONLY pure markdown with no explanations or commentary
- Do not add any introductory or concluding statements"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, extraction_mode: str = 'balanced'):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model or os.getenv('DEFAULT_MODEL', 'deepseek/deepseek-chat')
        self.max_tokens = int(os.getenv('MAX_TOKENS', '32000'))
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.extraction_mode = extraction_mode  # 'balanced', 'recall', 'precision'

        # Fallback converter (html2text) for when both AI and Trafilatura fail
        self.html2text_converter = html2text.HTML2Text()
        self.html2text_converter.ignore_links = False
        self.html2text_converter.ignore_images = False
        self.html2text_converter.ignore_emphasis = False
        self.html2text_converter.body_width = 0  # Don't wrap lines
        self.html2text_converter.ignore_tables = False

    def convert_to_markdown(self, html: str, title: str = "", custom_prompt: str = "") -> Tuple[str, bool, Optional[str]]:
        """
        Convert HTML to Markdown using AI or fallback chain
        Fallback order: AI → Trafilatura → html2text

        Args:
            html: Preprocessed HTML string
            title: Page title
            custom_prompt: Optional custom instructions for AI processing

        Returns:
            Tuple of (markdown_content, used_ai, error_message)
        """
        log_info(f"[CONVERSION START] HTML size: {len(html)} chars, Title: '{title}'")
        log_info(f"[CONVERSION] API key available: {bool(self.api_key)}")

        # Try AI conversion first if API key is available
        if self.api_key:
            try:
                log_info("[CONVERSION] Attempting AI conversion...")
                markdown = self._convert_with_ai(html, title, custom_prompt)
                log_info(f"[CONVERSION] AI conversion SUCCESS - {len(markdown)} chars")
                return markdown, True, None
            except Exception as e:
                log_warning(f"[CONVERSION] AI conversion FAILED: {e}")
                print(f"AI conversion failed: {e}. Falling back to Trafilatura.")
                error_msg = str(e)
        else:
            log_info("[CONVERSION] No API key - skipping AI conversion")
            error_msg = "No API key provided"

        # Try Trafilatura extraction
        log_info("[CONVERSION] Attempting Trafilatura extraction...")
        try:
            markdown = self._convert_with_trafilatura(html, title, timeout=30)
            if markdown and len(markdown.strip()) > 50:  # Ensure meaningful content
                log_info(f"[CONVERSION] Trafilatura SUCCESS - {len(markdown)} chars")
                print(f"Using Trafilatura extraction (mode: {self.extraction_mode})")
                return markdown, False, error_msg
            else:
                log_warning(f"[CONVERSION] Trafilatura returned insufficient content: {len(markdown) if markdown else 0} chars")
                print("Trafilatura extraction returned insufficient content, falling back to html2text")
        except concurrent.futures.TimeoutError:
            log_error("[CONVERSION] Trafilatura TIMEOUT after 30s")
            print("Trafilatura timed out after 30s. Falling back to html2text.")
        except Exception as e:
            log_error(f"[CONVERSION] Trafilatura FAILED: {e}", exc_info=True)
            print(f"Trafilatura failed: {e}. Falling back to html2text.")

        # Final fallback to html2text
        log_info("[CONVERSION] Attempting html2text fallback...")
        try:
            markdown = self._convert_with_html2text(html, title, timeout=30)
            log_info(f"[CONVERSION] html2text SUCCESS - {len(markdown)} chars")
            return markdown, False, error_msg
        except concurrent.futures.TimeoutError:
            log_error("[CONVERSION] html2text TIMEOUT after 30s")
            raise TimeoutError("HTML to markdown conversion timed out after 30 seconds")
        except Exception as e:
            log_error(f"[CONVERSION] html2text FAILED: {e}", exc_info=True)
            raise

    def _convert_with_ai(self, html: str, title: str, custom_prompt: str = "") -> str:
        """Convert HTML to markdown using OpenRouter API"""

        # Build user prompt with custom instructions if provided
        user_prompt_parts = ["Convert the following HTML to clean markdown."]

        if custom_prompt:
            user_prompt_parts.append(f"\nAdditional Instructions:\n{custom_prompt}")

        if title:
            user_prompt_parts.append(f"\nPage Title: {title}")

        user_prompt_parts.append(f"\nHTML:\n{html}")

        user_prompt = "\n".join(user_prompt_parts)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 4000,  # Output tokens
            "temperature": 0.3,  # Lower temperature for more consistent output
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/simple-page-saver",  # Optional
            "X-Title": "Simple Page Saver"  # Optional
        }

        # Log full request (without API key)
        print(f"[OpenRouter Request]")
        print(f"  URL: {self.base_url}")
        print(f"  Model: {payload['model']}")
        print(f"  System Prompt: {payload['messages'][0]['content'][:200]}...")
        print(f"  User Prompt Length: {len(payload['messages'][1]['content'])} chars")
        print(f"  Max Tokens: {payload['max_tokens']}")
        print(f"  Temperature: {payload['temperature']}")

        # Implement retry logic with exponential backoff
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                print(f"[OpenRouter] Sending request (attempt {attempt + 1}/{max_retries})...")
                response = requests.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=60
                )

                print(f"[OpenRouter Response] Status: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    print(f"[OpenRouter Response] Success!")
                    print(f"  Model Used: {result.get('model', 'N/A')}")
                    print(f"  Response Length: {len(result['choices'][0]['message']['content'])} chars")
                    if 'usage' in result:
                        print(f"  Token Usage: {result['usage']}")
                    markdown = result['choices'][0]['message']['content']
                    return markdown.strip()
                elif response.status_code == 429:  # Rate limit
                    print(f"[OpenRouter] Rate limited, retrying in {retry_delay}s...")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        raise Exception(f"Rate limited after {max_retries} attempts")
                else:
                    error_text = response.text
                    print(f"[OpenRouter Response] Error: {error_text}")
                    raise Exception(f"API error {response.status_code}: {error_text}")

            except requests.exceptions.Timeout:
                print(f"[OpenRouter] Request timed out after 60s")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise Exception("Request timeout after retries")

            except requests.exceptions.RequestException as e:
                print(f"[OpenRouter] Request exception: {str(e)}")
                raise Exception(f"Request failed: {str(e)}")

        raise Exception("Failed to convert after all retries")

    def _convert_with_trafilatura_unsafe(self, html: str, title: str) -> str:
        """
        Intelligent content extraction using Trafilatura (internal, no timeout)
        Supports three extraction modes: balanced, recall, precision
        """
        # Configure extraction based on mode
        favor_recall = self.extraction_mode == 'recall'
        favor_precision = self.extraction_mode == 'precision'

        log_info(f"[Trafilatura] Starting extraction with mode: {self.extraction_mode}")
        log_info(f"[Trafilatura] HTML size: {len(html)} chars")
        log_info(f"[Trafilatura] favor_recall={favor_recall}, favor_precision={favor_precision}")
        print(f"[Trafilatura] Extracting with mode: {self.extraction_mode}")
        print(f"  favor_recall={favor_recall}, favor_precision={favor_precision}")

        # Extract text content using Trafilatura
        log_info("[Trafilatura] Calling trafilatura.extract()...")
        start_time = time.time()

        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,  # Include tables for better data preservation
            include_images=True,  # Include image references
            include_links=True,   # Preserve links
            favor_recall=favor_recall,
            favor_precision=favor_precision,
            output_format='markdown'  # Direct markdown output
        )

        elapsed = time.time() - start_time
        log_info(f"[Trafilatura] trafilatura.extract() completed in {elapsed:.2f}s")

        if not text:
            log_warning("[Trafilatura] Extraction returned no content")
            raise ValueError("Trafilatura extraction returned no content")

        log_info(f"[Trafilatura] Extracted text length: {len(text)} chars")

        # Add title if provided and not already present
        if title and not text.startswith(f"# {title}"):
            log_info(f"[Trafilatura] Adding title: {title}")
            text = f"# {title}\n\n{text}"

        print(f"[Trafilatura] Extracted {len(text)} characters")
        log_info(f"[Trafilatura] Final output: {len(text)} chars")
        return text.strip()

    def _convert_with_trafilatura(self, html: str, title: str, timeout: int = 30) -> str:
        """
        Trafilatura extraction with timeout protection
        """
        log_info(f"[Trafilatura] Starting with {timeout}s timeout")
        thread_id = threading.current_thread().ident
        log_info(f"[Trafilatura] Running in thread: {thread_id}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._convert_with_trafilatura_unsafe, html, title)
            try:
                result = future.result(timeout=timeout)
                log_info(f"[Trafilatura] Completed successfully within timeout")
                return result
            except concurrent.futures.TimeoutError:
                log_error(f"[Trafilatura] TIMEOUT after {timeout}s - operation did not complete")
                raise

    def _convert_with_html2text_unsafe(self, html: str, title: str) -> str:
        """Final fallback conversion using html2text library (internal, no timeout)"""
        log_info("[html2text] Starting html2text conversion")
        log_info(f"[html2text] HTML size: {len(html)} chars")
        log_info(f"[html2text] Title: '{title}'")
        print("[html2text] Using basic html2text conversion")

        # Add title if provided
        if title:
            log_info(f"[html2text] Prepending title: {title}")
            markdown = f"# {title}\n\n"
        else:
            markdown = ""

        log_info("[html2text] Calling self.html2text_converter.handle()...")
        start_time = time.time()

        try:
            text = self.html2text_converter.handle(html)
            elapsed = time.time() - start_time
            log_info(f"[html2text] handle() completed in {elapsed:.2f}s")
            log_info(f"[html2text] Output text length: {len(text)} chars")
        except Exception as e:
            elapsed = time.time() - start_time
            log_error(f"[html2text] EXCEPTION after {elapsed:.2f}s: {e}", exc_info=True)
            raise

        markdown += text.strip()
        log_info(f"[html2text] Final markdown length: {len(markdown)} chars")

        return markdown

    def _convert_with_html2text(self, html: str, title: str, timeout: int = 30) -> str:
        """
        html2text conversion with timeout protection
        This is the final fallback when both AI and Trafilatura fail
        """
        log_info(f"[html2text] Starting with {timeout}s timeout")
        thread_id = threading.current_thread().ident
        log_info(f"[html2text] Running in thread: {thread_id}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._convert_with_html2text_unsafe, html, title)
            try:
                log_info("[html2text] Waiting for conversion to complete...")
                result = future.result(timeout=timeout)
                log_info(f"[html2text] Completed successfully within timeout")
                return result
            except concurrent.futures.TimeoutError:
                log_error(f"[html2text] TIMEOUT after {timeout}s - operation did not complete")
                log_error(f"[html2text] This indicates html2text.handle() is hanging indefinitely")
                log_error(f"[html2text] HTML may contain problematic content causing infinite loop")
                raise

    def chunk_html(self, html: str, max_chars: int = 80000) -> list:
        """
        Split HTML into chunks if too large
        Splits at major heading boundaries

        Args:
            html: HTML string
            max_chars: Maximum characters per chunk

        Returns:
            List of HTML chunks
        """
        if len(html) <= max_chars:
            return [html]

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'lxml')
        chunks = []
        current_chunk = []
        current_size = 0

        # Find all top-level elements
        body = soup.find('body') or soup
        for element in body.children:
            if hasattr(element, 'name'):
                element_str = str(element)
                element_size = len(element_str)

                # If adding this element would exceed max_chars and we have content, start new chunk
                if current_size + element_size > max_chars and current_chunk:
                    chunks.append(''.join(current_chunk))
                    current_chunk = [element_str]
                    current_size = element_size
                else:
                    current_chunk.append(element_str)
                    current_size += element_size

        # Add remaining chunk
        if current_chunk:
            chunks.append(''.join(current_chunk))

        return chunks

    def convert_large_html(self, html: str, title: str = "", custom_prompt: str = "") -> Tuple[str, bool, Optional[str]]:
        """
        Convert large HTML by chunking if necessary

        Args:
            html: HTML string
            title: Page title
            custom_prompt: Optional custom instructions for AI processing

        Returns:
            Tuple of (markdown_content, used_ai, error_message)
        """
        # Check if chunking is needed (80K chars ≈ 20K tokens)
        if len(html) <= 80000:
            return self.convert_to_markdown(html, title, custom_prompt)

        chunks = self.chunk_html(html)
        markdown_parts = []
        used_ai = False
        errors = []

        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)}")
            md, ai_used, error = self.convert_to_markdown(chunk, title if i == 0 else "", custom_prompt)
            markdown_parts.append(md)
            used_ai = used_ai or ai_used
            if error:
                errors.append(f"Chunk {i+1}: {error}")

        full_markdown = "\n\n---\n\n".join(markdown_parts)
        error_msg = "; ".join(errors) if errors else None

        return full_markdown, used_ai, error_msg


def estimate_cost(html: str, model: str = 'deepseek/deepseek-chat') -> dict:
    """
    Estimate the cost of processing HTML

    Args:
        html: HTML string
        model: Model identifier

    Returns:
        Dict with token estimates and cost
    """
    # Rough token estimation (1 token ≈ 4 characters)
    input_tokens = len(html) // 4

    # Approximate costs per 1M tokens (as of 2024)
    costs = {
        'openai/gpt-3.5-turbo': {'input': 0.50, 'output': 1.50},
        'openai/gpt-4-turbo': {'input': 10.00, 'output': 30.00},
        'anthropic/claude-3-sonnet': {'input': 3.00, 'output': 15.00},
        'anthropic/claude-3-haiku': {'input': 0.25, 'output': 1.25},
        'deepseek/deepseek-chat': {'input': 0.14, 'output': 0.28}
    }

    model_cost = costs.get(model, costs['deepseek/deepseek-chat'])

    # Estimate output tokens (usually less than input)
    output_tokens = input_tokens // 2

    input_cost = (input_tokens / 1_000_000) * model_cost['input']
    output_cost = (output_tokens / 1_000_000) * model_cost['output']
    total_cost = input_cost + output_cost

    return {
        'estimated_input_tokens': input_tokens,
        'estimated_output_tokens': output_tokens,
        'estimated_cost_usd': round(total_cost, 6),
        'model': model
    }

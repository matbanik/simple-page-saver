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

# Use child logger of main 'simple_page_saver' logger for proper hierarchy
# This automatically inherits the QueueHandler setup from main logger (non-blocking!)
logger = logging.getLogger('simple_page_saver.ai_converter')

# Note: No handler setup needed here - it inherits from parent logger
# The parent logger uses QueueHandler + QueueListener for non-blocking async-safe logging


class AIConverter:
    """Converts HTML to Markdown using OpenRouter API with fallback"""

    # Model configurations with context window limits (in tokens)
    MODEL_CONTEXT_LIMITS = {
        'openai/gpt-3.5-turbo': 16000,
        'openai/gpt-4-turbo': 128000,
        'openai/gpt-4o': 128000,
        'anthropic/claude-3-sonnet': 200000,
        'anthropic/claude-3-haiku': 200000,
        'anthropic/claude-3.5-sonnet': 200000,
        'deepseek/deepseek-chat': 128000,
        'google/gemini-pro': 32000,
        'google/gemini-1.5-pro': 1000000,
        'meta-llama/llama-3-70b': 8000,
    }

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

    def get_model_context_limit(self) -> int:
        """
        Get the context window limit for the current model

        Priority:
        1. Query OpenRouter API for real-time model info
        2. Check local cache
        3. Fallback to hardcoded limits
        4. Default to 128K

        Returns:
            Maximum context tokens for the model (defaults to 128K if unknown)
        """
        # Try querying OpenRouter API for model info
        if self.api_key:
            try:
                context_limit = self._query_openrouter_model_info(self.model)
                if context_limit:
                    logger.info(f"[Model Context] OpenRouter API: '{self.model}' has {context_limit} token context")
                    return context_limit
            except Exception as e:
                logger.warning(f"[Model Context] Failed to query OpenRouter API: {e}")

        # Try exact match in hardcoded limits
        if self.model in self.MODEL_CONTEXT_LIMITS:
            return self.MODEL_CONTEXT_LIMITS[self.model]

        # Try fuzzy match (e.g., "gpt-4-turbo-preview" matches "gpt-4-turbo")
        for known_model, limit in self.MODEL_CONTEXT_LIMITS.items():
            if known_model in self.model or self.model in known_model:
                logger.info(f"[Model Context] Fuzzy matched '{self.model}' to '{known_model}': {limit} tokens")
                return limit

        # Default to conservative 128K for unknown models
        logger.warning(f"[Model Context] Unknown model '{self.model}', defaulting to 128K context limit")
        return 128000

    def _query_openrouter_model_info(self, model_id: str) -> Optional[int]:
        """
        Query OpenRouter API for model context length

        Args:
            model_id: Model identifier (e.g., 'anthropic/claude-3-sonnet')

        Returns:
            Context length in tokens, or None if not found
        """
        try:
            url = "https://openrouter.ai/api/v1/models"
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            response = requests.get(url, headers=headers, timeout=5)

            if response.status_code == 200:
                models = response.json().get('data', [])

                # Find matching model
                for model in models:
                    if model.get('id') == model_id:
                        context_length = model.get('context_length')
                        if context_length:
                            return int(context_length)
                        break

            return None
        except Exception as e:
            logger.debug(f"[Model Context] OpenRouter API query failed: {e}")
            return None

    def convert_to_markdown(self, html: str, title: str = "", custom_prompt: str = "", use_ai: bool = True) -> Tuple[str, bool, Optional[str]]:
        """
        Convert HTML to Markdown using AI or fallback chain
        Fallback order: AI -> Trafilatura -> html2text

        Args:
            html: Preprocessed HTML string
            title: Page title
            custom_prompt: Optional custom instructions for AI processing
            use_ai: Whether to use AI conversion (default: True)

        Returns:
            Tuple of (markdown_content, used_ai, error_message)
        """
        logger.info(f"[CONVERSION START] HTML size: {len(html)} chars, Title: '{title}'")
        logger.info(f"[CONVERSION] API key available: {bool(self.api_key)}, use_ai: {use_ai}")

        # Try AI conversion first if API key is available AND use_ai is True
        if self.api_key and use_ai:
            try:
                logger.info("[CONVERSION] Attempting AI conversion...")
                markdown = self._convert_with_ai(html, title, custom_prompt)
                logger.info(f"[CONVERSION] AI conversion SUCCESS - {len(markdown)} chars")
                return markdown, True, None
            except Exception as e:
                logger.warning(f"[CONVERSION] AI conversion FAILED: {e}")
                print(f"AI conversion failed: {e}. Falling back to Trafilatura.")
                error_msg = str(e)
        else:
            logger.info("[CONVERSION] No API key - skipping AI conversion")
            error_msg = "No API key provided"

        # Try Trafilatura extraction
        logger.info("[CONVERSION] Attempting Trafilatura extraction...")
        try:
            markdown = self._convert_with_trafilatura(html, title, timeout=30)
            if markdown and len(markdown.strip()) > 50:  # Ensure meaningful content
                logger.info(f"[CONVERSION] Trafilatura SUCCESS - {len(markdown)} chars")
                print(f"Using Trafilatura extraction (mode: {self.extraction_mode})")
                return markdown, False, error_msg
            else:
                logger.warning(f"[CONVERSION] Trafilatura returned insufficient content: {len(markdown) if markdown else 0} chars")
                print("Trafilatura extraction returned insufficient content, falling back to html2text")
        except concurrent.futures.TimeoutError:
            logger.error("[CONVERSION] Trafilatura TIMEOUT after 30s")
            print("Trafilatura timed out after 30s. Falling back to html2text.")
        except Exception as e:
            logger.error(f"[CONVERSION] Trafilatura FAILED: {e}", exc_info=True)
            print(f"Trafilatura failed: {e}. Falling back to html2text.")

        # Final fallback to html2text
        logger.info("[CONVERSION] Attempting html2text fallback...")
        try:
            markdown = self._convert_with_html2text(html, title, timeout=30)
            logger.info(f"[CONVERSION] html2text SUCCESS - {len(markdown)} chars")
            return markdown, False, error_msg
        except concurrent.futures.TimeoutError:
            logger.error("[CONVERSION] html2text TIMEOUT after 30s")
            raise TimeoutError("HTML to markdown conversion timed out after 30 seconds")
        except Exception as e:
            logger.error(f"[CONVERSION] html2text FAILED: {e}", exc_info=True)
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

        # Validate request size before sending - use PRECISE token counting
        from preprocessing import count_tokens

        # Extract model name for tokenizer (normalize OpenRouter format)
        model_name = self.model.split('/')[-1] if '/' in self.model else self.model

        # Count exact tokens in the actual payloads
        system_tokens = count_tokens(self.SYSTEM_PROMPT, model_name)
        user_tokens = count_tokens(user_prompt, model_name)
        output_tokens = 4000  # What we're requesting in max_tokens

        # Total tokens = input (system + user) + output
        input_tokens = system_tokens + user_tokens
        total_tokens = input_tokens + output_tokens

        # Get model-specific context limit dynamically
        max_context = self.get_model_context_limit()

        logger.info(f"[Token Count] System: {system_tokens}, User: {user_tokens}, Output: {output_tokens}, Total: {total_tokens}")
        logger.info(f"[Token Count] Model: {self.model}, Context Limit: {max_context}")
        print(f"[Token Count] Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}, Limit: {max_context}")

        if total_tokens > max_context:
            raise ValueError(
                f"Content too large: {total_tokens} tokens (input: {input_tokens}, output: {output_tokens}) "
                f"exceeds {max_context} limit for model '{self.model}'. Please use chunking for large content."
            )

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
        from copy import deepcopy
        from trafilatura.settings import DEFAULT_CONFIG

        # Configure extraction based on mode
        favor_recall = self.extraction_mode == 'recall'
        favor_precision = self.extraction_mode == 'precision'

        logger.info(f"[Trafilatura] Starting extraction with mode: {self.extraction_mode}")
        logger.info(f"[Trafilatura] HTML size: {len(html)} chars")
        logger.info(f"[Trafilatura] favor_recall={favor_recall}, favor_precision={favor_precision}")
        print(f"[Trafilatura] Extracting with mode: {self.extraction_mode}")
        print(f"  favor_recall={favor_recall}, favor_precision={favor_precision}")

        # Create custom config to fix spacing issues
        # Issue: MIN_EXTRACTED_SIZE default of 250 causes word bunching
        # Solution: Lower threshold to prevent secondary extraction algorithm
        config = deepcopy(DEFAULT_CONFIG)
        config['DEFAULT']['MIN_EXTRACTED_SIZE'] = '100'  # Lower from default 250
        logger.info("[Trafilatura] Using custom config: MIN_EXTRACTED_SIZE=100 (default: 250)")

        # Extract text content using Trafilatura
        logger.info("[Trafilatura] Calling trafilatura.extract()...")
        start_time = time.time()

        # Configure what to include/exclude to minimize token usage while preserving visible text
        # Exclude images and links to reduce tokens - AI will focus on text content
        # Keep tables as they contain important structured data
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,     # Keep tables for data
            include_images=False,    # Drop images to save tokens
            include_links=False,     # Drop links to save tokens
            include_formatting=True, # Keep minimal formatting for readability
            favor_recall=favor_recall,
            favor_precision=favor_precision,
            output_format='markdown', # Direct markdown output
            config=config  # Use custom config to fix spacing
        )

        logger.info(f"[Trafilatura] Extraction complete - images: False, links: False (token optimization)")

        elapsed = time.time() - start_time
        logger.info(f"[Trafilatura] trafilatura.extract() completed in {elapsed:.2f}s")

        if not text:
            logger.warning("[Trafilatura] Extraction returned no content")
            raise ValueError("Trafilatura extraction returned no content")

        logger.info(f"[Trafilatura] Extracted text length: {len(text)} chars")

        # Add title if provided and not already present
        if title and not text.startswith(f"# {title}"):
            logger.info(f"[Trafilatura] Adding title: {title}")
            text = f"# {title}\n\n{text}"

        print(f"[Trafilatura] Extracted {len(text)} characters")
        logger.info(f"[Trafilatura] Final output: {len(text)} chars")
        return text.strip()

    def _convert_with_trafilatura(self, html: str, title: str, timeout: int = 30) -> str:
        """
        Trafilatura extraction with timeout protection
        """
        logger.info(f"[Trafilatura] Starting with {timeout}s timeout")
        thread_id = threading.current_thread().ident
        logger.info(f"[Trafilatura] Running in thread: {thread_id}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._convert_with_trafilatura_unsafe, html, title)
            try:
                result = future.result(timeout=timeout)
                logger.info(f"[Trafilatura] Completed successfully within timeout")
                return result
            except concurrent.futures.TimeoutError:
                logger.error(f"[Trafilatura] TIMEOUT after {timeout}s - operation did not complete")
                raise

    def _convert_with_html2text_unsafe(self, html: str, title: str) -> str:
        """Final fallback conversion using html2text library (internal, no timeout)"""
        logger.info("[html2text] Starting html2text conversion")
        logger.info(f"[html2text] HTML size: {len(html)} chars")
        logger.info(f"[html2text] Title: '{title}'")
        print("[html2text] Using basic html2text conversion")

        # Add title if provided
        if title:
            logger.info(f"[html2text] Prepending title: {title}")
            markdown = f"# {title}\n\n"
        else:
            markdown = ""

        logger.info("[html2text] Calling self.html2text_converter.handle()...")
        start_time = time.time()

        try:
            text = self.html2text_converter.handle(html)
            elapsed = time.time() - start_time
            logger.info(f"[html2text] handle() completed in {elapsed:.2f}s")
            logger.info(f"[html2text] Output text length: {len(text)} chars")
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[html2text] EXCEPTION after {elapsed:.2f}s: {e}", exc_info=True)
            raise

        markdown += text.strip()
        logger.info(f"[html2text] Final markdown length: {len(markdown)} chars")

        return markdown

    def _convert_with_html2text(self, html: str, title: str, timeout: int = 30) -> str:
        """
        html2text conversion with timeout protection
        This is the final fallback when both AI and Trafilatura fail
        """
        logger.info(f"[html2text] Starting with {timeout}s timeout")
        thread_id = threading.current_thread().ident
        logger.info(f"[html2text] Running in thread: {thread_id}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._convert_with_html2text_unsafe, html, title)
            try:
                logger.info("[html2text] Waiting for conversion to complete...")
                result = future.result(timeout=timeout)
                logger.info(f"[html2text] Completed successfully within timeout")
                return result
            except concurrent.futures.TimeoutError:
                logger.error(f"[html2text] TIMEOUT after {timeout}s - operation did not complete")
                logger.error(f"[html2text] This indicates html2text.handle() is hanging indefinitely")
                logger.error(f"[html2text] HTML may contain problematic content causing infinite loop")
                raise

    def chunk_html(self, html: str, max_chars: int = 80000) -> list:
        """
        Split HTML into chunks if too large
        Splits at paragraph/newline boundaries for better semantic coherence

        Args:
            html: HTML string
            max_chars: Maximum characters per chunk

        Returns:
            List of HTML chunks
        """
        if len(html) <= max_chars:
            return [html]

        logger.info(f"[Chunking] Splitting {len(html)} chars into chunks of max {max_chars} chars")

        # Split by paragraphs first (double newlines), then single newlines
        # This preserves semantic boundaries better than HTML structure parsing
        paragraphs = html.split('\n\n')

        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para) + 2  # +2 for the \n\n we'll add back

            # If this single paragraph is larger than max_chars, split it further
            if para_size > max_chars:
                # Save current chunk if it has content
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0

                # Split large paragraph by sentences/lines
                lines = para.split('\n')
                temp_chunk = []
                temp_size = 0

                for line in lines:
                    line_size = len(line) + 1  # +1 for \n

                    if temp_size + line_size > max_chars and temp_chunk:
                        # Flush temp chunk
                        chunks.append('\n'.join(temp_chunk))
                        temp_chunk = [line]
                        temp_size = line_size
                    else:
                        temp_chunk.append(line)
                        temp_size += line_size

                # Add remaining lines
                if temp_chunk:
                    chunks.append('\n'.join(temp_chunk))

            # Normal paragraph - check if adding it would exceed limit
            elif current_size + para_size > max_chars and current_chunk:
                # Start new chunk
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                # Add to current chunk
                current_chunk.append(para)
                current_size += para_size

        # Add remaining chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        logger.info(f"[Chunking] Created {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            logger.info(f"[Chunking] Chunk {i+1}: {len(chunk)} chars")

        return chunks

    def convert_large_html(self, html: str, title: str = "", custom_prompt: str = "", extraction_strategy: str = "markdown", worker_count: int = 4, overlap_percentage: float = 0.1) -> Tuple[str, bool, Optional[str]]:
        """
        Convert large HTML with intelligent chunking and parallel processing
        COMPLETE OVERHAUL - Inspired by Crawl4AI architecture

        Args:
            html: HTML string
            title: Page title
            custom_prompt: Optional custom instructions for AI processing
            extraction_strategy: 'markdown', 'structured', or 'combined'
            worker_count: Number of parallel workers (default 4)
            overlap_percentage: Chunk overlap percentage (default 0.1 = 10%)

        Returns:
            Tuple of (content, used_ai, error_message)
            - For 'markdown': content is markdown string
            - For 'structured': content is JSON string
            - For 'combined': content is JSON with both formats
        """
        from token_manager import TokenManager
        from chunking import SmartChunker
        from parallel_processor import ParallelChunkProcessor, ChunkResult
        from extraction_strategies import get_strategy
        from result_merger import ResultMerger
        from processing_monitor import ProcessingMonitor

        # Initialize components
        token_mgr = TokenManager(self.api_key)
        monitor = ProcessingMonitor()
        monitor.start_processing()

        # Extract model name for tokenizer
        model_name = self.model.split('/')[-1] if '/' in self.model else self.model

        # Calculate token budget
        budget = token_mgr.calculate_token_budget(
            model_id=self.model,
            system_prompt=self.SYSTEM_PROMPT,
            custom_prompt=custom_prompt,
            title=title,
            output_tokens=4000,
            safety_margin=0.95
        )

        logger.info(f"[Processing] Token budget: {budget['max_input_tokens']} tokens available for input")
        print(f"[Processing] Token budget: {budget['max_input_tokens']} input tokens (max context: {budget['max_context']})")

        # Count HTML tokens
        html_tokens = token_mgr.count_tokens(html, model_name)

        # Check if chunking is needed
        if html_tokens <= budget['max_input_tokens']:
            logger.info(f"[Processing] No chunking needed: {html_tokens} <= {budget['max_input_tokens']}")
            print(f"[Processing] No chunking needed: {html_tokens} tokens")
            return self.convert_to_markdown(html, title, custom_prompt)

        # Chunking required
        logger.info(f"[Processing] Chunking required: {html_tokens} > {budget['max_input_tokens']}")
        print(f"[Processing] Chunking required: {html_tokens} tokens exceeds limit")

        # Create chunker with overlap
        chunker = SmartChunker(
            max_tokens=int(budget['max_input_tokens'] * 0.8),  # Target 80% of max for safety
            model_name=model_name,
            overlap_percentage=overlap_percentage
        )

        # Chunk the HTML
        chunks, chunking_metadata = chunker.chunk_with_preallocation(html)
        monitor.set_chunking_metadata(chunking_metadata)

        logger.info(f"[Processing] Created {len(chunks)} chunks using {chunking_metadata['strategy']}")
        print(f"[Processing] Split into {len(chunks)} chunks (strategy: {chunking_metadata['strategy']})")

        # Check for oversized chunks
        if chunking_metadata['oversized_chunks']:
            error_msg = f"Chunking failed: {len(chunking_metadata['oversized_chunks'])} chunks exceed token limit"
            logger.error(f"[Processing] {error_msg}")
            print(f"[Processing] ERROR: {error_msg}")
            return "", False, error_msg

        # Setup extraction strategy
        strategy = get_strategy(extraction_strategy, instruction=custom_prompt)

        # Define chunk processing function
        def process_single_chunk(chunk_idx: int, chunk: str, args: dict) -> ChunkResult:
            """Process a single chunk (called by parallel processor)"""
            start_time = time.time()

            try:
                # Count input tokens
                input_tokens = token_mgr.count_tokens(chunk, model_name)

                # Build prompt using strategy
                chunk_title = title if chunk_idx == 0 else ""
                prompts = strategy.build_prompt(chunk, chunk_title, chunk_idx, len(chunks))

                # Convert chunk to markdown (the underlying method handles AI/fallback)
                md, ai_used, error = self.convert_to_markdown(chunk, chunk_title, custom_prompt)

                if error:
                    raise Exception(error)

                # Post-process using strategy
                md = strategy.post_process(md, chunk_idx)

                # Count output tokens
                output_tokens = token_mgr.count_tokens(md, model_name)

                processing_time = time.time() - start_time

                # Record metrics
                monitor.record_chunk_result(
                    chunk_index=chunk_idx,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    processing_time=processing_time,
                    success=True,
                    error=None,
                    strategy_used=strategy.__class__.__name__
                )

                return ChunkResult(
                    chunk_index=chunk_idx,
                    success=True,
                    output=md,
                    error=None,
                    tokens_processed=input_tokens,
                    processing_time=processing_time,
                    used_ai=ai_used
                )

            except Exception as e:
                processing_time = time.time() - start_time

                monitor.record_chunk_result(
                    chunk_index=chunk_idx,
                    input_tokens=0,
                    output_tokens=0,
                    processing_time=processing_time,
                    success=False,
                    error=str(e),
                    strategy_used=strategy.__class__.__name__
                )

                return ChunkResult(
                    chunk_index=chunk_idx,
                    success=False,
                    output=None,
                    error=str(e),
                    tokens_processed=0,
                    processing_time=processing_time,
                    used_ai=False
                )

        # Process chunks in parallel
        parallel_processor = ParallelChunkProcessor(max_workers=worker_count)
        results, parallel_metadata = parallel_processor.process_chunks(
            chunks=chunks,
            process_func=process_single_chunk,
            process_args={}
        )

        # Merge results based on extraction strategy
        successful_outputs = [r.output for r in results if r.success and r.output]

        if not successful_outputs:
            error_msg = "All chunks failed to process"
            logger.error(f"[Processing] {error_msg}")
            print(f"[Processing] ERROR: {error_msg}")
            return "", False, error_msg

        merger = ResultMerger(overlap_percentage=overlap_percentage)

        if extraction_strategy == 'structured':
            # Merge JSON blocks
            merge_result = merger.merge_json_chunks(successful_outputs)
        elif extraction_strategy == 'combined':
            # Merge combined format
            combined = merger.merge_combined_chunks(successful_outputs)
            merge_result = None  # Handle differently below
        else:
            # Default: merge markdown
            merge_result = merger.merge_markdown_chunks(successful_outputs)

        if merge_result:
            logger.info(f"[Processing] Merged {merge_result.chunk_count} chunks, removed {merge_result.overlap_removed} overlap")

        # Collect final metrics
        final_metrics = monitor.get_metrics(self.model)
        monitor.print_summary(final_metrics)

        # Check if any AI was used
        used_ai = any(r.used_ai for r in results)

        # Collect errors
        errors = [f"Chunk {r.chunk_index+1}: {r.error}" for r in results if not r.success]
        error_msg = "; ".join(errors) if errors else None

        # Return appropriate content based on strategy
        if extraction_strategy == 'combined':
            import json
            return json.dumps(combined, indent=2), used_ai, error_msg
        else:
            return merge_result.combined_text, used_ai, error_msg


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

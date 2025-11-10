"""
AI Converter using OpenRouter API
Converts preprocessed HTML to clean markdown
"""

import os
import time
import html2text
from typing import Optional, Tuple
import requests
from dotenv import load_dotenv

load_dotenv()


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

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model or os.getenv('DEFAULT_MODEL', 'deepseek/deepseek-chat')
        self.max_tokens = int(os.getenv('MAX_TOKENS', '32000'))
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

        # Fallback converter (html2text) for when API is unavailable
        self.html2text_converter = html2text.HTML2Text()
        self.html2text_converter.ignore_links = False
        self.html2text_converter.ignore_images = False
        self.html2text_converter.ignore_emphasis = False
        self.html2text_converter.body_width = 0  # Don't wrap lines
        self.html2text_converter.ignore_tables = False

    def convert_to_markdown(self, html: str, title: str = "", custom_prompt: str = "") -> Tuple[str, bool, Optional[str]]:
        """
        Convert HTML to Markdown using AI or fallback

        Args:
            html: Preprocessed HTML string
            title: Page title
            custom_prompt: Optional custom instructions for AI processing

        Returns:
            Tuple of (markdown_content, used_ai, error_message)
        """
        # Try AI conversion first if API key is available
        if self.api_key:
            try:
                markdown = self._convert_with_ai(html, title, custom_prompt)
                return markdown, True, None
            except Exception as e:
                print(f"AI conversion failed: {e}. Falling back to html2text.")
                error_msg = str(e)
        else:
            error_msg = "No API key provided"

        # Fallback to html2text
        markdown = self._convert_with_html2text(html, title)
        return markdown, False, error_msg

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

        # Implement retry logic with exponential backoff
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()
                    markdown = result['choices'][0]['message']['content']
                    return markdown.strip()
                elif response.status_code == 429:  # Rate limit
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        raise Exception(f"Rate limited after {max_retries} attempts")
                else:
                    raise Exception(f"API error {response.status_code}: {response.text}")

            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise Exception("Request timeout after retries")

            except requests.exceptions.RequestException as e:
                raise Exception(f"Request failed: {str(e)}")

        raise Exception("Failed to convert after all retries")

    def _convert_with_html2text(self, html: str, title: str) -> str:
        """Fallback conversion using html2text library"""
        markdown = self.html2text_converter.handle(html)

        # Add title if provided
        if title:
            markdown = f"# {title}\n\n{markdown}"

        return markdown.strip()

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

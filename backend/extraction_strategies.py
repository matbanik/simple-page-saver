"""
Extraction Strategy Framework
Inspired by Crawl4AI's ExtractionStrategy classes
Supports both Markdown and Structured (JSON) extraction
"""

import logging
import json
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger('simple_page_saver.extraction_strategies')


class ExtractionStrategy(ABC):
    """Base class for extraction strategies"""

    def __init__(self, system_prompt: str, instruction: Optional[str] = None):
        self.system_prompt = system_prompt
        self.instruction = instruction

    @abstractmethod
    def build_prompt(self, html: str, title: str, chunk_index: int, total_chunks: int) -> Dict[str, str]:
        """
        Build the prompt for AI model

        Returns:
            Dict with 'system' and 'user' messages
        """
        pass

    @abstractmethod
    def post_process(self, response: str, chunk_index: int) -> str:
        """Post-process AI response"""
        pass


class MarkdownExtractionStrategy(ExtractionStrategy):
    """Extract content as clean markdown (default strategy)"""

    DEFAULT_SYSTEM_PROMPT = """You are a content extraction specialist. Convert the provided HTML to clean, readable markdown.

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

    def __init__(self, instruction: Optional[str] = None):
        super().__init__(self.DEFAULT_SYSTEM_PROMPT, instruction)

    def build_prompt(self, html: str, title: str, chunk_index: int, total_chunks: int) -> Dict[str, str]:
        """Build markdown extraction prompt"""

        user_parts = ["Convert the following HTML to clean markdown."]

        # Add chunking context if multiple chunks
        if total_chunks > 1:
            user_parts.append(f"\nNote: This is chunk {chunk_index + 1} of {total_chunks}. Extract content naturally without adding chunk markers.")

        # Add custom instruction if provided
        if self.instruction:
            user_parts.append(f"\nAdditional Instructions:\n{self.instruction}")

        # Add title (only for first chunk)
        if title and chunk_index == 0:
            user_parts.append(f"\nPage Title: {title}")

        # Add HTML content
        user_parts.append(f"\nHTML:\n{html}")

        return {
            'system': self.system_prompt,
            'user': '\n'.join(user_parts)
        }

    def post_process(self, response: str, chunk_index: int) -> str:
        """Clean up markdown response"""
        # Remove any leading/trailing whitespace
        cleaned = response.strip()

        # Remove common AI artifacts
        artifacts = [
            "Here is the markdown:",
            "Here's the markdown:",
            "Here is the converted markdown:",
            "```markdown",
            "```"
        ]

        for artifact in artifacts:
            if cleaned.lower().startswith(artifact.lower()):
                cleaned = cleaned[len(artifact):].strip()
            if cleaned.endswith(artifact):
                cleaned = cleaned[:-len(artifact)].strip()

        return cleaned


class StructuredExtractionStrategy(ExtractionStrategy):
    """
    Extract structured data as JSON blocks
    Inspired by Crawl4AI's JSON extraction approach
    """

    DEFAULT_SYSTEM_PROMPT = """You are a web content extraction expert. Extract all important and meaningful content blocks from the provided HTML as a JSON array.

Each block should have:
- "index": sequential number starting from 0
- "tags": array of relevant semantic tags (e.g., ["article", "product", "review", "heading", "paragraph", "list", "table"])
- "type": content type (e.g., "text", "heading", "list", "table", "code", "quote")
- "content": the actual text content
- "metadata": optional object with additional info (e.g., {"level": 1} for h1, {"href": "url"} for links)

Focus on:
- Main content areas (articles, posts, products, descriptions)
- Important metadata (dates, authors, prices, ratings)
- Structured data (lists, tables, code blocks)
- Preserve heading hierarchy and content relationships

Exclude:
- Navigation menus
- Advertisements
- Footers and sidebars (unless they contain important content)
- Boilerplate text
- Empty or meaningless blocks

Return ONLY a valid JSON array with no additional text or explanation."""

    def __init__(self, instruction: Optional[str] = None, schema: Optional[Dict[str, Any]] = None):
        super().__init__(self.DEFAULT_SYSTEM_PROMPT, instruction)
        self.schema = schema  # Optional: custom schema for structured extraction

    def build_prompt(self, html: str, title: str, chunk_index: int, total_chunks: int) -> Dict[str, str]:
        """Build structured extraction prompt"""

        user_parts = ["Extract content blocks from the following HTML as a JSON array."]

        # Add chunking context
        if total_chunks > 1:
            user_parts.append(f"\nNote: This is chunk {chunk_index + 1} of {total_chunks}. Start block indices from {chunk_index * 1000} to avoid conflicts.")

        # Add custom instruction if provided
        if self.instruction:
            user_parts.append(f"\nAdditional Instructions: {self.instruction}")

        # Add schema if provided
        if self.schema:
            user_parts.append(f"\nTarget Schema:\n{json.dumps(self.schema, indent=2)}")
            user_parts.append("\nExtract data matching the schema structure. If a field is not found, use null.")

        # Add title context
        if title:
            user_parts.append(f"\nPage Title: {title}")

        # Add HTML content
        user_parts.append(f"\nHTML:\n{html}")

        return {
            'system': self.system_prompt,
            'user': '\n'.join(user_parts)
        }

    def post_process(self, response: str, chunk_index: int) -> str:
        """Parse and validate JSON response"""
        # Remove markdown code blocks if present
        cleaned = response.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned[7:].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:].strip()

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        try:
            # Try to parse as JSON
            data = json.loads(cleaned)

            # Validate structure
            if not isinstance(data, list):
                logger.warning(f"[StructuredStrategy] Chunk {chunk_index}: Response is not an array, wrapping")
                data = [data]

            # Validate each block has required fields
            valid_blocks = []
            for i, block in enumerate(data):
                if isinstance(block, dict):
                    # Ensure required fields
                    if 'content' not in block:
                        logger.warning(f"[StructuredStrategy] Chunk {chunk_index}, block {i}: Missing 'content' field")
                        continue

                    # Add default fields if missing
                    if 'index' not in block:
                        block['index'] = i
                    if 'tags' not in block:
                        block['tags'] = []
                    if 'type' not in block:
                        block['type'] = 'text'

                    valid_blocks.append(block)

            # Re-serialize for consistency
            return json.dumps(valid_blocks, indent=2)

        except json.JSONDecodeError as e:
            logger.error(f"[StructuredStrategy] Chunk {chunk_index}: Invalid JSON: {e}")
            logger.error(f"[StructuredStrategy] Response preview: {cleaned[:200]}...")

            # Return error block
            error_block = [{
                "index": chunk_index,
                "error": True,
                "tags": ["error"],
                "type": "error",
                "content": f"JSON parsing failed: {str(e)}",
                "raw_response": cleaned[:500]
            }]
            return json.dumps(error_block, indent=2)


class CombinedExtractionStrategy(ExtractionStrategy):
    """
    Extract both markdown AND structured JSON
    Useful for getting readable output + structured data
    """

    def __init__(self, instruction: Optional[str] = None):
        system_prompt = """You are a dual-mode content extraction expert. Extract content from HTML in BOTH formats:

1. MARKDOWN: Clean, readable markdown for human consumption
2. JSON: Structured data blocks for machine processing

Return your response in this exact format:
---MARKDOWN---
[Your markdown content here]
---JSON---
[Your JSON array here]
---END---

Follow the same quality standards for both formats as described in previous instructions."""
        super().__init__(system_prompt, instruction)

    def build_prompt(self, html: str, title: str, chunk_index: int, total_chunks: int) -> Dict[str, str]:
        """Build combined extraction prompt"""

        user_parts = ["Extract the following HTML in BOTH markdown and JSON formats."]

        if total_chunks > 1:
            user_parts.append(f"\nNote: Chunk {chunk_index + 1} of {total_chunks}.")

        if self.instruction:
            user_parts.append(f"\nInstructions: {self.instruction}")

        if title and chunk_index == 0:
            user_parts.append(f"\nPage Title: {title}")

        user_parts.append(f"\nHTML:\n{html}")

        return {
            'system': self.system_prompt,
            'user': '\n'.join(user_parts)
        }

    def post_process(self, response: str, chunk_index: int) -> str:
        """Parse combined response and return as JSON with both formats"""
        try:
            # Split by markers
            parts = response.split('---MARKDOWN---')
            if len(parts) < 2:
                raise ValueError("Missing MARKDOWN section")

            remaining = parts[1].split('---JSON---')
            if len(remaining) < 2:
                raise ValueError("Missing JSON section")

            markdown = remaining[0].strip()
            json_part = remaining[1].split('---END---')[0].strip()

            # Parse JSON
            json_data = json.loads(json_part)

            # Return combined result as JSON
            result = {
                "markdown": markdown,
                "structured": json_data,
                "chunk_index": chunk_index
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"[CombinedStrategy] Chunk {chunk_index}: Parsing failed: {e}")
            return json.dumps({
                "error": True,
                "message": str(e),
                "raw_response": response[:500]
            }, indent=2)


def get_strategy(strategy_name: str, instruction: Optional[str] = None, schema: Optional[Dict[str, Any]] = None) -> ExtractionStrategy:
    """
    Factory function to get extraction strategy by name

    Args:
        strategy_name: 'markdown', 'structured', or 'combined'
        instruction: Optional custom instruction
        schema: Optional schema for structured extraction

    Returns:
        ExtractionStrategy instance
    """
    strategies = {
        'markdown': MarkdownExtractionStrategy,
        'structured': StructuredExtractionStrategy,
        'combined': CombinedExtractionStrategy
    }

    strategy_class = strategies.get(strategy_name.lower(), MarkdownExtractionStrategy)

    if strategy_name.lower() == 'structured' and schema:
        return strategy_class(instruction=instruction, schema=schema)
    else:
        return strategy_class(instruction=instruction)

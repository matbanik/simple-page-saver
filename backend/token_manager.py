"""
Token Management System
Centralized token counting and limit management
Inspired by Crawl4AI's token management approach
"""

import logging
from typing import Optional, Dict
import requests
from functools import lru_cache

logger = logging.getLogger('simple_page_saver.token_manager')


class TokenManager:
    """
    Manages token counting and context limits
    Provides precise token counting with tiktoken and dynamic model limit queries
    """

    # Hardcoded fallback limits
    MODEL_CONTEXT_LIMITS = {
        'openai/gpt-3.5-turbo': 16000,
        'openai/gpt-4-turbo': 128000,
        'openai/gpt-4o': 128000,
        'openai/gpt-4o-mini': 128000,
        'anthropic/claude-3-sonnet': 200000,
        'anthropic/claude-3-haiku': 200000,
        'anthropic/claude-3.5-sonnet': 200000,
        'anthropic/claude-3.5-haiku': 200000,
        'deepseek/deepseek-chat': 128000,
        'google/gemini-pro': 32000,
        'google/gemini-1.5-pro': 1000000,
        'google/gemini-2.0-flash': 1000000,
        'meta-llama/llama-3-70b': 8000,
        'meta-llama/llama-3.1-70b': 128000,
        'meta-llama/llama-3.1-405b': 128000,
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._model_cache = {}  # Cache for model limits

    def count_tokens(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """
        Precisely count tokens using tiktoken

        Args:
            text: Text to count
            model: Model name for tokenizer selection

        Returns:
            Token count
        """
        import tiktoken

        try:
            # Try to get encoding for specific model
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base (GPT-3.5/4 encoding)
            encoding = tiktoken.get_encoding("cl100k_base")

        tokens = encoding.encode(text)
        return len(tokens)

    def get_model_context_limit(self, model_id: str) -> int:
        """
        Get context limit for model

        Priority:
        1. Cache
        2. OpenRouter API query
        3. Hardcoded limits
        4. Default 128K

        Returns:
            Context limit in tokens
        """
        # Check cache first
        if model_id in self._model_cache:
            return self._model_cache[model_id]

        # Try querying OpenRouter API
        if self.api_key:
            try:
                limit = self._query_openrouter_api(model_id)
                if limit:
                    self._model_cache[model_id] = limit
                    logger.info(f"[TokenManager] OpenRouter API: '{model_id}' = {limit} tokens")
                    return limit
            except Exception as e:
                logger.warning(f"[TokenManager] OpenRouter API query failed: {e}")

        # Check hardcoded limits
        if model_id in self.MODEL_CONTEXT_LIMITS:
            limit = self.MODEL_CONTEXT_LIMITS[model_id]
            self._model_cache[model_id] = limit
            return limit

        # Fuzzy match
        for known_model, limit in self.MODEL_CONTEXT_LIMITS.items():
            if known_model in model_id or model_id in known_model:
                logger.info(f"[TokenManager] Fuzzy matched '{model_id}' → '{known_model}': {limit}")
                self._model_cache[model_id] = limit
                return limit

        # Default fallback
        default_limit = 128000
        logger.warning(f"[TokenManager] Unknown model '{model_id}', using default {default_limit}")
        self._model_cache[model_id] = default_limit
        return default_limit

    def _query_openrouter_api(self, model_id: str) -> Optional[int]:
        """Query OpenRouter API for model info"""
        try:
            url = "https://openrouter.ai/api/v1/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(url, headers=headers, timeout=5)

            if response.status_code == 200:
                models = response.json().get('data', [])
                for model in models:
                    if model.get('id') == model_id:
                        context_length = model.get('context_length')
                        if context_length:
                            return int(context_length)

            return None
        except Exception as e:
            logger.debug(f"[TokenManager] API query error: {e}")
            return None

    def calculate_token_budget(
        self,
        model_id: str,
        system_prompt: str,
        custom_prompt: str = "",
        title: str = "",
        output_tokens: int = 4000,
        safety_margin: float = 0.95
    ) -> Dict[str, int]:
        """
        Calculate token budget for request

        Args:
            model_id: Model identifier
            system_prompt: System prompt text
            custom_prompt: Optional custom prompt
            title: Optional page title
            output_tokens: Requested output tokens
            safety_margin: Safety factor (0.95 = 5% margin)

        Returns:
            Dict with budget breakdown
        """
        # Extract model name for tokenizer
        model_name = model_id.split('/')[-1] if '/' in model_id else model_id

        # Count overhead tokens
        system_tokens = self.count_tokens(system_prompt, model_name)
        custom_tokens = self.count_tokens(custom_prompt, model_name) if custom_prompt else 0
        title_tokens = self.count_tokens(f"\nPage Title: {title}", model_name) if title else 0

        overhead_tokens = system_tokens + custom_tokens + title_tokens

        # Get model limit
        max_context = self.get_model_context_limit(model_id)

        # Apply safety margin
        effective_context = int(max_context * safety_margin)

        # Calculate max input tokens
        max_input_tokens = effective_context - output_tokens - overhead_tokens

        return {
            'max_context': max_context,
            'effective_context': effective_context,
            'system_tokens': system_tokens,
            'custom_tokens': custom_tokens,
            'title_tokens': title_tokens,
            'overhead_tokens': overhead_tokens,
            'output_tokens': output_tokens,
            'max_input_tokens': max_input_tokens,
            'safety_margin': safety_margin
        }

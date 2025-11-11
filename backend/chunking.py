"""
Intelligent Chunking Engine
Inspired by Crawl4AI's merge_chunks() strategy
Multi-strategy approach with pre-allocation and overlap
"""

import math
import logging
from typing import List, Tuple, Dict, Any
from token_manager import TokenManager

logger = logging.getLogger('simple_page_saver.chunking')


class ChunkingStrategy:
    """Base class for chunking strategies"""

    def __init__(self, max_tokens: int, model_name: str, overlap_percentage: float = 0.1):
        self.max_tokens = max_tokens
        self.model_name = model_name
        self.overlap_percentage = overlap_percentage
        self.token_mgr = TokenManager()

    def chunk(self, text: str) -> List[str]:
        """Override in subclass"""
        raise NotImplementedError


class ParagraphChunkingStrategy(ChunkingStrategy):
    """Split by paragraph boundaries (\n\n)"""

    def chunk(self, text: str) -> List[str]:
        paragraphs = text.split('\n\n')

        if len(paragraphs) == 1:
            logger.info("[ParagraphChunking] No paragraph breaks found")
            return None  # Fallback to next strategy

        chunks = []
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self.token_mgr.count_tokens(para, self.model_name)

            if current_tokens + para_tokens > self.max_tokens and current_chunk:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(chunk_text)

                # Calculate overlap
                overlap_size = int(len(current_chunk) * self.overlap_percentage)
                if overlap_size > 0:
                    current_chunk = current_chunk[-overlap_size:]
                    current_tokens = sum(self.token_mgr.count_tokens(p, self.model_name) for p in current_chunk)
                else:
                    current_chunk = []
                    current_tokens = 0

            current_chunk.append(para)
            current_tokens += para_tokens

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        logger.info(f"[ParagraphChunking] Created {len(chunks)} chunks")
        return chunks if len(chunks) > 1 else None


class SentenceChunkingStrategy(ChunkingStrategy):
    """Split by sentence boundaries (. followed by space or newline)"""

    def chunk(self, text: str) -> List[str]:
        import re
        # Split by period followed by space or newline (simple sentence detection)
        sentences = re.split(r'\.\s+', text)

        if len(sentences) == 1:
            logger.info("[SentenceChunking] No sentence breaks found")
            return None  # Fallback to next strategy

        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.token_mgr.count_tokens(sentence, self.model_name)

            if current_tokens + sentence_tokens > self.max_tokens and current_chunk:
                chunk_text = '. '.join(current_chunk)
                chunks.append(chunk_text)

                # Add overlap
                overlap_size = int(len(current_chunk) * self.overlap_percentage)
                if overlap_size > 0:
                    current_chunk = current_chunk[-overlap_size:]
                    current_tokens = sum(self.token_mgr.count_tokens(s, self.model_name) for s in current_chunk)
                else:
                    current_chunk = []
                    current_tokens = 0

            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        if current_chunk:
            chunks.append('. '.join(current_chunk))

        logger.info(f"[SentenceChunking] Created {len(chunks)} chunks")
        return chunks if len(chunks) > 1 else None


class WordChunkingStrategy(ChunkingStrategy):
    """Word-based chunking (final fallback) - Crawl4AI's ultimate strategy"""

    def chunk(self, text: str) -> List[str]:
        words = text.split()
        total_words = len(words)

        logger.info(f"[WordChunking] Splitting {total_words} words")

        # Estimate words per token (conservative)
        WORDS_PER_TOKEN = 0.75
        target_words_per_chunk = int(self.max_tokens * WORDS_PER_TOKEN)

        # Calculate overlap in words
        overlap_words = int(target_words_per_chunk * self.overlap_percentage)

        chunks = []
        current_pos = 0

        while current_pos < total_words:
            # Calculate chunk boundaries
            chunk_end = min(current_pos + target_words_per_chunk, total_words)
            chunk_words = words[current_pos:chunk_end]
            chunk_text = ' '.join(chunk_words)

            chunks.append(chunk_text)

            # Move position forward (accounting for overlap)
            current_pos += (target_words_per_chunk - overlap_words)

            # Prevent infinite loop
            if current_pos >= total_words:
                break

        logger.info(f"[WordChunking] Created {len(chunks)} chunks")
        return chunks


class SmartChunker:
    """
    Intelligent chunking with multi-strategy fallback
    Inspired by Crawl4AI's robust approach
    """

    def __init__(self, max_tokens: int, model_name: str, overlap_percentage: float = 0.1):
        self.max_tokens = max_tokens
        self.model_name = model_name
        self.overlap_percentage = overlap_percentage
        self.token_mgr = TokenManager()

        # Initialize strategies in priority order
        self.strategies = [
            ParagraphChunkingStrategy(max_tokens, model_name, overlap_percentage),
            SentenceChunkingStrategy(max_tokens, model_name, overlap_percentage),
            WordChunkingStrategy(max_tokens, model_name, overlap_percentage)
        ]

    def chunk_with_preallocation(self, text: str) -> Tuple[List[str], Dict[str, Any]]:
        """
        Chunk text using Crawl4AI's pre-allocation strategy

        Returns:
            Tuple of (chunks, metadata)
        """
        # Step 1: Calculate total tokens and required chunks
        total_tokens = self.token_mgr.count_tokens(text, self.model_name)

        if total_tokens <= self.max_tokens:
            return [text], {
                'total_tokens': total_tokens,
                'chunk_count': 1,
                'strategy': 'no_chunking',
                'avg_tokens_per_chunk': total_tokens,
                'target_tokens_per_chunk': total_tokens,
                'actual_tokens_per_chunk': [total_tokens],
                'min_tokens': total_tokens,
                'max_tokens': total_tokens,
                'oversized_chunks': [],
                'overlap_percentage': self.overlap_percentage
            }

        # Step 2: Pre-calculate optimal chunk distribution
        chunk_count = math.ceil(total_tokens / self.max_tokens)
        target_tokens_per_chunk = math.ceil(total_tokens / chunk_count)

        logger.info(f"[Chunking] Pre-allocation: {total_tokens} tokens -> {chunk_count} chunks of ~{target_tokens_per_chunk} tokens")
        print(f"[Chunking] Pre-allocation: {total_tokens} tokens -> {chunk_count} chunks of ~{target_tokens_per_chunk} tokens")

        # Step 3: Try strategies in order until one succeeds
        chunks = None
        strategy_used = None

        for strategy in self.strategies:
            strategy_name = strategy.__class__.__name__
            logger.info(f"[Chunking] Trying {strategy_name}...")

            try:
                # Temporarily update max_tokens for this strategy
                strategy.max_tokens = target_tokens_per_chunk
                chunks = strategy.chunk(text)

                if chunks and len(chunks) > 1:
                    strategy_used = strategy_name
                    logger.info(f"[Chunking] {strategy_name} succeeded: {len(chunks)} chunks")
                    print(f"[Chunking] {strategy_name} succeeded: {len(chunks)} chunks")
                    break
                else:
                    logger.warning(f"[Chunking] {strategy_name} returned no chunks, trying next strategy")
            except Exception as e:
                logger.error(f"[Chunking] {strategy_name} failed: {e}")
                continue

        # Fallback: if all strategies fail, create single chunk (will trigger error later)
        if not chunks:
            logger.error("[Chunking] All strategies failed, returning single chunk")
            print("[Chunking] WARNING: All strategies failed, returning single chunk (may exceed limit)")
            chunks = [text]
            strategy_used = 'fallback_single'

        # Step 4: Verify chunk sizes and collect metadata
        chunk_sizes = []
        oversized_chunks = []

        for i, chunk in enumerate(chunks):
            chunk_tokens = self.token_mgr.count_tokens(chunk, self.model_name)
            chunk_sizes.append(chunk_tokens)

            if chunk_tokens > self.max_tokens:
                oversized_chunks.append((i+1, chunk_tokens))
                logger.error(f"[Chunking] Chunk {i+1} EXCEEDS limit: {chunk_tokens} > {self.max_tokens}")
                print(f"[Chunking] ERROR: Chunk {i+1} EXCEEDS limit: {chunk_tokens} > {self.max_tokens}")

        metadata = {
            'total_tokens': total_tokens,
            'chunk_count': len(chunks),
            'strategy': strategy_used,
            'target_tokens_per_chunk': target_tokens_per_chunk,
            'actual_tokens_per_chunk': chunk_sizes,
            'avg_tokens_per_chunk': sum(chunk_sizes) // len(chunk_sizes) if chunk_sizes else 0,
            'min_tokens': min(chunk_sizes) if chunk_sizes else 0,
            'max_tokens': max(chunk_sizes) if chunk_sizes else 0,
            'oversized_chunks': oversized_chunks,
            'overlap_percentage': self.overlap_percentage
        }

        return chunks, metadata

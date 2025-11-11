"""
Result Merging System
Combines chunk results with overlap deduplication
Supports both Markdown and JSON block merging
"""

import logging
import json
from typing import List, Union
from dataclasses import dataclass

logger = logging.getLogger('simple_page_saver.result_merger')


@dataclass
class MergeResult:
    """Result of merging multiple chunks"""
    combined_text: str
    original_length: int
    deduplicated_length: int
    overlap_removed: int
    chunk_count: int


class ResultMerger:
    """
    Merge chunk results with overlap deduplication
    Inspired by Crawl4AI's result combination
    """

    def __init__(self, overlap_percentage: float = 0.1):
        self.overlap_percentage = overlap_percentage

    def merge_markdown_chunks(self, chunks: List[str], separator: str = "\n\n---\n\n") -> MergeResult:
        """
        Merge markdown chunks with overlap deduplication

        Args:
            chunks: List of markdown strings
            separator: Separator between chunks

        Returns:
            MergeResult with combined text and metadata
        """
        if not chunks:
            return MergeResult("", 0, 0, 0, 0)

        if len(chunks) == 1:
            return MergeResult(
                chunks[0],
                len(chunks[0]),
                len(chunks[0]),
                0,
                1
            )

        logger.info(f"[Merger] Merging {len(chunks)} markdown chunks with {self.overlap_percentage*100}% overlap")

        original_length = sum(len(c) for c in chunks)
        merged_chunks = []
        total_overlap_removed = 0

        for i, chunk in enumerate(chunks):
            if i == 0:
                # First chunk - add as-is
                merged_chunks.append(chunk)
            else:
                # Subsequent chunks - try to detect and remove overlap
                prev_chunk = merged_chunks[-1]
                deduplicated, overlap_chars = self._remove_overlap(prev_chunk, chunk)

                if overlap_chars > 0:
                    logger.info(f"[Merger] Chunk {i+1}: Removed {overlap_chars} overlapping chars")
                    total_overlap_removed += overlap_chars

                merged_chunks.append(deduplicated)

        # Combine with separator
        combined = separator.join(merged_chunks)

        logger.info(f"[Merger] Original: {original_length} chars, Final: {len(combined)} chars, Removed: {total_overlap_removed} chars")
        print(f"[Merger] Merged {len(chunks)} chunks, removed {total_overlap_removed} overlap chars")

        return MergeResult(
            combined_text=combined,
            original_length=original_length,
            deduplicated_length=len(combined),
            overlap_removed=total_overlap_removed,
            chunk_count=len(chunks)
        )

    def merge_json_chunks(self, chunks: List[str]) -> MergeResult:
        """
        Merge JSON block chunks into a single JSON array
        Handles overlapping blocks by deduplicating based on content similarity

        Args:
            chunks: List of JSON strings (each should be an array)

        Returns:
            MergeResult with combined JSON and metadata
        """
        if not chunks:
            return MergeResult("[]", 0, 0, 0, 0)

        if len(chunks) == 1:
            return MergeResult(
                chunks[0],
                len(chunks[0]),
                len(chunks[0]),
                0,
                1
            )

        logger.info(f"[Merger] Merging {len(chunks)} JSON chunks")

        original_length = sum(len(c) for c in chunks)
        all_blocks = []
        total_duplicates = 0

        for i, chunk in enumerate(chunks):
            try:
                blocks = json.loads(chunk)

                if not isinstance(blocks, list):
                    logger.warning(f"[Merger] Chunk {i+1} is not an array, skipping")
                    continue

                # For first chunk, add all blocks
                if i == 0:
                    all_blocks.extend(blocks)
                else:
                    # For subsequent chunks, deduplicate based on content similarity
                    new_blocks, duplicates = self._deduplicate_json_blocks(all_blocks, blocks)
                    all_blocks.extend(new_blocks)
                    total_duplicates += duplicates

                    if duplicates > 0:
                        logger.info(f"[Merger] Chunk {i+1}: Removed {duplicates} duplicate blocks")

            except json.JSONDecodeError as e:
                logger.error(f"[Merger] Chunk {i+1}: Invalid JSON: {e}")
                # Add error block
                all_blocks.append({
                    "error": True,
                    "chunk_index": i,
                    "message": f"Invalid JSON: {str(e)}"
                })

        # Re-index all blocks sequentially
        for i, block in enumerate(all_blocks):
            if isinstance(block, dict) and 'index' in block:
                block['index'] = i

        # Serialize
        combined = json.dumps(all_blocks, indent=2)

        logger.info(f"[Merger] Combined {len(all_blocks)} blocks from {len(chunks)} chunks, removed {total_duplicates} duplicates")
        print(f"[Merger] Merged {len(chunks)} JSON chunks into {len(all_blocks)} blocks, removed {total_duplicates} duplicates")

        return MergeResult(
            combined_text=combined,
            original_length=original_length,
            deduplicated_length=len(combined),
            overlap_removed=total_duplicates,
            chunk_count=len(chunks)
        )

    def _remove_overlap(self, prev_chunk: str, current_chunk: str, min_overlap: int = 50) -> tuple:
        """
        Detect and remove overlapping content between markdown chunks

        Args:
            prev_chunk: Previous chunk
            current_chunk: Current chunk
            min_overlap: Minimum overlap length to consider

        Returns:
            Tuple of (deduplicated_current_chunk, overlap_chars_removed)
        """
        # Get the end of previous chunk (potential overlap region)
        overlap_window = int(len(prev_chunk) * self.overlap_percentage)
        if overlap_window < min_overlap:
            return current_chunk, 0

        prev_end = prev_chunk[-overlap_window:]

        # Try to find this substring at the start of current chunk
        # Use progressively smaller windows to find best match
        for size in range(len(prev_end), min_overlap, -10):
            search_str = prev_end[-size:]

            if current_chunk.startswith(search_str):
                # Found exact match - remove it
                deduplicated = current_chunk[size:]
                return deduplicated, size

        # No significant overlap found
        return current_chunk, 0

    def _deduplicate_json_blocks(self, existing_blocks: List[dict], new_blocks: List[dict]) -> tuple:
        """
        Deduplicate JSON blocks based on content similarity

        Args:
            existing_blocks: Already merged blocks
            new_blocks: New blocks to add

        Returns:
            Tuple of (unique_new_blocks, duplicate_count)
        """
        unique_blocks = []
        duplicate_count = 0

        # Create simple fingerprints of existing blocks (first 100 chars of content)
        existing_fingerprints = set()
        for block in existing_blocks:
            if isinstance(block, dict) and 'content' in block:
                content = str(block['content'])
                fingerprint = content[:100] if len(content) > 100 else content
                existing_fingerprints.add(fingerprint)

        # Check each new block
        for block in new_blocks:
            if isinstance(block, dict) and 'content' in block:
                content = str(block['content'])
                fingerprint = content[:100] if len(content) > 100 else content

                if fingerprint in existing_fingerprints:
                    # Duplicate detected
                    duplicate_count += 1
                else:
                    # New block
                    unique_blocks.append(block)
                    existing_fingerprints.add(fingerprint)
            else:
                # No content field, add it
                unique_blocks.append(block)

        return unique_blocks, duplicate_count

    def merge_combined_chunks(self, chunks: List[str]) -> dict:
        """
        Merge chunks from CombinedExtractionStrategy
        Each chunk contains both markdown and JSON

        Args:
            chunks: List of JSON strings with 'markdown' and 'structured' keys

        Returns:
            Dict with merged markdown and merged JSON
        """
        markdown_parts = []
        json_parts = []

        for i, chunk in enumerate(chunks):
            try:
                data = json.loads(chunk)

                if 'markdown' in data:
                    markdown_parts.append(data['markdown'])

                if 'structured' in data:
                    json_parts.append(json.dumps(data['structured']))

            except json.JSONDecodeError as e:
                logger.error(f"[Merger] Combined chunk {i+1}: Invalid JSON: {e}")

        # Merge both formats
        markdown_result = self.merge_markdown_chunks(markdown_parts)
        json_result = self.merge_json_chunks(json_parts)

        return {
            'markdown': markdown_result.combined_text,
            'structured': json_result.combined_text,
            'metadata': {
                'markdown_chunks': len(markdown_parts),
                'json_chunks': len(json_parts),
                'markdown_overlap_removed': markdown_result.overlap_removed,
                'json_duplicates_removed': json_result.overlap_removed
            }
        }

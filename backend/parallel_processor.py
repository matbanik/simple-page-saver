"""
Parallel Chunk Processing
Inspired by Crawl4AI's ThreadPoolExecutor approach
"""

import concurrent.futures
import logging
import time
from typing import List, Tuple, Callable, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger('simple_page_saver.parallel_processor')


@dataclass
class ChunkResult:
    """Result from processing a single chunk"""
    chunk_index: int
    success: bool
    output: Optional[str]
    error: Optional[str]
    tokens_processed: int
    processing_time: float
    used_ai: bool


class ParallelChunkProcessor:
    """
    Process multiple chunks in parallel using ThreadPoolExecutor
    Inspired by Crawl4AI's parallel processing architecture
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    def process_chunks(
        self,
        chunks: List[str],
        process_func: Callable[[int, str, Any], ChunkResult],
        process_args: Any = None
    ) -> Tuple[List[ChunkResult], dict]:
        """
        Process chunks in parallel

        Args:
            chunks: List of text chunks to process
            process_func: Function to process each chunk (must accept index, chunk, args)
            process_args: Additional arguments to pass to process_func

        Returns:
            Tuple of (results sorted by chunk_index, metadata)
        """
        logger.info(f"[Parallel] Processing {len(chunks)} chunks with {self.max_workers} workers")
        print(f"[Parallel] Processing {len(chunks)} chunks with {self.max_workers} workers")

        start_time = time.time()

        results = []

        # Create chunk data with indices
        chunk_data = [(i, chunk) for i, chunk in enumerate(chunks)]

        # Process in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(process_func, idx, chunk, process_args): idx
                for idx, chunk in chunk_data
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(futures):
                chunk_idx = futures[future]
                try:
                    result = future.result()
                    results.append(result)

                    status = "[OK]" if result.success else "[FAIL]"
                    logger.info(f"[Parallel] Chunk {chunk_idx+1}/{len(chunks)} {status} ({result.processing_time:.2f}s)")
                    print(f"[Parallel] Chunk {chunk_idx+1}/{len(chunks)} {status} ({result.processing_time:.2f}s)")

                except Exception as e:
                    logger.error(f"[Parallel] Chunk {chunk_idx+1} EXCEPTION: {e}")
                    results.append(ChunkResult(
                        chunk_index=chunk_idx,
                        success=False,
                        output=None,
                        error=str(e),
                        tokens_processed=0,
                        processing_time=0,
                        used_ai=False
                    ))

        # Sort results by chunk index to maintain order
        results.sort(key=lambda r: r.chunk_index)

        elapsed = time.time() - start_time

        # Calculate metadata
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_tokens = sum(r.tokens_processed for r in results)
        avg_time = sum(r.processing_time for r in results) / len(results) if results else 0

        metadata = {
            'total_chunks': len(chunks),
            'successful': successful,
            'failed': failed,
            'total_tokens_processed': total_tokens,
            'total_time': elapsed,
            'avg_time_per_chunk': avg_time,
            'workers_used': self.max_workers,
            'speedup_estimate': f"{avg_time * len(chunks) / elapsed:.1f}x" if elapsed > 0 else "N/A"
        }

        logger.info(f"[Parallel] Completed: {successful}/{len(chunks)} successful in {elapsed:.2f}s")
        logger.info(f"[Parallel] Estimated speedup: {metadata['speedup_estimate']}")
        print(f"[Parallel] Completed: {successful}/{len(chunks)} successful in {elapsed:.2f}s (speedup: {metadata['speedup_estimate']})")

        return results, metadata

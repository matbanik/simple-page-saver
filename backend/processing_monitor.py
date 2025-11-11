"""
Processing Monitor
Detailed diagnostics and metrics collection
"""

import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger('simple_page_saver.processing_monitor')


@dataclass
class ChunkMetrics:
    """Metrics for a single chunk"""
    chunk_index: int
    input_tokens: int
    output_tokens: int
    processing_time: float
    success: bool
    error: Optional[str]
    strategy_used: str


@dataclass
class ProcessingMetrics:
    """Overall processing metrics"""
    total_chunks: int
    successful_chunks: int
    failed_chunks: int
    total_input_tokens: int
    total_output_tokens: int
    total_time: float
    avg_time_per_chunk: float
    estimated_speedup: str
    chunking_strategy: str
    overlap_percentage: float
    model_used: str
    chunk_metrics: List[ChunkMetrics]


class ProcessingMonitor:
    """
    Monitor and collect metrics during processing
    """

    def __init__(self):
        self.start_time = None
        self.chunk_metrics = []
        self.chunking_metadata = {}

    def start_processing(self):
        """Mark start of processing"""
        self.start_time = time.time()
        logger.info("[Monitor] Processing started")

    def record_chunk_result(
        self,
        chunk_index: int,
        input_tokens: int,
        output_tokens: int,
        processing_time: float,
        success: bool,
        error: Optional[str],
        strategy_used: str
    ):
        """Record metrics for a processed chunk"""
        metrics = ChunkMetrics(
            chunk_index=chunk_index,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            processing_time=processing_time,
            success=success,
            error=error,
            strategy_used=strategy_used
        )
        self.chunk_metrics.append(metrics)

        status = "[OK]" if success else "[FAIL]"
        logger.info(
            f"[Monitor] Chunk {chunk_index+1} {status}: "
            f"{input_tokens} in, {output_tokens} out, {processing_time:.2f}s"
        )

    def set_chunking_metadata(self, metadata: Dict[str, Any]):
        """Store chunking metadata"""
        self.chunking_metadata = metadata

    def get_metrics(self, model_used: str) -> ProcessingMetrics:
        """Calculate final metrics"""
        if not self.start_time:
            raise ValueError("Processing not started")

        total_time = time.time() - self.start_time

        total_chunks = len(self.chunk_metrics)
        successful = sum(1 for m in self.chunk_metrics if m.success)
        failed = total_chunks - successful

        total_input = sum(m.input_tokens for m in self.chunk_metrics)
        total_output = sum(m.output_tokens for m in self.chunk_metrics)

        avg_time = sum(m.processing_time for m in self.chunk_metrics) / total_chunks if total_chunks > 0 else 0

        # Estimate sequential time (sum of all chunk times)
        sequential_time = sum(m.processing_time for m in self.chunk_metrics)
        speedup = f"{sequential_time / total_time:.1f}x" if total_time > 0 else "N/A"

        metrics = ProcessingMetrics(
            total_chunks=total_chunks,
            successful_chunks=successful,
            failed_chunks=failed,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_time=total_time,
            avg_time_per_chunk=avg_time,
            estimated_speedup=speedup,
            chunking_strategy=self.chunking_metadata.get('strategy', 'unknown'),
            overlap_percentage=self.chunking_metadata.get('overlap_percentage', 0.0),
            model_used=model_used,
            chunk_metrics=self.chunk_metrics
        )

        logger.info(f"[Monitor] Final Metrics: {successful}/{total_chunks} successful, {speedup} speedup, {total_time:.2f}s total")

        return metrics

    def print_summary(self, metrics: ProcessingMetrics):
        """Print human-readable summary"""
        print("\n" + "="*60)
        print("PROCESSING SUMMARY")
        print("="*60)
        print(f"Chunks: {metrics.successful_chunks}/{metrics.total_chunks} successful")
        print(f"Tokens: {metrics.total_input_tokens} input, {metrics.total_output_tokens} output")
        print(f"Time: {metrics.total_time:.2f}s total, {metrics.avg_time_per_chunk:.2f}s avg/chunk")
        print(f"Speedup: {metrics.estimated_speedup} (parallel processing)")
        print(f"Strategy: {metrics.chunking_strategy} (overlap: {metrics.overlap_percentage*100}%)")
        print(f"Model: {metrics.model_used}")

        if metrics.failed_chunks > 0:
            print(f"\nFailed Chunks:")
            for m in metrics.chunk_metrics:
                if not m.success:
                    print(f"  - Chunk {m.chunk_index+1}: {m.error}")

        print("="*60 + "\n")

        logger.info("[Monitor] Summary printed")

    def get_metrics_dict(self, metrics: ProcessingMetrics) -> dict:
        """Convert metrics to dict for JSON serialization"""
        return {
            'total_chunks': metrics.total_chunks,
            'successful_chunks': metrics.successful_chunks,
            'failed_chunks': metrics.failed_chunks,
            'total_input_tokens': metrics.total_input_tokens,
            'total_output_tokens': metrics.total_output_tokens,
            'total_time': round(metrics.total_time, 2),
            'avg_time_per_chunk': round(metrics.avg_time_per_chunk, 2),
            'estimated_speedup': metrics.estimated_speedup,
            'chunking_strategy': metrics.chunking_strategy,
            'overlap_percentage': metrics.overlap_percentage,
            'model_used': metrics.model_used,
            'chunk_details': [
                {
                    'chunk_index': m.chunk_index,
                    'input_tokens': m.input_tokens,
                    'output_tokens': m.output_tokens,
                    'processing_time': round(m.processing_time, 2),
                    'success': m.success,
                    'error': m.error
                }
                for m in metrics.chunk_metrics
            ]
        }

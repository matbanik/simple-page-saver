"""
Job Manager for tracking long-running operations
Stores job state in memory with optional persistence
"""

import uuid
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from threading import Lock
import json


class Job:
    """Represents a single job/operation"""

    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'

    TYPE_SINGLE_PAGE = 'single_page'
    TYPE_MULTI_PAGE = 'multi_page'
    TYPE_SITE_MAP = 'site_map'

    def __init__(self, job_type: str, params: dict):
        self.id = str(uuid.uuid4())
        self.type = job_type
        self.status = self.STATUS_PENDING
        self.params = params
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.progress = {
            'current': 0,
            'total': 0,
            'message': 'Initializing...'
        }
        self.result = None
        self.error = None

    def start(self):
        """Mark job as started"""
        self.status = self.STATUS_PROCESSING
        self.started_at = datetime.now().isoformat()

    def update_progress(self, current: int, total: int, message: str = ''):
        """Update job progress"""
        self.progress = {
            'current': current,
            'total': total,
            'message': message,
            'percent': round((current / total * 100) if total > 0 else 0, 1)
        }

    def complete(self, result: Any):
        """Mark job as completed"""
        self.status = self.STATUS_COMPLETED
        self.completed_at = datetime.now().isoformat()
        self.result = result

    def fail(self, error: str):
        """Mark job as failed"""
        self.status = self.STATUS_FAILED
        self.completed_at = datetime.now().isoformat()
        self.error = error

    def to_dict(self) -> dict:
        """Convert job to dictionary"""
        return {
            'id': self.id,
            'type': self.type,
            'status': self.status,
            'params': self.params,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'progress': self.progress,
            'result': self.result,
            'error': self.error
        }


class JobManager:
    """Manages all jobs in the system"""

    def __init__(self, max_jobs: int = 100, ttl_hours: int = 24):
        self.jobs: Dict[str, Job] = {}
        self.lock = Lock()
        self.max_jobs = max_jobs
        self.ttl_hours = ttl_hours

    def create_job(self, job_type: str, params: dict) -> Job:
        """Create a new job"""
        with self.lock:
            job = Job(job_type, params)
            self.jobs[job.id] = job

            # Clean up old jobs if we exceed max
            self._cleanup_old_jobs()

            return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        with self.lock:
            return self.jobs.get(job_id)

    def update_job_progress(self, job_id: str, current: int, total: int, message: str = ''):
        """Update job progress"""
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.update_progress(current, total, message)

    def complete_job(self, job_id: str, result: Any):
        """Mark job as completed"""
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.complete(result)

    def fail_job(self, job_id: str, error: str):
        """Mark job as failed"""
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.fail(error)

    def list_jobs(self, status: Optional[str] = None, limit: int = 50) -> List[dict]:
        """List all jobs, optionally filtered by status"""
        with self.lock:
            jobs = list(self.jobs.values())

            # Filter by status if specified
            if status:
                jobs = [j for j in jobs if j.status == status]

            # Sort by created_at (newest first)
            jobs.sort(key=lambda j: j.created_at, reverse=True)

            # Limit results
            jobs = jobs[:limit]

            return [job.to_dict() for job in jobs]

    def get_active_jobs(self) -> List[dict]:
        """Get all active (pending or processing) jobs"""
        return self.list_jobs(status=None)

    def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        with self.lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                return True
            return False

    def _cleanup_old_jobs(self):
        """Remove old completed/failed jobs to prevent memory bloat"""
        if len(self.jobs) <= self.max_jobs:
            return

        cutoff_time = datetime.now() - timedelta(hours=self.ttl_hours)

        # Find jobs to remove (old completed/failed jobs)
        to_remove = []
        for job_id, job in self.jobs.items():
            if job.status in [Job.STATUS_COMPLETED, Job.STATUS_FAILED]:
                if job.completed_at:
                    completed_time = datetime.fromisoformat(job.completed_at)
                    if completed_time < cutoff_time:
                        to_remove.append(job_id)

        # Remove old jobs
        for job_id in to_remove:
            del self.jobs[job_id]

        # If still over limit, remove oldest completed jobs
        if len(self.jobs) > self.max_jobs:
            completed_jobs = [
                (job_id, job) for job_id, job in self.jobs.items()
                if job.status in [Job.STATUS_COMPLETED, Job.STATUS_FAILED]
            ]
            completed_jobs.sort(key=lambda x: x[1].completed_at or '')

            # Remove oldest
            remove_count = len(self.jobs) - self.max_jobs
            for job_id, _ in completed_jobs[:remove_count]:
                del self.jobs[job_id]

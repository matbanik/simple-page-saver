"""
Diagnostic utilities for troubleshooting connection and processing issues
"""

import time
import threading
import traceback
import psutil
import os
from functools import wraps
from typing import Dict, Any, List
from datetime import datetime


class DiagnosticMonitor:
    """Monitors system state and request lifecycle"""

    def __init__(self):
        self.requests_in_progress = {}
        self.completed_requests = []
        self.active_locks = {}
        self.lock = threading.Lock()
        self.start_time = time.time()

    def log_request_start(self, endpoint: str, request_id: str, details: Dict[str, Any] = None):
        """Log when a request starts processing"""
        with self.lock:
            self.requests_in_progress[request_id] = {
                'endpoint': endpoint,
                'start_time': time.time(),
                'thread_id': threading.current_thread().ident,
                'thread_name': threading.current_thread().name,
                'details': details or {}
            }

        print(f"\n{'='*80}")
        print(f"[DIAGNOSTIC] REQUEST START")
        print(f"  Request ID: {request_id}")
        print(f"  Endpoint: {endpoint}")
        print(f"  Thread: {threading.current_thread().name} (ID: {threading.current_thread().ident})")
        print(f"  Active Threads: {threading.active_count()}")
        print(f"  In-Progress Requests: {len(self.requests_in_progress)}")
        self._log_system_resources()
        print(f"{'='*80}\n")

    def log_request_end(self, request_id: str, status: str = "success", error: str = None):
        """Log when a request completes"""
        with self.lock:
            if request_id in self.requests_in_progress:
                req_info = self.requests_in_progress.pop(request_id)
                duration = time.time() - req_info['start_time']

                req_info.update({
                    'end_time': time.time(),
                    'duration': duration,
                    'status': status,
                    'error': error
                })

                self.completed_requests.append(req_info)
                if len(self.completed_requests) > 100:
                    self.completed_requests.pop(0)

                print(f"\n{'='*80}")
                print(f"[DIAGNOSTIC] REQUEST END")
                print(f"  Request ID: {request_id}")
                print(f"  Endpoint: {req_info['endpoint']}")
                print(f"  Duration: {duration:.2f}s")
                print(f"  Status: {status}")
                if error:
                    print(f"  Error: {error}")
                print(f"  Thread: {threading.current_thread().name} (ID: {threading.current_thread().ident})")
                print(f"  Active Threads: {threading.active_count()}")
                print(f"  In-Progress Requests: {len(self.requests_in_progress)}")
                self._log_system_resources()
                print(f"{'='*80}\n")
            else:
                print(f"[DIAGNOSTIC WARNING] Request {request_id} ended but was not in progress tracking")

    def log_lock_acquire(self, lock_name: str, requester: str):
        """Log when a lock is being acquired"""
        thread_id = threading.current_thread().ident
        timestamp = time.time()

        print(f"[DIAGNOSTIC LOCK] Acquiring '{lock_name}' - Requester: {requester} - Thread: {thread_id}")

        with self.lock:
            if lock_name not in self.active_locks:
                self.active_locks[lock_name] = []
            self.active_locks[lock_name].append({
                'requester': requester,
                'thread_id': thread_id,
                'acquire_time': timestamp,
                'status': 'acquiring'
            })

    def log_lock_acquired(self, lock_name: str, requester: str):
        """Log when a lock has been acquired"""
        thread_id = threading.current_thread().ident
        print(f"[DIAGNOSTIC LOCK] [ACQUIRED] '{lock_name}' - Requester: {requester} - Thread: {thread_id}")

        with self.lock:
            if lock_name in self.active_locks:
                for entry in self.active_locks[lock_name]:
                    if entry['thread_id'] == thread_id and entry['status'] == 'acquiring':
                        entry['status'] = 'acquired'
                        entry['acquired_time'] = time.time()
                        break

    def log_lock_release(self, lock_name: str, requester: str):
        """Log when a lock is released"""
        thread_id = threading.current_thread().ident
        print(f"[DIAGNOSTIC LOCK] [RELEASED] '{lock_name}' - Requester: {requester} - Thread: {thread_id}")

        with self.lock:
            if lock_name in self.active_locks:
                self.active_locks[lock_name] = [
                    entry for entry in self.active_locks[lock_name]
                    if entry['thread_id'] != thread_id
                ]

    def log_exception(self, context: str, exception: Exception):
        """Log exception with full context"""
        print(f"\n{'!'*80}")
        print(f"[DIAGNOSTIC EXCEPTION] Context: {context}")
        print(f"  Exception Type: {type(exception).__name__}")
        print(f"  Exception Message: {str(exception)}")
        print(f"  Thread: {threading.current_thread().name} (ID: {threading.current_thread().ident})")
        print(f"  Stack Trace:")
        print(traceback.format_exc())
        print(f"{'!'*80}\n")

    def _log_system_resources(self):
        """Log current system resource usage"""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()

        print(f"  System Resources:")
        print(f"    Memory RSS: {memory_info.rss / 1024 / 1024:.1f} MB")
        print(f"    Memory VMS: {memory_info.vms / 1024 / 1024:.1f} MB")
        print(f"    Open Files: {len(process.open_files())}")
        print(f"    Connections: {len(process.connections())}")
        print(f"    CPU Percent: {process.cpu_percent():.1f}%")

    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report"""
        with self.lock:
            return {
                'uptime_seconds': time.time() - self.start_time,
                'active_threads': threading.active_count(),
                'thread_names': [t.name for t in threading.enumerate()],
                'requests_in_progress': len(self.requests_in_progress),
                'in_progress_details': list(self.requests_in_progress.values()),
                'completed_requests_count': len(self.completed_requests),
                'recent_requests': self.completed_requests[-10:] if self.completed_requests else [],
                'active_locks': {
                    name: len(entries) for name, entries in self.active_locks.items()
                },
                'lock_details': self.active_locks
            }

    def print_status_report(self):
        """Print formatted status report"""
        report = self.get_status_report()

        print(f"\n{'#'*80}")
        print(f"[DIAGNOSTIC] STATUS REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*80}")
        print(f"Uptime: {report['uptime_seconds']:.1f}s")
        print(f"Active Threads: {report['active_threads']}")
        print(f"  Thread Names: {', '.join(report['thread_names'])}")
        print(f"Requests In Progress: {report['requests_in_progress']}")

        if report['in_progress_details']:
            print(f"\nIn-Progress Request Details:")
            for req in report['in_progress_details']:
                elapsed = time.time() - req['start_time']
                print(f"  - {req['endpoint']} (ID: {req.get('details', {}).get('request_id', 'N/A')})")
                print(f"    Thread: {req['thread_name']}, Elapsed: {elapsed:.1f}s")

        print(f"\nCompleted Requests: {report['completed_requests_count']}")

        if report['recent_requests']:
            print(f"\nRecent Completed Requests (last 5):")
            for req in report['recent_requests'][-5:]:
                print(f"  - {req['endpoint']}: {req['status']} ({req['duration']:.2f}s)")
                if req.get('error'):
                    print(f"    Error: {req['error']}")

        print(f"\nActive Locks: {sum(report['active_locks'].values())}")
        for lock_name, count in report['active_locks'].items():
            print(f"  - {lock_name}: {count} holders")
            if lock_name in report['lock_details']:
                for entry in report['lock_details'][lock_name]:
                    elapsed = time.time() - entry.get('acquired_time', entry['acquire_time'])
                    print(f"    Thread {entry['thread_id']}: {entry['status']} ({elapsed:.1f}s)")

        self._log_system_resources()
        print(f"{'#'*80}\n")


def track_request(endpoint: str):
    """Decorator to track request lifecycle"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            import uuid
            request_id = str(uuid.uuid4())[:8]

            # Get monitor from app state if available
            monitor = getattr(track_request, 'monitor', None)
            if not monitor:
                return await func(*args, **kwargs)

            try:
                monitor.log_request_start(endpoint, request_id, {'args_count': len(args)})
                result = await func(*args, **kwargs)
                monitor.log_request_end(request_id, status="success")
                return result
            except Exception as e:
                monitor.log_exception(f"Request {endpoint}", e)
                monitor.log_request_end(request_id, status="error", error=str(e))
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import uuid
            request_id = str(uuid.uuid4())[:8]

            monitor = getattr(track_request, 'monitor', None)
            if not monitor:
                return func(*args, **kwargs)

            try:
                monitor.log_request_start(endpoint, request_id, {'args_count': len(args)})
                result = func(*args, **kwargs)
                monitor.log_request_end(request_id, status="success")
                return result
            except Exception as e:
                monitor.log_exception(f"Request {endpoint}", e)
                monitor.log_request_end(request_id, status="error", error=str(e))
                raise

        # Return appropriate wrapper based on whether function is async
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Global monitor instance
diagnostic_monitor = DiagnosticMonitor()
track_request.monitor = diagnostic_monitor

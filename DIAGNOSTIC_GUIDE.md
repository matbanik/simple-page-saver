# Diagnostic Mode Guide

## Overview

The diagnostic system provides comprehensive monitoring of:
- Request lifecycle tracking (start/end times, duration)
- Thread activity and concurrency
- Lock acquisition/release for JobManager
- System resource usage (memory, CPU, connections)
- Exception tracking with full context

Use this to debug connection timeout issues, lock deadlocks, resource leaks, and other runtime problems.

## Enabling Diagnostic Mode

### Method 1: GUI Checkbox (Recommended - Easiest!)

1. **Launch GUI**:
   ```bash
   cd backend
   python launcher.py -gui
   # Or double-click: start_gui.bat (Windows)
   ```

2. **Enable Diagnostic Mode**:
   - Check the "Enable Diagnostic Mode" checkbox in Settings
   - Click "Save Settings"
   - Click "Start Server" (or restart if already running)

3. **View Diagnostic Report**:
   - Click "View Diagnostic Report" button in Testing section
   - Shows real-time status: threads, locks, requests in progress
   - Warns if issues detected (hung requests, held locks)

**Benefits**:
- ✓ No need to set environment variables
- ✓ Persists across restarts (saved in settings.json)
- ✓ Visual indicator when enabled
- ✓ Built-in report viewer in GUI

### Method 2: Environment Variable (Advanced)

**Linux/Mac:**
```bash
export ENABLE_DIAGNOSTICS=true
cd backend
python launcher.py
```

**Windows PowerShell:**
```powershell
$env:ENABLE_DIAGNOSTICS = "true"
cd backend
python launcher.py
```

**Windows CMD:**
```cmd
set ENABLE_DIAGNOSTICS=true
cd backend
python launcher.py
```

### Method 3: Inline with Command

**Linux/Mac:**
```bash
ENABLE_DIAGNOSTICS=true python backend/launcher.py
```

**Windows PowerShell:**
```powershell
$env:ENABLE_DIAGNOSTICS="true"; python backend/launcher.py
```

## What Gets Logged

When diagnostic mode is enabled, you'll see extensive logging:

### 1. Request Start
```
================================================================================
[DIAGNOSTIC] REQUEST START
  Request ID: a3b4c5d6
  Endpoint: POST /process-html
  Thread: ThreadPoolExecutor-0_1 (ID: 12345)
  Active Threads: 4
  In-Progress Requests: 1
  System Resources:
    Memory RSS: 145.2 MB
    Memory VMS: 2048.5 MB
    Open Files: 23
    Connections: 2
    CPU Percent: 5.2%
================================================================================
```

### 2. Lock Operations
```
[DIAGNOSTIC LOCK] Acquiring 'JobManager.lock' - Requester: create_job(single_page) - Thread: 12345
[DIAGNOSTIC LOCK] ✓ Acquired 'JobManager.lock' - Requester: create_job(single_page) - Thread: 12345
[DIAGNOSTIC LOCK] ✗ Released 'JobManager.lock' - Requester: create_job(single_page) - Thread: 12345
```

### 3. Request End
```
================================================================================
[DIAGNOSTIC] REQUEST END
  Request ID: a3b4c5d6
  Endpoint: POST /process-html
  Duration: 2.45s
  Status: success
  Thread: ThreadPoolExecutor-0_1 (ID: 12345)
  Active Threads: 3
  In-Progress Requests: 0
  System Resources:
    Memory RSS: 147.3 MB
    ...
================================================================================
```

### 4. Exceptions
```
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
[DIAGNOSTIC EXCEPTION] Context: POST /process-html (a3b4c5d6)
  Exception Type: ValueError
  Exception Message: Invalid HTML format
  Thread: ThreadPoolExecutor-0_1 (ID: 12345)
  Stack Trace:
  ...
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

## Diagnostic API Endpoint

### GET /diagnostics

Retrieve real-time diagnostic status report.

**Request:**
```bash
curl http://localhost:8077/diagnostics
```

**Response:**
```json
{
  "uptime_seconds": 123.45,
  "active_threads": 4,
  "thread_names": ["MainThread", "ThreadPoolExecutor-0_1", "ThreadPoolExecutor-0_2"],
  "requests_in_progress": 0,
  "in_progress_details": [],
  "completed_requests_count": 5,
  "recent_requests": [
    {
      "endpoint": "POST /process-html",
      "start_time": 1699123456.78,
      "end_time": 1699123458.90,
      "duration": 2.12,
      "status": "success",
      "thread_id": 12345,
      "thread_name": "ThreadPoolExecutor-0_1"
    }
  ],
  "active_locks": {
    "JobManager.lock": 0
  },
  "lock_details": {}
}
```

**Key Fields to Monitor:**

- `requests_in_progress`: Should be 0 when idle. If > 0 after request completes, indicates hanging request
- `in_progress_details`: Shows which requests are stuck and for how long
- `active_locks`: Should be 0 when idle. If > 0, indicates lock not released
- `lock_details`: Shows which thread holds each lock and for how long

## Test Script

Use the included test script to reproduce the timeout issue:

```bash
# Start server with diagnostics
export ENABLE_DIAGNOSTICS=true
python backend/launcher.py

# In another terminal, run test
python backend/test_diagnostic.py
```

The test script will:
1. Perform initial health check
2. Process a test HTML page
3. Attempt health check after processing (where timeout may occur)
4. Retrieve and display diagnostic report

## Troubleshooting Common Issues

### Issue 1: Requests Stuck "In Progress"

**Symptoms:**
- `/diagnostics` shows `requests_in_progress > 0` even after request completed
- Subsequent requests timeout

**Diagnostic Steps:**
1. Check `/diagnostics` for `in_progress_details`
2. Look for thread ID and elapsed time
3. Check if exception occurred but wasn't properly logged
4. Review if `log_request_end()` was called in all code paths (including exceptions)

**Potential Causes:**
- Exception in finally block preventing cleanup
- Missing try/finally in request handler
- Thread killed before cleanup

### Issue 2: Locks Not Released

**Symptoms:**
- `/diagnostics` shows `active_locks > 0`
- Subsequent requests hang waiting for lock
- JobManager operations timeout

**Diagnostic Steps:**
1. Check `/diagnostics` for `lock_details`
2. Identify which operation acquired lock (see `requester` field)
3. Calculate how long lock has been held (`elapsed` time)
4. Check if exception occurred in locked section

**Potential Causes:**
- Exception in locked section without try/finally
- Thread died while holding lock
- Deadlock between multiple locks
- Forgot to call `_release_lock()`

### Issue 3: Thread Pool Exhaustion

**Symptoms:**
- `active_threads` keeps growing
- Server becomes unresponsive
- High memory usage

**Diagnostic Steps:**
1. Monitor `thread_names` in `/diagnostics`
2. Check if thread count matches uvicorn worker configuration
3. Look for threads with same prefix but growing count
4. Check `Open Files` and `Connections` metrics

**Potential Causes:**
- Blocking I/O in async context
- Missing await on async operations
- Requests library used instead of httpx in async code
- Resource leaks (files, sockets not closed)

### Issue 4: 5-Second Timeout from GUI

**Symptoms:**
- First extension request succeeds
- GUI health check immediately after times out
- Error: `Read timed out. (read timeout=5)`

**Diagnostic Steps:**
1. Run test script to reproduce
2. Check `/diagnostics` immediately after first request
3. Look for `requests_in_progress` - should be 0
4. Check `active_threads` - should return to baseline
5. Look for held locks in `active_locks`

**Root Causes to Check:**
1. Backend still processing (check `in_progress_details`)
2. Lock held (check `lock_details`)
3. Thread blocked (check thread count growth)
4. Uvicorn single-threaded (check worker count)
5. Sync blocking in async context (check stack traces)

## Performance Impact

**Warning:** Diagnostic mode has performance overhead:

- **Logging**: Extensive console output slows request processing
- **Lock tracking**: Additional operations on every lock acquire/release
- **Resource monitoring**: psutil calls add ~50ms per request
- **Thread safety**: DiagnosticMonitor uses its own lock

**Recommendations:**
- **Development**: Always use diagnostic mode for troubleshooting
- **Testing**: Enable to understand baseline performance
- **Production**: **NEVER** enable in production
- **Benchmarking**: Disable for accurate performance measurements

## Integration with Existing Logs

Diagnostic logs complement existing application logs:

**Backend Logs (`logs/simple_page_saver_*.log`):**
- Business logic (preprocessing, AI conversion)
- Request/response details
- Errors and warnings

**Diagnostic Logs (console output):**
- Request lifecycle
- Lock operations
- Thread activity
- System resources

Both use request IDs (e.g., `[a3b4c5d6]`) for correlation.

## Disabling Diagnostic Mode

Remove or set environment variable:

```bash
# Linux/Mac
unset ENABLE_DIAGNOSTICS

# Windows PowerShell
Remove-Item Env:ENABLE_DIAGNOSTICS

# Windows CMD
set ENABLE_DIAGNOSTICS=
```

Or restart server without the environment variable.

## Architecture

### Components:

1. **diagnostics.py** - DiagnosticMonitor class and decorators
2. **main.py** - Request tracking in endpoints
3. **job_manager.py** - Lock monitoring in all operations

### Data Flow:

```
Request Arrives
    ↓
[main.py] log_request_start()
    ↓
[job_manager.py] _acquire_lock() → log_lock_acquire/acquired
    ↓
Process Request
    ↓
[job_manager.py] _release_lock() → log_lock_release
    ↓
[main.py] log_request_end()
    ↓
Response Sent
```

### Thread Safety:

DiagnosticMonitor uses its own lock (`self.lock`) to protect shared state:
- `requests_in_progress`
- `completed_requests`
- `active_locks`

This is separate from JobManager.lock and won't cause deadlocks.

## Example Diagnostic Session

```bash
# Terminal 1: Start server with diagnostics
$ export ENABLE_DIAGNOSTICS=true
$ cd backend
$ python launcher.py

=== Simple Page Saver Backend Starting ===
================================================================================
DIAGNOSTIC MODE ENABLED
Detailed request lifecycle and lock monitoring is active
Performance may be impacted - disable for production
================================================================================
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8077

# Terminal 2: Run diagnostic test
$ cd backend
$ python test_diagnostic.py

================================================================================
  TEST 1: Initial Health Check
================================================================================

✓ Status: 200
✓ Response: {'status': 'healthy', ...}

================================================================================
  TEST 2: Process HTML (No AI)
================================================================================

Sending request (AI: False)...
✓ Status: 200
✓ Duration: 2.34s
✓ Job ID: abc123...
✓ Success: True

================================================================================
  TEST 3: Health Check After Processing (Issue Reproduction)
================================================================================

Waiting 2 seconds before health check...
Attempting health check with 5-second timeout...
✓ Status: 200
✓ Duration: 0.12s
✓ Response: {'status': 'healthy', ...}

# Or if bug occurs:
# ✗ TIMEOUT after 5.00s - THIS IS THE BUG!

================================================================================
  TEST 4: Diagnostics Status Report
================================================================================

✓ Diagnostic report retrieved successfully

Uptime: 45.3s
Active Threads: 3
Thread Names: MainThread, ThreadPoolExecutor-0_1, ThreadPoolExecutor-0_2
Requests In Progress: 0

Completed Requests: 2

Recent Requests:
  - POST /process-html: success (2.34s)
  - GET /: success (0.12s)

Active Locks: 0
```

## Interpreting Results

### Healthy State
- `requests_in_progress`: 0 when idle
- `active_threads`: Stable, doesn't grow indefinitely
- `active_locks`: 0 when idle
- `in_progress_details`: Empty array
- Request durations consistent

### Unhealthy State (Bug Present)
- `requests_in_progress`: > 0 even after request returns
- `in_progress_details`: Shows "stuck" request with high elapsed time
- `active_locks`: > 0, lock held indefinitely
- `lock_details`: Shows which thread and operation holds lock
- Subsequent requests timeout or hang

## Next Steps After Diagnosis

Once you've identified the issue using diagnostics:

1. **Lock Deadlock**: Check try/finally blocks in job_manager.py
2. **Request Hanging**: Check if exception prevents `log_request_end()`
3. **Thread Exhaustion**: Check for blocking I/O in async context
4. **Resource Leak**: Check open files/connections metrics

5. **Apply Fix**: Modify code based on findings
6. **Verify Fix**: Re-run test_diagnostic.py
7. **Disable Diagnostics**: Remove environment variable for normal operation

## Support

If diagnostics reveal an issue you can't resolve:

1. Save diagnostic report: `curl http://localhost:8077/diagnostics > diagnostic_report.json`
2. Save server logs: `backend/logs/simple_page_saver_*.log`
3. Include test script output
4. Document exact steps to reproduce
5. Note server configuration (workers, port, OS, Python version)

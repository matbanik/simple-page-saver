"""
Diagnostic Test Script for Connection Timeout Issue

This script simulates the issue where:
1. First request works fine
2. Second request (like GUI health check) times out after first request completes

Usage:
  1. Launch GUI: python launcher.py -gui
  2. Enable 'Diagnostic Mode' checkbox in Settings
  3. Click 'Save Settings' then 'Start Server'
  4. Run this script to simulate the problem
"""

import requests
import time
import json

API_URL = "http://localhost:8077"

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def test_health_check():
    """Test basic health check"""
    print_section("TEST 1: Initial Health Check")
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        print(f"[OK] Status: {response.status_code}")
        print(f"[OK] Response: {response.json()}")
        return True
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

def test_process_html(test_name, use_ai=False):
    """Test HTML processing endpoint"""
    print_section(f"TEST 2: {test_name}")

    test_html = """
    <html>
    <head><title>Test Page</title></head>
    <body>
        <h1>Test Content</h1>
        <p>This is a test paragraph with some content to process.</p>
        <p>This simulates a real page extraction scenario.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
    </body>
    </html>
    """

    payload = {
        'url': 'https://test.example.com',
        'html': test_html,
        'title': 'Test Page',
        'use_ai': use_ai,
        'extraction_mode': 'balanced'
    }

    print(f"Sending request (AI: {use_ai})...")
    start_time = time.time()

    try:
        response = requests.post(
            f"{API_URL}/process-html",
            json=payload,
            timeout=120
        )
        duration = time.time() - start_time

        print(f"[OK] Status: {response.status_code}")
        print(f"[OK] Duration: {duration:.2f}s")

        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Job ID: {data.get('job_id')}")
            print(f"[OK] Word Count: {data.get('word_count')}")
            print(f"[OK] Used AI: {data.get('used_ai')}")
            print(f"[OK] Success: {data.get('success')}")
            return True, duration
        else:
            print(f"[ERROR] Error Response: {response.text}")
            return False, duration

    except Exception as e:
        duration = time.time() - start_time
        print(f"[ERROR] Error after {duration:.2f}s: {e}")
        return False, duration

def test_health_check_after_processing():
    """Test health check after processing (this is where timeout occurs)"""
    print_section("TEST 3: Health Check After Processing (Issue Reproduction)")

    print("Waiting 2 seconds before health check...")
    time.sleep(2)

    print("Attempting health check with 5-second timeout...")
    start_time = time.time()

    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        duration = time.time() - start_time
        print(f"[OK] Status: {response.status_code}")
        print(f"[OK] Duration: {duration:.2f}s")
        print(f"[OK] Response: {response.json()}")
        return True
    except requests.exceptions.Timeout:
        duration = time.time() - start_time
        print(f"[ERROR] TIMEOUT after {duration:.2f}s - THIS IS THE BUG!")
        print(f"[ERROR] Backend did not respond within 5 seconds")
        return False
    except Exception as e:
        duration = time.time() - start_time
        print(f"[ERROR] Error after {duration:.2f}s: {e}")
        return False

def test_diagnostics_endpoint():
    """Get diagnostic status report"""
    print_section("TEST 4: Diagnostics Status Report")

    try:
        response = requests.get(f"{API_URL}/diagnostics", timeout=10)
        if response.status_code == 200:
            print("[OK] Diagnostic report retrieved successfully")
            data = response.json()

            print(f"\nUptime: {data.get('uptime_seconds', 0):.1f}s")
            print(f"Active Threads: {data.get('active_threads', 0)}")
            print(f"Thread Names: {', '.join(data.get('thread_names', []))}")
            print(f"Requests In Progress: {data.get('requests_in_progress', 0)}")

            in_progress = data.get('in_progress_details', [])
            if in_progress:
                print(f"\nWARNING: {len(in_progress)} requests still in progress!")
                for req in in_progress:
                    elapsed = time.time() - req.get('start_time', 0)
                    print(f"  - {req.get('endpoint')}: {elapsed:.1f}s elapsed")

            completed = data.get('completed_requests_count', 0)
            print(f"\nCompleted Requests: {completed}")

            recent = data.get('recent_requests', [])
            if recent:
                print(f"\nRecent Requests:")
                for req in recent[-5:]:
                    print(f"  - {req.get('endpoint')}: {req.get('status')} ({req.get('duration', 0):.2f}s)")

            locks = data.get('active_locks', {})
            print(f"\nActive Locks: {sum(locks.values())}")
            for lock_name, count in locks.items():
                print(f"  - {lock_name}: {count} holders")

            lock_details = data.get('lock_details', {})
            if lock_details:
                print(f"\nWARNING: Locks are still held!")
                for lock_name, entries in lock_details.items():
                    print(f"  Lock: {lock_name}")
                    for entry in entries:
                        elapsed = time.time() - entry.get('acquired_time', entry.get('acquire_time', 0))
                        print(f"    Thread {entry.get('thread_id')}: {entry.get('status')} ({elapsed:.1f}s)")

            return True
        elif response.status_code == 404:
            print("[ERROR] Diagnostics not enabled")
            print("[ERROR] Enable diagnostic mode in GUI:")
            print("[ERROR]   1. Launch GUI: python launcher.py -gui")
            print("[ERROR]   2. Check 'Enable Diagnostic Mode' checkbox")
            print("[ERROR]   3. Save Settings and restart server")
            return False
        else:
            print(f"[ERROR] Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

def main():
    """Run diagnostic test sequence"""
    print_section("Simple Page Saver - Diagnostic Test Suite")
    print("This script will:")
    print("1. Test initial health check")
    print("2. Process a test HTML page")
    print("3. Attempt health check after processing (where timeout occurs)")
    print("4. Retrieve diagnostic report")
    print("\nMake sure server is running with diagnostic mode enabled:")
    print("  1. Launch GUI: python launcher.py -gui")
    print("  2. Enable 'Diagnostic Mode' checkbox in Settings")
    print("  3. Click 'Save Settings' then 'Start Server'")
    input("\nPress Enter to start tests...")

    results = {}

    # Test 1: Initial health check
    results['initial_health'] = test_health_check()

    if not results['initial_health']:
        print("\n[ERROR] Server is not responding. Make sure it's running on port 8077")
        return

    # Test 2: Process HTML
    results['process_html'], duration = test_process_html("Process HTML (No AI)", use_ai=False)

    # Test 3: Health check after processing (THIS IS WHERE ISSUE OCCURS)
    results['health_after_processing'] = test_health_check_after_processing()

    # Test 4: Get diagnostics
    results['diagnostics'] = test_diagnostics_endpoint()

    # Summary
    print_section("TEST SUMMARY")
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")

    if not results.get('health_after_processing'):
        print("\n" + "!"*80)
        print("  BUG REPRODUCED!")
        print("  Health check timed out after processing request")
        print("  Check server logs and diagnostic report for details")
        print("!"*80)

if __name__ == "__main__":
    main()

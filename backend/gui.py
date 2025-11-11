"""
Tkinter GUI for Simple Page Saver Backend
Manages server settings, start/stop controls, and testing
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import psutil
import threading
import requests
import sys
from pathlib import Path

from settings_manager import SettingsManager


class ServerGUI:
    """GUI for managing the Simple Page Saver backend server"""

    def __init__(self, root):
        self.root = root
        self.root.title("Simple Page Saver - Backend Manager")
        self.root.geometry("700x800")

        self.settings_manager = SettingsManager()
        self.server_process = None
        self.server_running = False

        self.create_widgets()
        self.load_settings()
        self.check_server_status()

    def create_widgets(self):
        """Create all GUI widgets"""

        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        row = 0

        # Title
        title_label = ttk.Label(main_frame, text="Simple Page Saver Backend",
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=row, column=0, columnspan=2, pady=(0, 20))
        row += 1

        # Settings Section
        settings_label = ttk.Label(main_frame, text="Settings",
                                   font=('Arial', 12, 'bold'))
        settings_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        row += 1

        # Server Port
        ttk.Label(main_frame, text="Server Port:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.port_var = tk.StringVar()
        self.port_entry = ttk.Entry(main_frame, textvariable=self.port_var, width=30)
        self.port_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # AI Model
        ttk.Label(main_frame, text="AI Model:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(main_frame, textvariable=self.model_var, width=28)
        self.model_combo['values'] = (
            'deepseek/deepseek-chat',
            'openai/gpt-3.5-turbo',
            'openai/gpt-4-turbo',
            'anthropic/claude-3-haiku',
            'anthropic/claude-3-sonnet'
        )
        self.model_combo.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # API Key
        ttk.Label(main_frame, text="OpenRouter API Key:").grid(row=row, column=0, sticky=tk.W, pady=5)
        api_key_frame = ttk.Frame(main_frame)
        api_key_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)

        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(api_key_frame, textvariable=self.api_key_var,
                                       width=25, show="*")
        self.api_key_entry.grid(row=0, column=0, sticky=tk.W)

        self.show_key_var = tk.BooleanVar()
        self.show_key_check = ttk.Checkbutton(api_key_frame, text="Show",
                                              variable=self.show_key_var,
                                              command=self.toggle_api_key_visibility)
        self.show_key_check.grid(row=0, column=1, padx=5)
        row += 1

        # Max Tokens
        ttk.Label(main_frame, text="Max Tokens:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.max_tokens_var = tk.StringVar()
        self.max_tokens_entry = ttk.Entry(main_frame, textvariable=self.max_tokens_var, width=30)
        self.max_tokens_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Log Level
        ttk.Label(main_frame, text="Log Level:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.log_level_var = tk.StringVar()
        self.log_level_combo = ttk.Combobox(main_frame, textvariable=self.log_level_var, width=28)
        self.log_level_combo['values'] = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        self.log_level_combo.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Diagnostic Mode Checkbox
        self.diagnostic_mode_var = tk.BooleanVar()
        self.diagnostic_check = ttk.Checkbutton(
            main_frame,
            text="Enable Diagnostic Mode (detailed monitoring for troubleshooting)",
            variable=self.diagnostic_mode_var
        )
        self.diagnostic_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1

        # Save Settings Button
        self.save_btn = ttk.Button(main_frame, text="Save Settings", command=self.save_settings)
        self.save_btn.grid(row=row, column=0, columnspan=2, pady=10)
        row += 1

        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=row, column=0, columnspan=2,
                                                            sticky=(tk.W, tk.E), pady=10)
        row += 1

        # Server Control Section
        control_label = ttk.Label(main_frame, text="Server Control",
                                 font=('Arial', 12, 'bold'))
        control_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        row += 1

        # Status
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=row, column=0, columnspan=2, pady=5)

        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, padx=5)
        self.status_label = ttk.Label(status_frame, text="Unknown", foreground="gray")
        self.status_label.grid(row=0, column=1, padx=5)
        row += 1

        # Control Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        self.start_btn = ttk.Button(button_frame, text="Start Server",
                                    command=self.start_server, width=15)
        self.start_btn.grid(row=0, column=0, padx=5)

        self.stop_btn = ttk.Button(button_frame, text="Stop Server",
                                   command=self.stop_server, width=15)
        self.stop_btn.grid(row=0, column=1, padx=5)
        self.stop_btn.config(state=tk.DISABLED)

        self.refresh_btn = ttk.Button(button_frame, text="Refresh Status",
                                      command=self.check_server_status, width=15)
        self.refresh_btn.grid(row=0, column=2, padx=5)
        row += 1

        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=row, column=0, columnspan=2,
                                                            sticky=(tk.W, tk.E), pady=10)
        row += 1

        # Testing Section
        test_label = ttk.Label(main_frame, text="Testing",
                              font=('Arial', 12, 'bold'))
        test_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        row += 1

        # Test Buttons
        test_button_frame = ttk.Frame(main_frame)
        test_button_frame.grid(row=row, column=0, columnspan=2, pady=5)

        self.test_health_btn = ttk.Button(test_button_frame, text="Test Backend Health",
                                          command=self.test_backend_health, width=20)
        self.test_health_btn.grid(row=0, column=0, padx=5, pady=2)

        self.test_ai_btn = ttk.Button(test_button_frame, text="Test AI Connection",
                                      command=self.test_ai_connection, width=20)
        self.test_ai_btn.grid(row=0, column=1, padx=5, pady=2)

        self.diagnostic_report_btn = ttk.Button(test_button_frame, text="View Diagnostic Report",
                                                command=self.view_diagnostic_report, width=20)
        self.diagnostic_report_btn.grid(row=0, column=2, padx=5, pady=2)
        row += 1

        # Log Output
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="5")
        log_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S),
                      pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80,
                                                  wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Clear Log Button
        self.clear_log_btn = ttk.Button(log_frame, text="Clear Log",
                                       command=self.clear_log)
        self.clear_log_btn.grid(row=1, column=0, pady=5)
        row += 1

        # Configure main_frame row weight for log expansion
        main_frame.rowconfigure(row - 1, weight=1)

    def toggle_api_key_visibility(self):
        """Toggle API key visibility"""
        if self.show_key_var.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")

    def load_settings(self):
        """Load settings from settings manager"""
        self.port_var.set(str(self.settings_manager.get('server_port', 8077)))
        self.model_var.set(self.settings_manager.get('default_model', 'deepseek/deepseek-chat'))
        self.max_tokens_var.set(str(self.settings_manager.get('max_tokens', 32000)))
        self.log_level_var.set(self.settings_manager.get('log_level', 'INFO'))
        self.diagnostic_mode_var.set(self.settings_manager.get('diagnostic_mode', False))

        api_key = self.settings_manager.get_api_key()
        if api_key:
            self.api_key_var.set(api_key)

        self.log_message("Settings loaded successfully")

    def save_settings(self):
        """Save settings to settings manager"""
        try:
            # Validate port
            port = int(self.port_var.get())
            if port < 1024 or port > 65535:
                messagebox.showerror("Error", "Port must be between 1024 and 65535")
                return

            # Validate max tokens
            max_tokens = int(self.max_tokens_var.get())
            if max_tokens < 1000:
                messagebox.showerror("Error", "Max tokens must be at least 1000")
                return

            # Save settings
            self.settings_manager.set('server_port', port)
            self.settings_manager.set('default_model', self.model_var.get())
            self.settings_manager.set('max_tokens', max_tokens)
            self.settings_manager.set('log_level', self.log_level_var.get())
            self.settings_manager.set('diagnostic_mode', self.diagnostic_mode_var.get())
            self.settings_manager.set_api_key(self.api_key_var.get())

            self.log_message("Settings saved successfully")
            if self.diagnostic_mode_var.get():
                self.log_message("WARNING: Diagnostic mode enabled - detailed logging active")
            messagebox.showinfo("Success", "Settings saved successfully!")

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")

    def log_message(self, message):
        """Add message to log output"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def clear_log(self):
        """Clear log output"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def find_process_by_port(self, port):
        """Find process ID using specific port"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.status == 'LISTEN':
                return conn.pid
        return None

    def check_server_status(self):
        """Check if server is running"""
        port = int(self.port_var.get())
        pid = self.find_process_by_port(port)

        if pid:
            self.server_running = True
            self.status_label.config(text=f"Running (PID: {pid})", foreground="green")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.log_message(f"Server is running on port {port} (PID: {pid})")
        else:
            self.server_running = False
            self.status_label.config(text="Stopped", foreground="red")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.log_message(f"Server is not running on port {port}")

    def start_server(self):
        """Start the backend server"""
        try:
            # Save settings first
            self.save_settings()

            port = int(self.port_var.get())

            # Check if port is already in use
            if self.find_process_by_port(port):
                messagebox.showerror("Error", f"Port {port} is already in use!")
                return

            # Start server in separate process
            self.log_message(f"Starting server on port {port}...")

            # Use pythonw on Windows to avoid console window
            python_exe = sys.executable
            if sys.platform == 'win32':
                python_exe = python_exe.replace('python.exe', 'pythonw.exe')
                if not Path(python_exe).exists():
                    python_exe = sys.executable

            # Set up environment variables
            import os
            env = os.environ.copy()

            # Enable diagnostic mode if checkbox is checked
            diagnostic_mode = self.settings_manager.get('diagnostic_mode', False)
            if diagnostic_mode:
                env['ENABLE_DIAGNOSTICS'] = 'true'
                self.log_message("[DIAG] Diagnostic mode enabled - detailed monitoring active")
            else:
                env['ENABLE_DIAGNOSTICS'] = 'false'

            self.server_process = subprocess.Popen(
                [python_exe, 'main.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path(__file__).parent,
                env=env
            )

            # Wait a moment and check status
            self.root.after(2000, self.check_server_status)

        except Exception as e:
            self.log_message(f"Error starting server: {str(e)}")
            messagebox.showerror("Error", f"Failed to start server: {str(e)}")

    def stop_server(self):
        """Stop the backend server"""
        try:
            port = int(self.port_var.get())
            pid = self.find_process_by_port(port)

            if pid:
                self.log_message(f"Stopping server (PID: {pid})...")
                process = psutil.Process(pid)
                process.terminate()
                process.wait(timeout=5)
                self.log_message("Server stopped successfully")
            else:
                self.log_message("No server process found")

            self.check_server_status()

        except psutil.TimeoutExpired:
            self.log_message("Server did not stop gracefully, forcing...")
            process.kill()
            self.check_server_status()
        except Exception as e:
            self.log_message(f"Error stopping server: {str(e)}")
            messagebox.showerror("Error", f"Failed to stop server: {str(e)}")

    def test_backend_health(self):
        """Test backend health endpoint"""
        port = int(self.port_var.get())
        url = f"http://localhost:{port}/"

        self.log_message(f"Testing backend health at {url}...")

        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_message(f"Backend is healthy!")
                self.log_message(f"  Status: {data.get('status')}")
                self.log_message(f"  Version: {data.get('version')}")
                self.log_message(f"  AI Enabled: {data.get('ai_enabled')}")
                messagebox.showinfo("Success", "Backend is healthy!")
            else:
                self.log_message(f"Backend returned status {response.status_code}")
                messagebox.showwarning("Warning", f"Backend returned status {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.log_message("Cannot connect to backend - is it running?")
            messagebox.showerror("Error", "Cannot connect to backend. Is it running?")
        except Exception as e:
            self.log_message(f"Error testing backend: {str(e)}")
            messagebox.showerror("Error", f"Error: {str(e)}")

    def test_ai_connection(self):
        """Test OpenRouter AI connection"""
        port = int(self.port_var.get())
        url = f"http://localhost:{port}/process-html"

        self.log_message("Testing AI connection...")

        test_html = "<html><body><h1>Test</h1><p>Testing AI connection.</p></body></html>"

        try:
            response = requests.post(
                url,
                json={
                    'url': 'https://test.example.com',
                    'html': test_html,
                    'title': 'Test',
                    'use_ai': True
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                used_ai = data.get('used_ai', False)

                if used_ai:
                    self.log_message("AI connection successful!")
                    self.log_message(f"  Model: {self.model_var.get()}")
                    self.log_message(f"  Response length: {len(data.get('markdown', ''))} chars")
                    messagebox.showinfo("Success", "AI connection successful!")
                else:
                    error = data.get('error', 'Unknown')
                    self.log_message(f"AI not used. Reason: {error}")
                    messagebox.showwarning("Warning",
                                         f"AI not used. Using fallback.\nReason: {error}")
            else:
                self.log_message(f"Request failed with status {response.status_code}")
                messagebox.showerror("Error", f"Request failed: {response.status_code}")

        except requests.exceptions.ConnectionError:
            self.log_message("Cannot connect to backend - is it running?")
            messagebox.showerror("Error", "Cannot connect to backend. Is it running?")
        except Exception as e:
            self.log_message(f"Error testing AI: {str(e)}")
            messagebox.showerror("Error", f"Error: {str(e)}")

    def view_diagnostic_report(self):
        """View diagnostic status report"""
        port = int(self.port_var.get())
        url = f"http://localhost:{port}/diagnostics"

        self.log_message("Fetching diagnostic report...")

        try:
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                self.log_message("=" * 80)
                self.log_message("DIAGNOSTIC REPORT")
                self.log_message("=" * 80)
                self.log_message(f"Uptime: {data.get('uptime_seconds', 0):.1f}s")
                self.log_message(f"Active Threads: {data.get('active_threads', 0)}")
                self.log_message(f"Thread Names: {', '.join(data.get('thread_names', []))}")
                self.log_message(f"Requests In Progress: {data.get('requests_in_progress', 0)}")

                in_progress = data.get('in_progress_details', [])
                if in_progress:
                    self.log_message(f"\nWARNING: {len(in_progress)} requests still in progress!")
                    import time
                    for req in in_progress:
                        elapsed = time.time() - req.get('start_time', 0)
                        self.log_message(f"  - {req.get('endpoint')}: {elapsed:.1f}s elapsed")
                else:
                    self.log_message("[OK] No requests in progress (healthy)")

                completed = data.get('completed_requests_count', 0)
                self.log_message(f"\nCompleted Requests: {completed}")

                recent = data.get('recent_requests', [])
                if recent:
                    self.log_message(f"\nRecent Requests:")
                    for req in recent[-5:]:
                        status = req.get('status')
                        duration = req.get('duration', 0)
                        endpoint = req.get('endpoint')
                        status_icon = "[OK]" if status == "success" else "[FAIL]"
                        self.log_message(f"  {status_icon} {endpoint}: {status} ({duration:.2f}s)")

                locks = data.get('active_locks', {})
                total_locks = sum(locks.values())
                self.log_message(f"\nActive Locks: {total_locks}")

                if total_locks > 0:
                    self.log_message("WARNING: Locks are still held!")
                    for lock_name, count in locks.items():
                        self.log_message(f"  - {lock_name}: {count} holders")

                    import time
                    lock_details = data.get('lock_details', {})
                    if lock_details:
                        for lock_name, entries in lock_details.items():
                            self.log_message(f"  Lock: {lock_name}")
                            for entry in entries:
                                elapsed = time.time() - entry.get('acquired_time', entry.get('acquire_time', 0))
                                self.log_message(f"    Thread {entry.get('thread_id')}: {entry.get('status')} ({elapsed:.1f}s)")
                else:
                    self.log_message("[OK] No active locks (healthy)")

                self.log_message("=" * 80)

                # Show summary in messagebox
                if in_progress or total_locks > 0:
                    messagebox.showwarning(
                        "Diagnostic Report - Issues Detected",
                        f"WARNING: Potential Issues Detected!\n\n"
                        f"Requests In Progress: {len(in_progress)}\n"
                        f"Active Locks: {total_locks}\n\n"
                        f"See log for details."
                    )
                else:
                    messagebox.showinfo(
                        "Diagnostic Report - Healthy",
                        f"System Healthy\n\n"
                        f"Uptime: {data.get('uptime_seconds', 0):.1f}s\n"
                        f"Active Threads: {data.get('active_threads', 0)}\n"
                        f"Completed Requests: {completed}\n"
                        f"No hanging requests or locks"
                    )

            elif response.status_code == 404:
                self.log_message("[ERROR] Diagnostic mode not enabled on server")
                self.log_message("Enable 'Diagnostic Mode' checkbox, save settings, and restart server")
                messagebox.showwarning(
                    "Diagnostics Not Enabled",
                    "Diagnostic mode is not enabled.\n\n"
                    "To enable:\n"
                    "1. Check 'Enable Diagnostic Mode' checkbox\n"
                    "2. Click 'Save Settings'\n"
                    "3. Restart the server"
                )
            else:
                self.log_message(f"Request failed with status {response.status_code}")
                messagebox.showerror("Error", f"Request failed: {response.status_code}")

        except requests.exceptions.ConnectionError:
            self.log_message("Cannot connect to backend - is it running?")
            messagebox.showerror("Error", "Cannot connect to backend. Is it running?")
        except Exception as e:
            self.log_message(f"Error fetching diagnostic report: {str(e)}")
            messagebox.showerror("Error", f"Error: {str(e)}")


def main():
    """Run the GUI application"""
    root = tk.Tk()
    app = ServerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

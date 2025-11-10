"""
Launcher for Simple Page Saver Backend
Supports both GUI and direct server modes via command-line arguments
"""

import sys
import argparse
from pathlib import Path


def main():
    """Main launcher entry point"""
    parser = argparse.ArgumentParser(
        description='Simple Page Saver Backend Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  SimplePageSaver.exe              Start server directly (default)
  SimplePageSaver.exe -gui         Launch management GUI
  SimplePageSaver.exe --gui        Launch management GUI
  SimplePageSaver.exe -s           Start server directly
  SimplePageSaver.exe --server     Start server directly
  SimplePageSaver.exe -p 8080      Start server on port 8080
  SimplePageSaver.exe --port 8080  Start server on port 8080
        """
    )

    parser.add_argument(
        '-g', '--gui',
        action='store_true',
        help='Launch the management GUI'
    )

    parser.add_argument(
        '-s', '--server',
        action='store_true',
        help='Start server directly (default)'
    )

    parser.add_argument(
        '-p', '--port',
        type=int,
        help='Server port (overrides settings)'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Log level (overrides settings)'
    )

    args = parser.parse_args()

    # Determine mode
    if args.gui:
        launch_gui()
    else:
        # Default to server mode
        launch_server(port=args.port, log_level=args.log_level)


def launch_gui():
    """Launch the Tkinter management GUI"""
    print("Launching Simple Page Saver Management GUI...")

    try:
        import tkinter as tk
        from gui import ServerGUI

        root = tk.Tk()
        app = ServerGUI(root)
        root.mainloop()

    except ImportError as e:
        print(f"Error: Failed to import GUI components: {e}")
        print("Make sure tkinter is installed (should be included with Python)")
        sys.exit(1)
    except Exception as e:
        print(f"Error launching GUI: {e}")
        sys.exit(1)


def launch_server(port=None, log_level=None):
    """Launch the server directly"""
    print("=" * 60)
    print("  Simple Page Saver Backend Server")
    print("=" * 60)

    try:
        from settings_manager import SettingsManager
        from logging_config import setup_logging
        import uvicorn
        import os

        # Load settings
        settings = SettingsManager()

        # Override with command-line arguments
        if port:
            settings.set('server_port', port)
            print(f"Using port from command-line: {port}")

        if log_level:
            settings.set('log_level', log_level)
            print(f"Using log level from command-line: {log_level}")

        # Setup logging
        logger = setup_logging(log_level=settings.get('log_level', 'INFO'))

        # Export settings as environment variables
        env_vars = settings.export_for_env()
        for key, value in env_vars.items():
            os.environ[key] = value

        server_port = settings.get('server_port', 8077)
        server_log_level = settings.get('log_level', 'INFO')

        logger.info("=" * 60)
        logger.info("Server Configuration:")
        logger.info(f"  Port: {server_port}")
        logger.info(f"  Model: {settings.get('default_model')}")
        logger.info(f"  Log Level: {server_log_level}")
        logger.info(f"  AI Enabled: {bool(settings.get_api_key())}")
        logger.info("=" * 60)

        print(f"\nStarting server on http://localhost:{server_port}")
        print(f"API Documentation: http://localhost:{server_port}/docs")
        print(f"AI Enabled: {bool(settings.get_api_key())}")
        print("\nPress CTRL+C to stop the server")
        print("=" * 60)
        print()

        # Import and run the application
        from main_updated import app

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=server_port,
            log_level=server_log_level.lower()
        )

    except ImportError as e:
        print(f"Error: Failed to import server components: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

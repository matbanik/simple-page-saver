"""
Build script for creating executable of Simple Page Saver Backend
Uses PyInstaller to create standalone executable
"""

import PyInstaller.__main__
import shutil
from pathlib import Path

# Clean previous builds
dist_dir = Path('dist')
build_dir = Path('build')

if dist_dir.exists():
    shutil.rmtree(dist_dir)
if build_dir.exists():
    shutil.rmtree(build_dir)

print("Building Simple Page Saver Backend executable...")
print("Entry point: launcher.py (supports both GUI and server modes)")

# PyInstaller configuration
PyInstaller.__main__.run([
    'launcher.py',  # Main entry point (supports command-line args)
    '--name=SimplePageSaver',
    '--onefile',  # Single executable
    '--console',  # Keep console for server mode and command-line args
    '--add-data=settings.json;.' if Path('settings.json').exists() else '--add-data=.env.example;.',
    '--hidden-import=uvicorn',
    '--hidden-import=uvicorn.logging',
    '--hidden-import=uvicorn.loops',
    '--hidden-import=uvicorn.loops.auto',
    '--hidden-import=uvicorn.protocols',
    '--hidden-import=uvicorn.protocols.http',
    '--hidden-import=uvicorn.protocols.http.auto',
    '--hidden-import=uvicorn.protocols.websockets',
    '--hidden-import=uvicorn.protocols.websockets.auto',
    '--hidden-import=uvicorn.lifespan',
    '--hidden-import=uvicorn.lifespan.on',
    '--collect-all=fastapi',
    '--collect-all=pydantic',
    '--collect-all=bs4',
    '--collect-all=lxml',
    '--icon=NONE',  # Add your icon path here if you have one
])

print("\n" + "=" * 60)
print("Build complete!")
print("=" * 60)
print(f"Executable location: {dist_dir / 'SimplePageSaver.exe'}")
print()
print("Usage:")
print("  SimplePageSaver.exe              Start server directly (default)")
print("  SimplePageSaver.exe -gui         Launch management GUI")
print("  SimplePageSaver.exe --gui        Launch management GUI")
print("  SimplePageSaver.exe -p 8080      Start server on port 8080")
print("  SimplePageSaver.exe --help       Show all options")
print("=" * 60)

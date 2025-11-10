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

# PyInstaller configuration
PyInstaller.__main__.run([
    'gui.py',  # Main entry point
    '--name=SimplePageSaver',
    '--onefile',  # Single executable
    '--windowed',  # No console window for GUI
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

print("\nBuild complete!")
print(f"Executable location: {dist_dir / 'SimplePageSaver.exe'}")
print("\nYou can now run the executable to start the GUI.")

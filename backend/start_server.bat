@echo off
REM Convenience launcher for Simple Page Saver Server

if exist "dist\SimplePageSaver.exe" (
    echo Starting Simple Page Saver Server...
    "dist\SimplePageSaver.exe"
) else if exist "SimplePageSaver.exe" (
    echo Starting Simple Page Saver Server...
    "SimplePageSaver.exe"
) else (
    echo ERROR: SimplePageSaver.exe not found!
    echo.
    echo Please build the executable first:
    echo   build.ps1
    echo.
    echo Or run directly with Python:
    echo   python launcher.py
    echo.
    pause
)

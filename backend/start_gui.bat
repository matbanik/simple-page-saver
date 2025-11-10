@echo off
REM Convenience launcher for Simple Page Saver GUI

if exist "dist\SimplePageSaver.exe" (
    echo Starting Simple Page Saver Management GUI...
    start "" "dist\SimplePageSaver.exe" -gui
) else if exist "SimplePageSaver.exe" (
    echo Starting Simple Page Saver Management GUI...
    start "" "SimplePageSaver.exe" -gui
) else (
    echo ERROR: SimplePageSaver.exe not found!
    echo.
    echo Please build the executable first:
    echo   build.ps1
    echo.
    echo Or run directly with Python:
    echo   python launcher.py -gui
    echo.
    pause
)

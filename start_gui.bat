@echo off
echo Starting Simple Page Saver Backend GUI...
echo.

REM Check if venv exists at root level
if exist "venv\Scripts\activate.bat" (
    echo Found virtual environment at root level
    call venv\Scripts\activate.bat
    cd backend
    goto :run_gui
)

REM Check if venv exists in backend folder
if exist "backend\venv\Scripts\activate.bat" (
    echo Found virtual environment in backend folder
    cd backend
    call venv\Scripts\activate.bat
    goto :run_gui
)

REM No venv found, create one at root level
echo No virtual environment found. Creating one at root level...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    echo Please ensure Python is installed and added to PATH
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing requirements...
cd backend
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)

:run_gui
echo.
echo Launching GUI...
python gui.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start GUI
    pause
    exit /b 1
)

pause
@echo off
REM Setup script for Windows environments
echo Setting up Port Scanner Server environment for Windows...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        echo Try: python -m pip install --upgrade pip
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing server dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    echo This might be due to missing Visual C++ Build Tools
    echo Please install Visual Studio Build Tools or Visual Studio Community
    pause
    exit /b 1
)

REM Initialize database
echo Initializing database...
python run.py init-db

echo.
echo Server setup complete!
echo.
echo To start the server:
echo   venv\Scripts\activate.bat
echo   python run.py
echo.
pause

@echo off
REM Build script for Speech to Text portable application
REM This creates a portable folder that can be copied to a USB drive

echo ==========================================
echo Speech to Text - Build Script
echo ==========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "src\main.py" (
    echo ERROR: Please run this script from the project root directory
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Run PyInstaller
echo.
echo Building executable with PyInstaller...
echo This may take several minutes...
echo.

pyinstaller speech_to_text.spec --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

REM Create models directory in dist
echo.
echo Creating models directory...
if not exist "dist\SpeechToText\models" mkdir "dist\SpeechToText\models"

REM Copy README
echo Copying documentation...
copy README.md "dist\SpeechToText\" >nul 2>&1

echo.
echo ==========================================
echo Build complete!
echo ==========================================
echo.
echo Output folder: dist\SpeechToText\
echo.
echo To use on USB:
echo   1. Copy the entire "dist\SpeechToText" folder to your USB drive
echo   2. Run SpeechToText.exe
echo   3. On first run, the Whisper model (~244MB) will be downloaded
echo.
echo Total size will be approximately 550-650MB after model download.
echo.
pause

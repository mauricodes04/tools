@echo off
REM Build script for OCRTool portable executable
REM Requires: Python with PyInstaller installed, Tesseract files in tesseract/ folder

echo ========================================
echo Building OCRTool Portable Executable
echo ========================================
echo.

REM Check if tesseract folder exists
if not exist "tesseract\tesseract.exe" (
    echo ERROR: tesseract\tesseract.exe not found!
    echo.
    echo Please copy Tesseract OCR files to the tesseract\ folder:
    echo   - tesseract.exe
    echo   - All required DLLs
    echo   - tessdata\eng.traineddata
    echo.
    echo See tesseract\README.txt for details.
    pause
    exit /b 1
)

REM Check if tessdata exists
if not exist "tesseract\tessdata\eng.traineddata" (
    echo ERROR: tesseract\tessdata\eng.traineddata not found!
    echo.
    echo Please copy eng.traineddata to tesseract\tessdata\
    pause
    exit /b 1
)

echo Tesseract files found. Starting build...
echo.

REM Run PyInstaller with the spec file
pyinstaller OCRTool.spec --clean --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Output folder: dist\OCRTool\
echo.
echo You can copy the entire dist\OCRTool\ folder to a USB drive.
echo Run OCRTool.exe to start the application.
echo.
pause

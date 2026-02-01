@echo off
echo ========================================
echo Building Rockyou Portable Executable
echo ========================================
echo.

REM Clean previous builds
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Build with PyInstaller
pyinstaller Rockyou.spec

echo.
if exist "dist\Rockyou\Rockyou.exe" (
    echo ========================================
    echo Build successful!
    echo Executable: dist\Rockyou\Rockyou.exe
    echo ========================================
) else (
    echo Build failed!
)

pause

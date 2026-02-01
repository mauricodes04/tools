@echo off
:: Speech to Text - Run Script
:: Refreshes PATH and launches the application

echo Starting Speech to Text...

:: Refresh PATH to include any newly installed tools (like FFmpeg)
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SysPath=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "UsrPath=%%b"
set "PATH=%SysPath%;%UsrPath%"

:: Run the application
python src/main.py

pause

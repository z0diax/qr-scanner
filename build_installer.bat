@echo off
REM Build script for QR Attendance Scanner

echo Building QR Attendance Scanner...
echo.

REM Step 1: Clean previous builds
echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist "QR Attendance Scanner.spec" del "QR Attendance Scanner.spec"
echo Done.
echo.

REM Step 2: Build executable with PyInstaller
echo Building executable with PyInstaller...
pyinstaller --onefile ^
  --windowed ^
  --name="QR Attendance Scanner" ^
  --specpath=. ^
  main.py

if errorlevel 1 (
  echo Error building executable!
  pause
  exit /b 1
)
echo Done.
echo.

REM Step 3: Create installer with Inno Setup (if installed)
echo.
echo Executable created successfully in dist\ folder!
echo.
echo To create an installer:
echo 1. Install Inno Setup from https://jrsoftware.org/isdl.php
echo 2. Open installer.iss with Inno Setup Compiler
echo 3. Click Compile
echo.
echo Alternatively, users can run QR Attendance Scanner.exe directly from dist\ folder.
echo.
pause

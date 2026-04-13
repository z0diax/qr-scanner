# Building the QR Attendance Scanner Installer

## Quick Build (Exe Only)

Simply run the batch script:

```cmd
build_installer.bat
```

This will:
1. Clean previous builds
2. Create `QR Attendance Scanner.exe` in the `dist\` folder
3. Show instructions for creating an installer

## Manual Build Steps

### Option 1: Simple Executable (No Installer)

```bash
pyinstaller build_exe.spec
```

Output: `dist\QR Attendance Scanner\QR Attendance Scanner.exe`

Users can run this directly without installation.

### Option 2: Professional Installer with Setup Wizard

**Requirements:**
- Inno Setup (free) - [Download here](https://jrsoftware.org/isdl.php)

**Steps:**
1. Build the executable first:
   ```bash
   pyinstaller build_exe.spec
   ```

2. Open Inno Setup and load `installer.iss`

3. Click "Compile" to generate `QRScannerSetup.exe`

## Distribution

- **Simple:** Share `QR Attendance Scanner.exe` from `dist\` folder
- **Professional:** Share `QRScannerSetup.exe` - includes uninstaller and shortcuts

## What Gets Installed

- Application executable
- All PySide6, OpenCV, and PyZBar dependencies bundled
- Start menu shortcuts
- Desktop shortcut (optional)

## System Requirements

- Windows 7 or later
- .NET Framework (usually pre-installed)
- Webcam for QR scanning

## Troubleshooting

**"RecursionError" in build:**
```bash
pyinstaller --onefile --windowed --name="QR Attendance Scanner" main.py
```

**Missing dependencies:**
```bash
pip install -r requirements.txt
pyinstaller build_exe.spec
```

**Antivirus warning:**
Some antivirus software may flag PyInstaller executables. This is a false positive. You can:
- Sign the executable with a code certificate
- Report it to your antivirus vendor
- Use a different build approach (e.g., py2exe, cx_Freeze)

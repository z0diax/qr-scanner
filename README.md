# QR Attendance Scanner

Desktop QR attendance scanner built with Python, PySide6, OpenCV, and Google Sheets integration.

The app can:

- scan QR codes from a webcam
- sync a roster from Google Sheets
- store attendance locally for offline use
- export attendance back to Google Sheets through Google Apps Script

## Requirements

- Python 3.10+
- Webcam
- Windows is the primary target in this project

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

On Windows, the local database is stored in:

```text
%LOCALAPPDATA%\QRAttendanceScanner\attendance.db
```

## Google Sheets Sync

Paste a normal Google Sheets link into the sync field. The app converts standard sheet URLs to the CSV export URL automatically.

Example accepted input:

```text
https://docs.google.com/spreadsheets/d/your-sheet-id/edit#gid=0
```

Important:

- the sheet must be shared as `Anyone with the link`
- access must be `Viewer`
- if the sheet is private, Google will reject the CSV request

## Attendance Export Setup

This project includes an example Google Apps Script file at `google_apps_script_example.gs`.

Basic setup:

1. Open the target Google Sheet.
2. Go to `Extensions > Apps Script`.
3. Paste the contents of `google_apps_script_example.gs`.
4. Deploy it as a Web App.
5. Set Web App access so the desktop app can call it.
6. Copy the Web App URL into the app's export field.

The export script writes attendance rows into the spreadsheet and can replace rows for the same attendance date.

## Dependencies

- `PySide6` for the desktop UI
- `opencv-python` for camera access
- `pyzbar` for QR decoding

## Notes

- Sync downloads the current sheet as CSV.
- Export sends attendance records as JSON to the Apps Script endpoint.
- The app keeps local attendance data even when the network is unavailable.

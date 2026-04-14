# QR Attendance Scanner

A desktop application for scanning QR codes to track attendance in real-time. Syncs roster data from Google Sheets and exports attendance records back to Google Sheets with full offline support.

## Features

✅ **QR Code Scanning** - Scan QR codes from webcam with live preview  
✅ **Google Sheets Sync** - Import roster data from public Google Sheets  
✅ **Offline Support** - Works without internet; syncs when connection returns  
✅ **Local Database** - Stores attendance records locally for reliability  
✅ **Attendance Export** - Send attendance data back to Google Sheets via Apps Script  
✅ **Real-time Statistics** - View present/absent counts and attendance rate  
✅ **Attendance History** - Browse all scans for the day with timestamps  
✅ **Manual Entry** - Mark users as present without scanning QR codes  
✅ **Duplicate Prevention** - Warns when same user scans twice in one day  
✅ **Audio/Visual Feedback** - Beeps and styled notifications for clarity  
✅ **Network Status** - Real-time online/offline indicator  

## System Requirements

- **Python 3.10+**
- **Windows 7+** (primary target)
- **Webcam** (for QR scanning)
- **Internet connection** (for syncing; app works offline without it)

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- `PySide6` - Desktop UI framework
- `opencv-python` - Camera/video access
- `pyzbar` - QR code decoding

### 2. Run the Application

```bash
python main.py
```

On Windows, the local database is stored in:
```
%LOCALAPPDATA%\QRAttendanceScanner\attendance.db
```

## Google Sheets Setup

### Get a Roster Sheet URL

1. Create or open a Google Sheet with your roster
2. Share the sheet: **Anyone with the link → Viewer access**
3. Copy the normal Google Sheets URL:
   ```
   https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit#gid=0
   ```

The app automatically converts this to a CSV export URL for data import.

**Sheet Requirements:**
- Must be shared as "Anyone with the link"
- Access level must be "Viewer" (reader-only)
- Must have at least an ID column for matching scans

### Supported Column Names

The app looks for these column names (case-insensitive):
- **ID columns**: `id`, `participant id`, `student id`, `user id`
- **Name columns**: `name`, `full name`, `student name`
- **Course columns**: `course`, `class`, `group`, `department`

## Attendance Export Setup

### Create a Google Apps Script

1. Open your target Google Sheet
2. Go to **Extensions → Apps Script**
3. Delete the default `myFunction()` code
4. Paste the entire contents of `installer/scriptforqr_combined.gs`
5. Click **Deploy** → **New Deployment** → **Type: Web app**
   - Execute as: Your email
   - Who has access: Anyone
6. Copy the Web App URL (looks like `https://script.google.com/macros/s/...`)
7. Paste this URL into the app's "Google Apps Script Export URL" field

**The script:**
- Receives attendance data from the desktop app
- Creates an "Attendance Export" sheet automatically
- Replaces old attendance for the same date
- Includes QR code generation and email confirmation features

## App Walkthrough

### Camera Tab
- **Start Scan** - Begin scanning QR codes
- **Stop Scan** - Pause recording
- Real-time camera preview
- Scan details display
- Network status indicator

### Synced Users Tab
- View all imported roster data
- **Statistics**: Total users, Present today, Absent today, Attendance rate
- **Search** - Filter by ID, name, email, or any field
- **Mark Present** - Manually record attendance (select user, click button)
- **Sync Sheet** - Download latest roster from Google Sheets
- **Export Attendance** - Send attendance to Google Sheets
- **Delete Local Records** - Clear all data (URLs saved for re-sync)

### Attendance History Tab
- All scans for today (newest first)
- Shows: Time, User ID, Name, Course
- **Refresh** button to update

### System Status Tab
- Connection status (Online/Offline)
- Last sync timestamp
- Last export timestamp
- Recent activity log

### Data Sources Tab
- **Google Sheets Link** - Paste your roster sheet URL
- **Google Apps Script URL** - Paste your Web App deployment URL
- Test/Open buttons for quick access

## Features in Detail

### Duplicate Scan Detection
If the same user scans multiple times in one day:
- First scan: ✅ Success (1000Hz beep)
- Subsequent scans: ⚠️ Warning (600Hz beep) - prevents double-counting

### Attendance Status
Each user can be:
- **Present** - Scanned at least once today or manually marked
- **Absent** - No scan recorded
- **(Manual)** - Status was changed in the app interface

### QR Code Matching
The app automatically matches scanned QR codes to user IDs by:
1. Exact ID match
2. Prefix matching (first user whose ID starts with scan value)
3. Contains matching (first user whose ID contains scan value)

### Email Notifications
When using the Apps Script:
- Automatically generates QR codes (300x300px)
- Sends confirmation email with:
  - Unique Participant ID
  - All submitted information
  - QR code as attachment and inline image
- Professional, styled HTML email template

## Offline Operation

The app maintains full functionality offline:
- ✅ Scans work completely offline
- ✅ Local database stores all attendance
- ✅ Manual entries work offline
- ❌ Sync requires internet
- ❌ Export requires internet

When internet returns, sync and export operations will work normally.

## Database

Attendance data is stored locally in SQLite:
- **users** - Synced roster data
- **attendance** - Scan records (user ID + timestamp)
- **attendance_override** - Manual attendance changes
- **settings** - App configuration (URLs, headers, sync times)

## Troubleshooting

### Camera not detected
- Check that webcam is connected
- Ensure no other app is using the camera
- Try restarting the application
- Check Windows device permissions

### Sync fails with "unreachable" error
- Verify internet connection
- Check that Sheet URL is correct and publicly shared
- Ensure share setting is "Anyone with the link"
- Try re-pasting the URL in the app

### Export fails
- Verify Apps Script URL is correct
- Check that Google Sheet is accessible
- Ensure Apps Script was deployed as "Web app → Anyone"
- Check Google Apps Script execution logs for errors

### QR Code not scanned
- Ensure QR code is properly formatted
- Check camera lighting
- Code must contain a valid user ID from roster
- Try manually entering the ID using "Mark Present"

## Data Privacy

- ✅ All attendance data stored locally on your computer
- ✅ Only syncs with YOUR Google Sheets
- ✅ No data sent to external servers (except Google's services)
- ✅ Apps Script requires explicit deployment by you

## Building an EXE

This project includes build configuration for PyInstaller:

```bash
python -m PyInstaller build_exe.spec
```

Creates a standalone `.exe` in the `build/` directory.

## Project Structure

```
qr-scanner/
├── main.py                 # Application entry point
├── ui.py                   # PySide6 UI (camera, users, history, status, sync)
├── database.py             # SQLite database manager
├── scanner.py              # QR scanner thread
├── sync.py                 # Google Sheets sync & export
├── requirements.txt        # Python dependencies
├── installer/
│   ├── scriptforqr_combined.gs    # Google Apps Script
│   └── build_exe.spec             # PyInstaller config
└── README.md              # This file
```

## Dependencies

See `requirements.txt`:
- **PySide6** - GUI framework
- **opencv-python** - Camera & QR detection
- **pyzbar** - QR code decoding

## License

This project is provided as-is for educational and organizational use.

## Support

For issues or feature requests, contact the development team or check the app logs.

---

**Version**: 2.0 (with Attendance History, Manual Entry, and Statistics)  
**Last Updated**: April 2026

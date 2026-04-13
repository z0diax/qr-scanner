# Google Sheets Sync Troubleshooting Guide

## Error: "No internet connection or the CSV link is unreachable"

This error can occur for several reasons. Follow these steps to diagnose and fix it.

## Quick Checklist

- [ ] Google Sheet is shared: **"Anyone with the link" as Viewer**
- [ ] You have internet connection (try opening google.com in your browser)
- [ ] Google Sheets link is in the correct format
- [ ] The spreadsheet hasn't been moved or deleted
- [ ] You're using the correct sheet tab (if multiple tabs exist)

## Step-by-Step Troubleshooting

### 1. Verify Google Sheets Sharing Settings

**Your Google Sheet MUST be shared publicly:**
1. Open your Google Sheet
2. Click **Share** (top right)
3. Change to **"Anyone with the link"**
4. Set access level to **Viewer** (read-only)
5. Click **Copy link**
6. Paste this link into the QR Scanner app

**Why this matters:** If the sheet is private or requires sign-in, the app cannot access it.

### 2. Check the Google Sheets Link Format

**Correct formats:**
```
https://docs.google.com/spreadsheets/d/SHEET-ID/edit#gid=0
https://docs.google.com/spreadsheets/d/SHEET-ID/edit?usp=sharing
```

**Copy exactly as shown:**
1. Open your shared Google Sheet in browser
2. Look at the URL in the address bar
3. Copy it completely
4. Paste into QR Scanner "Sync" tab

**Important:** If you see `#gid=123`, the `123` specifies which sheet tab to use.

### 3. Test Internet Connection

The app needs to download from Google Sheets.

**Test in the app:**
- Look at the top right of the Camera tab
- You should see **ONLINE** (green) or **OFFLINE** (gray)
- If OFFLINE, you don't have internet

**Test manually:**
1. Open Windows PowerShell
2. Run: `Test-Connection google.com -Count 1`
3. If successful, you have internet
4. If fails, fix your network connection and try again

### 4. Verify the CSV Export URL

The app converts your Google Sheet link to a CSV export URL automatically.

**To manually test:**
1. Take your Google Sheets link: `https://docs.google.com/spreadsheets/d/SHEET-ID/edit#gid=0`
2. Replace `/edit#` with `/export?`
3. Add: `format=csv&gid=0` (if tab ID is 0)
4. Result: `https://docs.google.com/spreadsheets/d/SHEET-ID/export?format=csv&gid=0`
5. Open this URL in your browser
6. If it works, you'll see CSV data
7. If it fails, you'll see an error page

### 5. Check for Multiple Sheet Tabs

If your Google Sheet has multiple tabs, you might be using the wrong one.

**Solution:** Make sure you're syncing from the correct tab.
- The link includes `#gid=0` (tab ID)
- Different tabs have different IDs
- Share the specific tab you want to sync

### 6. Check the Attendance Column Names

The sync expects certain column headers. If your columns don't match, you'll get a different error.

**Expected columns (or similar names):**
- ID / Student ID / Participant ID
- Name / Full Name
- Course / Program
- Email (optional)
- Any custom columns

## New Improved Error Messages

The updated app now shows more specific errors:

| Error | Meaning | Solution |
|-------|---------|----------|
| "No internet connection" | Network is down | Check your internet connection |
| "Google Sheets denied access" | Sheet is private | Share sheet as "Viewer" access |
| "Sheet tab could not be found" | Wrong gid in URL | Check the `#gid=0` part of URL |
| "CSV file is empty" | Sheet has no data | Add data to the spreadsheet |
| "Cannot open as CSV export" | URL format wrong | Verify the sharing and gid settings |
| "Request timed out" | Google is slow to respond | Try again in a moment |

## If You're Still Having Issues

1. **Try the direct CSV export URL:**
   - Instead of pasting your Google Sheets link
   - Paste the full CSV export URL
   - Example: `https://docs.google.com/spreadsheets/d/YOUR-ID/export?format=csv&gid=0`

2. **Test with a simple sheet:**
   - Create a new Google Sheet with just 2 columns: ID and Name
   - Add 2-3 test rows
   - Share it and try syncing
   - If this works, your original sheet has a data issue

3. **Check sheet tab ID:**
   - If syncing from a non-default tab (not the first tab)
   - Get the tab ID from the URL: `#gid=123`
   - Make sure this is included in the CSV export URL

## Example: Complete Sync Setup

Let's say you have a Google Sheet shared as "Anyone with the link":

```
Original link: https://docs.google.com/spreadsheets/d/1A2B3C4D5E6F7/edit#gid=0

What the app converts it to:
https://docs.google.com/spreadsheets/d/1A2B3C4D5E6F7/export?format=csv&gid=0

What you paste in the app:
https://docs.google.com/spreadsheets/d/1A2B3C4D5E6F7/edit#gid=0
(the app does the conversion automatically)
```

## Testing Checklist

After fixing issues:

- [ ] Sheet is publicly shared (Viewer access)
- [ ] You can open the CSV export URL in a browser
- [ ] The CSV preview in browser shows your data
- [ ] QR Scanner shows ONLINE status
- [ ] Click "Test CSV Link" button - should succeed
- [ ] Click "Sync" button - should load your data

---

If none of these steps work, please provide:
1. The exact error message from the app
2. Whether the ONLINE/OFFLINE badge shows
3. Whether you can open your Google Sheet's CSV export URL in a browser
4. A screenshot of your sheet's first few rows (redact sensitive data)

# Combined Google Apps Script Setup Guide

## Overview
`scriptforqr_combined.gs` includes both:
- **QR code generation & email** (form submission)
- **Attendance data export** (web app endpoint)

All in a single, unified script.

## Step-by-Step Setup

### 1. Update Your Google Apps Script

**In your Google Sheet:**
1. Go to **Extensions** → **Apps Script**
2. Clear all existing code
3. Paste the entire contents of `scriptforqr_combined.gs`
4. **Save** (Ctrl+S)

### 2. Set Up Form Submission Trigger

**Automatic (Recommended):**
- The `onFormSubmit` function will automatically trigger when responses are submitted
- No manual setup needed - it's built-in

**Manual Verification:**
1. Click **Triggers** (clock icon on left)
2. Look for: `onFormSubmit` → `From form` → Your form name
3. Event: `On form submit`
4. If missing, create it:
   - Click "Create new trigger"
   - Function: `onFormSubmit`
   - Deployment: `Head`
   - Event source: `From form`
   - Event type: `On form submit`
   - Click **Save**

### 3. Deploy as Web App (for Attendance Export)

**Deploy:**
1. Click **Deploy** (top right)
2. Select **New Deployment**
3. Select deployment type: **Web app**
4. Execute as: **Your account**
5. Who has access: **Anyone**
6. Click **Deploy**
7. **Copy the URL** - you'll need this for your Python app

**Example URL:**
```
https://script.google.com/macros/d/[DEPLOYMENT_ID]/userwp
```

### 4. Configure Your Python App

In your QR Scanner app, paste the deployed URL into:
- **Tab:** "Data Sources"
- **Field:** "Export URL"
- Save it

Now when you click "Export Attendance", your data will go to this Google Apps Script.

### 5. Test Everything

**Test Form Submission:**
1. Submit a test response to your Google Form
2. Check: 
   - Was Participant ID generated? ✓
   - Was QR code emailed? ✓
   - Check your email inbox

**Test Attendance Export:**
1. In your Python app, sync some users
2. Scan a few QR codes
3. Click "Export Attendance"
4. Check: Your Google Sheet should have attendance data updated ✓

## Troubleshooting

### Form submission email not sent
- **Check:** Email address column exists ("Email", "Email Address")
- **Check:** Email values are not empty
- **Fix:** Edit the form response manually, re-save the sheet → trigger runs again

### Export endpoint returns error
- **Check:** Web app deployment URL is correct (copy-pasted fully)
- **Check:** Python app has internet connection
- **Check:** Google Sheet is accessible (not archived/deleted)
- **Fix:** Redeploy the web app with new deployment

### "No Email Column Found" error
- **Solution:** Rename your email column to exactly "Email Address" or "Email"
- **Or:** Edit the header check in `onFormSubmit` function

### QR code not generating
- **Check:** QR server API is accessible (https://api.qrserver.com/)
- **Check:** Participant ID was created successfully
- **Fix:** Check Apps Script logs (View → Logs) for errors

## File Structure

```
qr-scanner/
├── scriptforqr_combined.gs        ← Use this one script
├── scriptforqr.gs                  (old - can delete)
├── google_apps_script_example.gs   (old - can delete)
└── [other app files]
```

## Important Notes

✅ **Both functions use the same utility functions** (no duplication)
✅ **No need to manage two separate scripts** anymore
✅ **One web app URL** replaces the old two URLs
✅ **All participant data flows through one system**

## Next Steps

1. Copy `scriptforqr_combined.gs` code into your Apps Script
2. Set up the form submission trigger
3. Create web app deployment
4. Copy deployment URL to your Python app
5. Test both form submissions and attendance exports

---

**Questions?** Check the troubleshooting section or review the function comments in the script.

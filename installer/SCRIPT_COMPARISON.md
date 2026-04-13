# Combined Script Summary

## What Changed

### Before: Two Separate Scripts
```
scriptforqr.gs (QR code + email on form submit)
google_apps_script_example.gs (attendance export via web app)
│
├─ Duplicate utility functions
├─ Two separate deployments needed
├─ Two different URLs to manage
└─ Harder to maintain consistency
```

### After: One Combined Script
```
scriptforqr_combined.gs
│
├─ onFormSubmit() → QR code + email (form submission)
├─ doPost() → Attendance export (web app endpoint)
├─ Shared utility functions (no duplication)
├─ One deployment
└─ One clean system
```

## Code Organization

```javascript
scriptforqr_combined.gs
├─ PART 1: WEB APP ENDPOINT (doPost)
│  ├─ Receive attendance payload from Python
│  ├─ Update Google Sheet with records
│  └─ Return JSON status
│
├─ PART 2: FORM SUBMISSION (onFormSubmit)
│  ├─ Generate Participant ID
│  ├─ Create QR code
│  ├─ Email to participant
│  └─ Update sheet with ID
│
└─ UTILITIES (shared by both)
   ├─ ensureIdFirstColumn_()
   ├─ generateParticipantId_()
   ├─ findColumnIndex_()
   ├─ escapeHtml_()
   ├─ deriveHeadersFromPayload()
   ├─ getRecordValue()
   ├─ normalizeHeader()
   └─ prettifyHeader()
```

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Number of files** | 2 | 1 |
| **Entry points** | 2 | 2 (same file) |
| **Utility functions** | Duplicated | Shared |
| **Deployments needed** | 2 | 1 |
| **URLs to manage** | 2 | 1 |
| **Maintenance** | Complex | Simple |
| **Consistency** | Risk of divergence | Single source of truth |

## Function Reference

### onFormSubmit(e)
**Triggered:** When form is submitted
**Does:**
- Checks for email column
- Generates unique Participant ID
- Creates QR code via API
- Sends email with QR code attachment
- Updates sheet with ID

### doPost(e)
**Triggered:** When Python app sends POST request
**Does:**
- Parses attendance payload
- Updates or creates "Attendance Export" sheet
- Replaces old records for the same date
- Returns JSON response

## Testing Checklist

- [ ] Form submission generates Participant ID
- [ ] QR code attaches to email
- [ ] Email is received by participant
- [ ] Python app can sync from Google Sheet
- [ ] Python app can export attendance to sheet
- [ ] Attendance records appear in Google Sheet
- [ ] Exporting again replaces old data correctly

## Migration Path (if needed)

If you're moving from the old scripts:

1. **Backup old sheets** (export to CSV first)
2. **Copy `scriptforqr_combined.gs` code** into a new Apps Script project
3. **Test in new project** with test form and sheet
4. **Once verified**, update your production script
5. **Delete old script files** (optional)

---

**This combined approach is cleaner, easier to maintain, and reduces the risk of bugs from inconsistent code.**

/**
 * Allowed characters: letters, numbers, underscore, dash.
 */
var ID_PREFIX = "HRA";
/**
 * Number of digits for the sequence number. Example:
 * 3 -> 001, 4 -> 0001, etc.
 */
var ID_PAD_LENGTH = 3;

function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents);
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var sheetName = payload.sheet_name || "Attendance Export";
    var sheet = spreadsheet.getSheetByName(sheetName);

    if (!sheet) {
      sheet = spreadsheet.insertSheet(sheetName);
    }

    var headers = Array.isArray(payload.headers) && payload.headers.length > 0
      ? payload.headers
      : deriveHeadersFromPayload(payload);
    var attendanceDateColumn = headers.indexOf("Attendance Date");

    if (sheet.getLastRow() === 0) {
      sheet.appendRow(headers);
    } else {
      var existingHeaderRow = sheet.getRange(1, 1, 1, headers.length).getValues()[0];
      var headersDiffer = existingHeaderRow.length !== headers.length;
      if (!headersDiffer) {
        for (var headerIndex = 0; headerIndex < headers.length; headerIndex++) {
          if (String(existingHeaderRow[headerIndex]) !== String(headers[headerIndex])) {
            headersDiffer = true;
            break;
          }
        }
      }
      if (headersDiffer) {
        sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
      }
    }

    if (payload.mode === "replace_date" && payload.attendance_date && attendanceDateColumn >= 0) {
      var lastRow = sheet.getLastRow();
      if (lastRow > 1) {
        var values = sheet.getRange(2, 1, lastRow - 1, headers.length).getValues();
        for (var rowIndex = values.length - 1; rowIndex >= 0; rowIndex--) {
          if (String(values[rowIndex][attendanceDateColumn]) === String(payload.attendance_date)) {
            sheet.deleteRow(rowIndex + 2);
          }
        }
      }
    }

    var rows = (payload.records || []).map(function(record) {
      return headers.map(function(header) {
        return getRecordValue(record, header, payload);
      });
    });

    if (rows.length > 0) {
      sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, headers.length).setValues(rows);
    }

    return ContentService
      .createTextOutput(JSON.stringify({ ok: true, rows: rows.length }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: String(error) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// for QR code generation and email

function onFormSubmit(e) {
  try {
    var sheet = e.range.getSheet();
    var row = e.range.getRow();
    var lastColumn = sheet.getLastColumn();

    var headers = sheet.getRange(1, 1, 1, lastColumn).getValues()[0];

    // ALWAYS ensure Participant ID is column 1
    var participantIdCol = ensureIdFirstColumn_(sheet, headers);

    // Re-read headers after possible column insert
    headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    var lastColumn = sheet.getLastColumn();

    var emailCol = findColumnIndex_(headers, ["Email Address", "Email"]);

    if (emailCol === -1) {
      throw new Error('No "Email Address" or "Email" column found.');
    }

    var email = sheet.getRange(row, emailCol).getValue();

    if (!email) {
      throw new Error("Respondent email is empty.");
    }

    var existingId = sheet.getRange(row, participantIdCol).getValue();
    var participantId = existingId || generateParticipantId_(sheet, participantIdCol);

    sheet.getRange(row, participantIdCol).setValue(participantId);

    var qrUrl = "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=" + encodeURIComponent(participantId);
    var qrBlob = UrlFetchApp.fetch(qrUrl).getBlob().setName("qr_" + participantId + ".png");

    // Dynamically build email content from all columns
    var rowValues = sheet.getRange(row, 1, 1, lastColumn).getValues()[0];
    var plainBodyLines = [];
    var htmlBodyLines = [];

    var greeting = "Summary of your submitted information:";
    plainBodyLines.push(greeting);
    htmlBodyLines.push("<p><strong>" + greeting + "</strong></p>");
    htmlBodyLines.push("<ul>");

    // Iterate through all columns and include non-empty values
    for (var col = 1; col <= lastColumn; col++) {
      var header = headers[col - 1];
      var value = rowValues[col - 1];

      // Skip empty values and the participant ID column (we show that separately)
      if (!header || !value || col === participantIdCol) {
        continue;
      }

      var headerStr = String(header).trim();
      var valueStr = String(value).trim();

      plainBodyLines.push(headerStr + ": " + valueStr);
      htmlBodyLines.push('<li style="padding: 10px 0; color: #555; border-bottom: 1px solid #eee;"><strong style="color: #667eea; display: block; margin-bottom: 5px;">' + escapeHtml_(headerStr) + ':</strong> ' + escapeHtml_(valueStr) + '</li>');
    }

    htmlBodyLines.push("</ul>");

    var subject = "Your QR Code Registration";

    var plainBody =
      "Good Day!,\n\n" +
      "Your Participant ID: " + participantId + "\n\n" +
      plainBodyLines.join("\n") + "\n\n" +
      "Your QR code is attached and included in this email.";

    var htmlBody =
      '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 8px;">' +
      '  <div style="background: white; border-radius: 8px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">' +
      '    <h2 style="color: #333; margin-top: 0; text-align: center;">Registration Confirmation</h2>' +
      '    <hr style="border: none; border-top: 2px solid #667eea; margin: 30px 0;">' +
      '    <p style="color: #555; font-size: 16px;">Good Day!,</p>' +
      '    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 25px 0;">' +
      '      <p style="margin: 0; font-size: 14px; opacity: 0.9;">Your Participant ID</p>' +
      '      <p style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold; letter-spacing: 2px;">' + escapeHtml_(participantId) + '</p>' +
      '    </div>' +
      '    <h3 style="color: #333; margin-top: 30px; margin-bottom: 15px; font-size: 16px;">Registration Details</h3>' +
      '    <div style="background: #f8f9fa; padding: 20px; border-left: 4px solid #667eea; border-radius: 4px;">' +
      '      <ul style="list-style: none; padding: 0; margin: 0;">' +
      htmlBodyLines.join("") +
      '      </ul>' +
      '    </div>' +
      '    <div style="text-align: center; margin: 30px 0;">' +
      '      <p style="color: #666; font-size: 14px; margin-bottom: 15px;">Your QR Code</p>' +
      '      <img src="cid:qrcode" style="max-width: 250px; height: auto; border: 2px solid #e0e0e0; border-radius: 8px; padding: 10px; background: white;">' +
      '    </div>' +
      '    <p style="color: #999; font-size: 12px; text-align: center; margin-top: 20px; border-top: 1px solid #eee; padding-top: 20px;">' +
      '      This QR code is your unique identifier. Please keep it safe and secure.' +
      '    </p>' +
      '  </div>' +
      '</div>';

    GmailApp.sendEmail(email, subject, plainBody, {
      htmlBody: htmlBody,
      inlineImages: { qrcode: qrBlob },
      attachments: [qrBlob]
    });

  } catch (error) {
    Logger.log("Error in onFormSubmit: " + error.message);
    throw error;
  }
}

function ensureIdFirstColumn_(sheet, headers) {
  var idIndex = -1;

  for (var i = 0; i < headers.length; i++) {
    if (String(headers[i]).trim().toLowerCase() === "participant id") {
      idIndex = i + 1;
      break;
    }
  }

  if (idIndex === -1) {
    sheet.insertColumnBefore(1);
    sheet.getRange(1, 1).setValue("Participant ID");
    return 1;
  }

  return idIndex;
}

function sanitizePrefix_(value) {
  return String(value || "").trim().replace(/[^A-Za-z0-9_-]/g, "");
}


function generateParticipantId_(sheet, participantIdCol) {
  var year = new Date().getFullYear();
  var lastRow = sheet.getLastRow();

  // Use code-level prefix only (no spreadsheet fallback)
  var prefix = sanitizePrefix_(typeof ID_PREFIX !== "undefined" ? ID_PREFIX : "");

  var patternStart = String(prefix) + year + "-";

  var count = 0;

  if (lastRow > 1) {
    var values = sheet.getRange(2, participantIdCol, lastRow - 1, 1).getValues();

    for (var i = 0; i < values.length; i++) {
      var val = values[i][0];
      if (typeof val === "string" && String(val).indexOf(patternStart) === 0) {
        count++;
      }
    }
  }

  var next = count + 1;

  var padLen = (typeof ID_PAD_LENGTH !== "undefined" && parseInt(ID_PAD_LENGTH, 10) > 0)
    ? parseInt(ID_PAD_LENGTH, 10)
    : 3;

  var padded = String(next).padStart(padLen, "0");

  return patternStart + padded;
}

function findColumnIndex_(headers, possibleNames) {
  for (var i = 0; i < headers.length; i++) {
    var header = String(headers[i]).trim();
    for (var j = 0; j < possibleNames.length; j++) {
      if (header.toLowerCase() === possibleNames[j].toLowerCase()) {
        return i + 1;
      }
    }
  }
  return -1;
}

function escapeHtml_(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function deriveHeadersFromPayload(payload) {
  var records = payload.records || [];
  if (records.length > 0) {
    var firstRecord = records[0];
    var recordKeys = Object.keys(firstRecord);
    if (recordKeys.length > 0) {
      return recordKeys.map(function(key) {
        return prettifyHeader(key);
      });
    }
  }

  return [
    "ID",
    "Name",
    "Course",
    "Attendance",
    "Last Scanned",
    "Manual Override",
    "Attendance Date",
    "Exported At"
  ];
}

function getRecordValue(record, header, payload) {
  if (record == null) {
    return "";
  }

  if (Object.prototype.hasOwnProperty.call(record, header)) {
    return record[header] || "";
  }

  var legacyMap = {
    "ID": "id",
    "Name": "name",
    "Course": "course",
    "Attendance": "attendance_status",
    "Last Scanned": "last_scanned",
    "Manual Override": "manual_status",
    "Attendance Date": "attendance_date",
    "Exported At": "exported_at"
  };

  var normalizedHeader = normalizeHeader(header);
  var candidateKeys = [header];

  if (legacyMap[header]) {
    candidateKeys.push(legacyMap[header]);
  }

  candidateKeys.push(normalizedHeader);
  candidateKeys.push(normalizedHeader.replace(/\s+/g, "_"));
  candidateKeys.push(normalizedHeader.toLowerCase());

  for (var keyIndex = 0; keyIndex < candidateKeys.length; keyIndex++) {
    var key = candidateKeys[keyIndex];
    if (Object.prototype.hasOwnProperty.call(record, key) && record[key] !== undefined && record[key] !== null) {
      return record[key];
    }
  }

  if (header === "Attendance Date") {
    return payload.attendance_date || "";
  }
  if (header === "Exported At") {
    return payload.exported_at || "";
  }

  return "";
}

function normalizeHeader(value) {
  return String(value || "")
    .replace(/([a-z])([A-Z])/g, "$1_$2")
    .replace(/\s+/g, "_")
    .toLowerCase();
}

function prettifyHeader(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, function(character) {
      return character.toUpperCase();
    });
}

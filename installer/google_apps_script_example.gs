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

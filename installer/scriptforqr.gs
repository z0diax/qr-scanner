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
      htmlBodyLines.push("<li><strong>" + escapeHtml_(headerStr) + ":</strong> " + escapeHtml_(valueStr) + "</li>");
    }

    htmlBodyLines.push("</ul>");

    var subject = "Your QR Code Registration";

    var plainBody =
      "Hello,\n\n" +
      "Your Participant ID: " + participantId + "\n\n" +
      plainBodyLines.join("\n") + "\n\n" +
      "Your QR code is attached and included in this email.";

    var htmlBody =
      "<p>Hello,</p>" +
      "<p><strong>Your Participant ID: " + escapeHtml_(participantId) + "</strong></p>" +
      htmlBodyLines.join("") +
      '<p><img src="cid:qrcode" style="max-width: 300px;"></p>';

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

function generateParticipantId_(sheet, participantIdCol) {
  var year = new Date().getFullYear();
  var lastRow = sheet.getLastRow();

  var count = 0;

  if (lastRow > 1) {
    var values = sheet.getRange(2, participantIdCol, lastRow - 1, 1).getValues();

    for (var i = 0; i < values.length; i++) {
      var val = values[i][0];
      if (typeof val === "string" && val.indexOf(year + "-") === 0) {
        count++;
      }
    }
  }

  var next = count + 1;
  var padded = ("000" + next).slice(-3);

  return year + "-" + padded;
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
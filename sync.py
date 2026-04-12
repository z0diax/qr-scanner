from __future__ import annotations

import csv
import io
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from database import DatabaseManager


class SyncError(Exception):
    pass


@dataclass
class SyncResult:
    records_synced: int
    synced_at: str


@dataclass
class ExportResult:
    records_exported: int
    exported_at: str
    attendance_date: str


def has_internet(test_url: str = "https://clients3.google.com/generate_204") -> bool:
    request = urllib.request.Request(test_url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5):
            return True
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def sync_users(csv_url: str, database: DatabaseManager) -> SyncResult:
    if not csv_url:
        raise SyncError("Enter a public Google Sheets link or CSV export URL before syncing.")

    normalized_csv_url = _normalize_csv_url(csv_url)
    headers, rows = _download_csv_rows(normalized_csv_url)
    users, id_header = _normalize_rows(headers, rows)
    if not users:
        raise SyncError("No valid user records were found in the CSV file.")

    records_synced = database.replace_users(users, headers, id_header)
    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    database.set_last_sync(synced_at)
    database.set_csv_url(csv_url.strip())
    return SyncResult(records_synced=records_synced, synced_at=synced_at)


def export_attendance_snapshot(
    web_app_url: str,
    database: DatabaseManager,
    attendance_date: str | None = None,
) -> ExportResult:
    if not web_app_url:
        raise SyncError("Enter a Google Apps Script Web App URL before exporting attendance.")

    export_date = attendance_date or datetime.now().strftime("%Y-%m-%d")
    records = database.get_attendance_snapshot(export_date)
    if not records:
        raise SyncError("There are no synced users available to export.")

    exported_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source_headers = database.get_sync_headers()
    export_headers = source_headers + [
        "Attendance",
        "Last Scanned",
        "Manual Override",
        "Attendance Date",
        "Exported At",
    ]
    payload = {
        "mode": "replace_date",
        "attendance_date": export_date,
        "exported_at": exported_at,
        "headers": export_headers,
        "records": [
            _build_export_record(record, source_headers, export_date, exported_at)
            for record in records
        ],
    }

    request = urllib.request.Request(
        web_app_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "QRAttendanceScanner/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        raise SyncError(f"Attendance export failed with HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise SyncError("No internet connection or the export endpoint is unreachable.") from exc

    database.set_export_url(web_app_url)
    database.set_last_export(exported_at)
    return ExportResult(
        records_exported=len(records),
        exported_at=exported_at,
        attendance_date=export_date,
    )


def _build_export_record(
    record: dict[str, str],
    source_headers: list[str],
    attendance_date: str,
    exported_at: str,
) -> dict[str, str]:
    raw_data = record.get("raw_data", {})
    export_record = {
        header: str(raw_data.get(header, "")) if isinstance(raw_data, dict) else ""
        for header in source_headers
    }
    export_record["Attendance"] = str(record.get("attendance_status", ""))
    export_record["Last Scanned"] = str(record.get("last_scanned", ""))
    export_record["Manual Override"] = str(record.get("manual_status", ""))
    export_record["Attendance Date"] = attendance_date
    export_record["Exported At"] = exported_at
    return export_record


def _download_csv_rows(csv_url: str) -> tuple[list[str], list[dict[str, str]]]:
    request = urllib.request.Request(csv_url, headers={"User-Agent": "QRAttendanceScanner/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            content = response.read().decode("utf-8-sig")
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise SyncError(
                "Google Sheets denied access to this file. Set the sheet to "
                "'Anyone with the link' as Viewer, or publish that sheet tab as CSV, then try again."
            ) from exc
        if exc.code == 404:
            raise SyncError("The Google Sheets file or sheet tab could not be found from the pasted link.") from exc
        raise SyncError(f"CSV download failed with HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise SyncError("No internet connection or the CSV link is unreachable.") from exc

    if not content.strip():
        raise SyncError("The downloaded CSV file is empty.")

    sample = content.lstrip()
    if sample.startswith("<!DOCTYPE html") or sample.startswith("<html"):
        raise SyncError("The provided link could not be opened as a public Google Sheets CSV export.")

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise SyncError("The CSV file must contain a header row.")

    headers = [header.strip() for header in reader.fieldnames if header and header.strip()]
    return headers, [dict(row) for row in reader]


def _normalize_csv_url(csv_url: str) -> str:
    normalized_url = csv_url.strip()
    parsed_url = urlparse(normalized_url)
    if parsed_url.scheme not in {"http", "https"}:
        return normalized_url

    if "docs.google.com" not in parsed_url.netloc.lower():
        return normalized_url

    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", parsed_url.path)
    if not match:
        return normalized_url

    spreadsheet_id = match.group(1)
    query_values = parse_qs(parsed_url.query)
    fragment_values = parse_qs(parsed_url.fragment)
    gid = (query_values.get("gid", [""])[0] or fragment_values.get("gid", [""])[0]).strip()

    export_query = {"format": "csv"}
    if gid:
        export_query["gid"] = gid

    return urlunparse(
        (
            "https",
            "docs.google.com",
            f"/spreadsheets/d/{spreadsheet_id}/export",
            "",
            urlencode(export_query),
            "",
        )
    )


def _normalize_rows(
    headers: list[str],
    rows: Iterable[dict[str, str]],
) -> tuple[list[dict[str, str | dict[str, str]]], str]:
    if not headers:
        return [], ""

    id_header = _detect_header(
        headers,
        "id",
        "studentid",
        "student_id",
        "participantid",
        "participant_id",
        "qr",
        "qrvalue",
        "qr_value",
        "userid",
        "user_id",
        "number",
        "code",
    )
    if not id_header:
        id_header = headers[0]

    name_header = _detect_header(
        headers,
        "name",
        "fullname",
        "full_name",
        "studentname",
        "student_name",
    )
    timestamp_header = _detect_header(
        headers,
        "timestamp",
        "updatedat",
        "updated_at",
        "lastupdated",
        "last_updated",
        "date",
    )
    course_header = _detect_header(
        headers,
        "course",
        "program",
        "section",
        "department",
        "batchname",
        "batch_name",
    )

    users: list[dict[str, str | dict[str, str]]] = []
    for row in rows:
        raw_data = {
            header: (row.get(header, "") or "").strip()
            for header in headers
        }
        user_id = raw_data.get(id_header, "").strip()
        if not user_id:
            continue

        name = raw_data.get(name_header, "").strip() if name_header else ""
        timestamp = raw_data.get(timestamp_header, "").strip() if timestamp_header else ""
        course = raw_data.get(course_header, "").strip() if course_header else ""
        users.append(
            {
                "id": user_id,
                "name": name or user_id,
                "course": course,
                "timestamp": timestamp,
                "raw_data": raw_data,
            }
        )
    return users, id_header


def _pick_value(row: dict[str, str], *candidates: str) -> str:
    for candidate in candidates:
        value = row.get(candidate, "")
        if value:
            return value
    return ""


def _normalize_header(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum() or character == "_")


def _detect_header(headers: list[str], *candidates: str) -> str:
    normalized_headers = {
        _normalize_header(header): header
        for header in headers
    }
    for candidate in candidates:
        if candidate in normalized_headers:
            return normalized_headers[candidate]
    return ""

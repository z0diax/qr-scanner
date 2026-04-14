from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable


class DatabaseManager:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    course TEXT DEFAULT '',
                    timestamp TEXT DEFAULT '',
                    raw_data TEXT DEFAULT '{}'
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(users)").fetchall()
            }
            if "raw_data" not in columns:
                connection.execute("ALTER TABLE users ADD COLUMN raw_data TEXT DEFAULT '{}'")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance (
                    id TEXT NOT NULL,
                    time_scanned TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance_override (
                    user_id TEXT NOT NULL,
                    attendance_date TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('Present', 'Absent')),
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, attendance_date)
                )
                """
            )

    def get_user(self, user_id: str) -> dict[str, str] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id, name, course, timestamp, raw_data FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "name": row["name"],
            "course": row["course"],
            "timestamp": row["timestamp"],
            "raw_data": self._load_raw_data(row["raw_data"]),
        }

    def find_user_by_scan_value(self, scan_value: str) -> dict[str, str] | None:
        normalized = scan_value.strip()
        if not normalized:
            return None

        exact_match = self.get_user(normalized)
        if exact_match is not None:
            return exact_match

        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, name, course, timestamp, raw_data
                FROM users
                WHERE ? LIKE id || '%'
                ORDER BY LENGTH(id) DESC
                LIMIT 1
                """,
                (normalized,),
            ).fetchone()

            if row is None:
                    row = connection.execute(
                        """
                    SELECT id, name, course, timestamp, raw_data
                    FROM users
                    WHERE instr(?, id) > 0
                    ORDER BY LENGTH(id) DESC
                    LIMIT 1
                    """,
                    (normalized,),
                ).fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "name": row["name"],
            "course": row["course"],
            "timestamp": row["timestamp"],
            "raw_data": self._load_raw_data(row["raw_data"]),
        }

    def replace_users(
        self,
        users: Iterable[dict[str, str | dict[str, str]]],
        source_headers: list[str],
        id_header: str,
    ) -> int:
        rows = list(users)
        with self.connect() as connection:
            connection.execute("DELETE FROM users")
            connection.executemany(
                """
                INSERT INTO users (id, name, course, timestamp, raw_data)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        str(row["id"]),
                        str(row["name"]),
                        str(row["course"]),
                        str(row["timestamp"]),
                        json.dumps(row["raw_data"], ensure_ascii=True),
                    )
                    for row in rows
                ],
            )
        self.set_sync_headers(source_headers)
        self.set_id_header(id_header)
        return len(rows)

    def clear_local_records(self) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM users")
            connection.execute("DELETE FROM attendance")
            connection.execute("DELETE FROM attendance_override")

        self.set_sync_headers([])
        self.set_id_header("")
        self.set_last_sync("Never")

    def get_users(self, search_text: str = "", attendance_date: str | None = None) -> list[dict[str, str]]:
        scan_date = attendance_date or datetime.now().strftime("%Y-%m-%d")
        search_value = f"%{search_text.strip()}%"
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    users.id,
                    users.name,
                    users.course,
                    users.timestamp,
                    users.raw_data,
                    CASE
                        WHEN attendance_override.status IS NOT NULL THEN attendance_override.status
                        WHEN attendance_today.last_scanned IS NULL THEN 'Absent'
                        ELSE 'Present'
                    END AS attendance_status,
                    COALESCE(attendance_today.last_scanned, '') AS last_scanned,
                    COALESCE(attendance_override.status, '') AS manual_status
                FROM users
                LEFT JOIN (
                    SELECT
                        id,
                        MAX(time_scanned) AS last_scanned
                    FROM attendance
                    WHERE substr(time_scanned, 1, 10) = ?
                    GROUP BY id
                ) AS attendance_today ON attendance_today.id = users.id
                LEFT JOIN attendance_override
                    ON attendance_override.user_id = users.id
                    AND attendance_override.attendance_date = ?
                WHERE
                    users.id LIKE ?
                    OR users.name LIKE ?
                    OR users.course LIKE ?
                    OR users.raw_data LIKE ?
                ORDER BY users.name COLLATE NOCASE ASC, users.id ASC
                """,
                (scan_date, scan_date, search_value, search_value, search_value, search_value),
            ).fetchall()

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "course": row["course"],
                "timestamp": row["timestamp"],
                "raw_data": self._load_raw_data(row["raw_data"]),
                "attendance_status": row["attendance_status"],
                "last_scanned": row["last_scanned"],
                "manual_status": row["manual_status"],
            }
            for row in rows
        ]

    def get_attendance_snapshot(self, attendance_date: str | None = None) -> list[dict[str, str]]:
        return self.get_users("", attendance_date)

    def set_attendance_status(
        self,
        user_id: str,
        status: str,
        attendance_date: str | None = None,
    ) -> None:
        scan_date = attendance_date or datetime.now().strftime("%Y-%m-%d")
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO attendance_override (user_id, attendance_date, status, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, attendance_date)
                DO UPDATE SET
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (user_id, scan_date, status, updated_at),
            )

    def record_attendance(self, user_id: str, scanned_at: str | None = None) -> str:
        timestamp = scanned_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO attendance (id, time_scanned) VALUES (?, ?)",
                (user_id, timestamp),
            )
        return timestamp

    def get_setting(self, key: str, default: str = "") -> str:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def get_last_sync(self) -> str:
        return self.get_setting("last_sync", "Never")

    def set_last_sync(self, value: str) -> None:
        self.set_setting("last_sync", value)

    def get_csv_url(self) -> str:
        return self.get_setting("csv_url", "")

    def set_csv_url(self, value: str) -> None:
        self.set_setting("csv_url", value)

    def get_export_url(self) -> str:
        return self.get_setting("export_url", "")

    def set_export_url(self, value: str) -> None:
        self.set_setting("export_url", value)

    def get_last_export(self) -> str:
        return self.get_setting("last_export", "Never")

    def set_last_export(self, value: str) -> None:
        self.set_setting("last_export", value)

    def get_sync_headers(self) -> list[str]:
        raw_value = self.get_setting("sync_headers", "[]")
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return []
        return [str(value) for value in parsed]

    def set_sync_headers(self, headers: list[str]) -> None:
        self.set_setting("sync_headers", json.dumps(headers, ensure_ascii=True))

    def get_id_header(self) -> str:
        return self.get_setting("id_header", "")

    def set_id_header(self, value: str) -> None:
        self.set_setting("id_header", value)

    def get_attendance_logs(
        self,
        attendance_date: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, str]]:
        """Get attendance logs for a specific date, sorted by time (newest first)."""
        scan_date = attendance_date or datetime.now().strftime("%Y-%m-%d")
        with self.connect() as connection:
            query = """
                SELECT
                    attendance.id,
                    attendance.time_scanned,
                    users.name,
                    users.course,
                    users.raw_data
                FROM attendance
                LEFT JOIN users ON attendance.id = users.id
                WHERE substr(attendance.time_scanned, 1, 10) = ?
                ORDER BY attendance.time_scanned DESC
            """
            if limit:
                query += f" LIMIT {limit}"
            
            rows = connection.execute(query, (scan_date,)).fetchall()
        
        return [
            {
                "id": row["id"],
                "name": row["name"] or "Unknown User",
                "time_scanned": row["time_scanned"],
                "course": row["course"] or "",
                "raw_data": self._load_raw_data(row["raw_data"]),
            }
            for row in rows
        ]

    def get_attendance_for_user_today(self, user_id: str, attendance_date: str | None = None) -> list[dict[str, str]]:
        """Get all scans for a specific user on a specific date."""
        scan_date = attendance_date or datetime.now().strftime("%Y-%m-%d")
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT time_scanned
                FROM attendance
                WHERE id = ? AND substr(time_scanned, 1, 10) = ?
                ORDER BY time_scanned DESC
                """,
                (user_id, scan_date),
            ).fetchall()
        
        return [{"time_scanned": row["time_scanned"]} for row in rows]

    def has_user_scanned_today(self, user_id: str, attendance_date: str | None = None) -> bool:
        """Check if a user has already scanned today."""
        logs = self.get_attendance_for_user_today(user_id, attendance_date)
        return len(logs) > 0

    def get_attendance_stats(self, attendance_date: str | None = None) -> dict[str, int | float]:
        """Get attendance statistics for a specific date."""
        users = self.get_users("", attendance_date)
        total_users = len(users)
        present_users = sum(1 for u in users if u["attendance_status"] == "Present")
        absent_users = total_users - present_users
        rate = (present_users / total_users * 100) if total_users > 0 else 0
        
        return {
            "total": total_users,
            "present": present_users,
            "absent": absent_users,
            "rate": round(rate, 1),
        }

    def _load_raw_data(self, raw_value: str | None) -> dict[str, str]:
        if not raw_value:
            return {}
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return {}
        return {
            str(key): str(value) if value is not None else ""
            for key, value in parsed.items()
        }

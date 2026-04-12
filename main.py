from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QStyleFactory

from database import DatabaseManager
from ui import MainWindow


def get_app_data_dir() -> Path:
    if os.name == "nt":
        base_dir = Path(os.getenv("LOCALAPPDATA", Path.home()))
        app_dir = base_dir / "QRAttendanceScanner"
    else:
        app_dir = Path.home() / ".qr_attendance_scanner"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("QR Attendance Scanner")
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setFont(QFont("Segoe UI", 10))

    database = DatabaseManager(get_app_data_dir() / "attendance.db")
    database.initialize()

    window = MainWindow(database)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

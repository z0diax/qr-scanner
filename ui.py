from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent, QColor, QDesktopServices, QImage, QPixmap, QResizeEvent
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from database import DatabaseManager
from scanner import QRScannerThread
from sync import ExportResult, SyncError, SyncResult, export_attendance_snapshot, has_internet, sync_users


class SyncWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    online_checked = Signal(bool)

    def __init__(self, database: DatabaseManager, csv_url: str) -> None:
        super().__init__()
        self.database = database
        self.csv_url = csv_url

    @Slot()
    def run(self) -> None:
        online = has_internet()
        self.online_checked.emit(online)
        if not online:
            self.failed.emit("No internet connection. Sync requires an active connection.")
            return

        try:
            result = sync_users(self.csv_url, self.database)
        except SyncError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover
            self.failed.emit(f"Unexpected sync error: {exc}")
        else:
            self.finished.emit(result)


class ExportWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    online_checked = Signal(bool)

    def __init__(self, database: DatabaseManager, web_app_url: str) -> None:
        super().__init__()
        self.database = database
        self.web_app_url = web_app_url

    @Slot()
    def run(self) -> None:
        online = has_internet()
        self.online_checked.emit(online)
        if not online:
            self.failed.emit("No internet connection. Export requires an active connection.")
            return

        try:
            result = export_attendance_snapshot(self.web_app_url, self.database)
        except SyncError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover
            self.failed.emit(f"Unexpected export error: {exc}")
        else:
            self.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self, database: DatabaseManager) -> None:
        super().__init__()
        self.database = database
        self.scanner_thread: QRScannerThread | None = None
        self.sync_thread: QThread | None = None
        self.sync_worker: SyncWorker | None = None
        self.export_thread: QThread | None = None
        self.export_worker: ExportWorker | None = None
        self.online_status = False
        self._updating_user_table = False
        self.sheet_headers: list[str] = []
        self.attendance_column_index = 0
        self.last_scanned_column_index = 1
        self._latest_preview_image: QImage | None = None

        self.setWindowTitle("QR Attendance Scanner")
        self.resize(1360, 860)
        self.camera_tab_index = 0
        self.users_tab_index = 1
        self.status_tab_index = 2
        self.sync_tab_index = 3

        self._build_ui()
        self._apply_styles()
        self._load_saved_settings()
        self._set_status_message("Local attendance database ready.")
        self._refresh_status_label()
        self.refresh_user_table()

    def _build_ui(self) -> None:
        container = QWidget()
        container.setObjectName("mainContainer")
        root_layout = QHBoxLayout(container)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(14)

        root_layout.addWidget(self._build_app_sidebar(), 0)

        content_shell = QWidget()
        content_shell.setObjectName("mainContentShell")
        content_layout = QVBoxLayout(content_shell)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        self.tabs = QStackedWidget()
        self.tabs.setObjectName("workspaceStack")
        self.tabs.addWidget(self._build_camera_tab())
        self.tabs.addWidget(self._build_users_tab())
        self.tabs.addWidget(self._build_status_tab())
        self.tabs.addWidget(self._build_sync_tab())
        content_layout.addWidget(self.tabs, 1)

        root_layout.addWidget(content_shell, 1)
        self._set_sidebar_index(self.camera_tab_index)

        self.setCentralWidget(container)

        self.start_button.clicked.connect(self.start_scan)
        self.stop_button.clicked.connect(self.stop_scan)
        self.sync_button.clicked.connect(self.sync_data)
        self.export_button.clicked.connect(self.export_attendance)
        self.delete_local_records_button.clicked.connect(self.delete_local_records)
        self.open_csv_url_button.clicked.connect(self.open_csv_url)
        self.test_csv_url_button.clicked.connect(self.sync_data)
        self.open_export_url_button.clicked.connect(self.open_export_url)
        self.test_export_url_button.clicked.connect(self.export_attendance)
        self.search_input.textChanged.connect(self.refresh_user_table)
        self.user_table.itemChanged.connect(self._handle_user_table_item_changed)

    def _build_camera_toolbar(self) -> QFrame:
        hero = QFrame()
        hero.setObjectName("cameraToolbar")
        layout = QVBoxLayout(hero)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        title_column = QVBoxLayout()
        title_column.setSpacing(0)

        title_label = QLabel("Camera")
        title_label.setObjectName("pageTitle")

        title_column.addWidget(title_label)

        self.network_badge = QLabel("OFFLINE")
        self.network_badge.setObjectName("offlineBadge")
        self.network_badge.setAlignment(Qt.AlignCenter)
        self.network_badge.setFixedHeight(34)
        self.network_badge.setMinimumWidth(126)

        top_row.addLayout(title_column, 1)
        top_row.addWidget(self.network_badge, 0, Qt.AlignTop)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.start_button = QPushButton("Start Scan")
        self.start_button.setObjectName("primaryButton")
        self.stop_button = QPushButton("Stop Scan")
        self.stop_button.setObjectName("ghostButton")
        self.stop_button.setEnabled(False)

        action_row.addWidget(self.start_button)
        action_row.addWidget(self.stop_button)
        action_row.addStretch()

        layout.addLayout(top_row)
        layout.addLayout(action_row)
        return hero

    def _build_preview_panel(self) -> QFrame:
        panel = self._create_card("Camera", "")
        layout = panel.layout()
        assert isinstance(layout, QVBoxLayout)

        signal_row = QHBoxLayout()
        signal_row.setSpacing(12)

        self.camera_state_chip = QLabel("CAMERA IDLE")
        self.camera_state_chip.setObjectName("subtleChip")
        self.camera_state_chip.setAlignment(Qt.AlignCenter)

        signal_row.addWidget(self.camera_state_chip)
        signal_row.addStretch()

        self.preview_label = QLabel("Camera preview will appear here.")
        self.preview_label.setObjectName("previewPanel")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(500)
        self.preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.preview_label.setWordWrap(True)

        layout.addLayout(signal_row)
        layout.addWidget(self.preview_label, 1)
        return panel

    def _build_app_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("appSidebar")
        sidebar.setFixedWidth(214)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(14)

        brand_card = QFrame()
        brand_card.setObjectName("sidebarBrand")
        brand_layout = QVBoxLayout(brand_card)
        brand_layout.setContentsMargins(14, 14, 14, 14)
        brand_layout.setSpacing(4)

        brand_title = QLabel("QR Scanner")
        brand_title.setObjectName("sidebarTitle")
        brand_layout.addWidget(brand_title)
        layout.addWidget(brand_card)

        self.camera_nav_button = self._create_nav_button("Camera", self.camera_tab_index)
        self.users_nav_button = self._create_nav_button("Synced Users", self.users_tab_index)
        self.status_nav_button = self._create_nav_button("System Status", self.status_tab_index)
        self.sync_nav_button = self._create_nav_button("Data Sources", self.sync_tab_index)

        for button in (
            self.camera_nav_button,
            self.users_nav_button,
            self.status_nav_button,
            self.sync_nav_button,
        ):
            layout.addWidget(button)

        layout.addStretch()
        return sidebar

    def _build_camera_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(self._build_camera_toolbar())
        workspace_splitter = QSplitter(Qt.Horizontal)
        workspace_splitter.setChildrenCollapsible(False)
        workspace_splitter.addWidget(self._build_preview_panel())

        details_column = QWidget()
        details_column.setMinimumWidth(300)
        details_column.setMaximumWidth(360)
        details_layout = QVBoxLayout(details_column)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(12)

        scan_card = self._create_card("Scan Details", "")
        scan_card_layout = scan_card.layout()
        assert isinstance(scan_card_layout, QVBoxLayout)

        self.result_label = self._create_value_label("Waiting for scan...")
        self.user_info_label = self._create_value_label("No local record loaded.")
        self.result_label.setMinimumHeight(72)
        self.user_info_label.setMinimumHeight(140)

        scan_card_layout.addWidget(self._create_field("Scanned Result", self.result_label))
        scan_card_layout.addWidget(self._create_field("Matched Record", self.user_info_label))

        details_layout.addWidget(scan_card)
        details_layout.addStretch()

        workspace_splitter.addWidget(details_column)
        workspace_splitter.setStretchFactor(0, 6)
        workspace_splitter.setStretchFactor(1, 2)

        layout.addWidget(workspace_splitter, 1)
        return page

    def _build_users_tab(self) -> QWidget:
        page = self._create_card("Synced Users", "")
        layout = page.layout()
        assert isinstance(layout, QVBoxLayout)
        layout.setSpacing(12)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)

        self.sync_button = QPushButton("Sync Sheet")
        self.sync_button.setObjectName("accentButton")
        self.export_button = QPushButton("Export Attendance")
        self.export_button.setObjectName("secondaryButton")
        self.delete_local_records_button = QPushButton("Delete Local Records")
        self.delete_local_records_button.setObjectName("dangerButton")

        actions_row.addWidget(self.sync_button)
        actions_row.addWidget(self.export_button)
        actions_row.addWidget(self.delete_local_records_button)
        actions_row.addStretch()

        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)

        self.synced_count_tile, self.synced_count_value = self._create_stat_tile("Synced Rows", "0")
        self.present_count_tile, self.present_count_value = self._create_stat_tile("Present Today", "0")
        self.columns_count_tile, self.columns_count_value = self._create_stat_tile("Sheet Columns", "0")
        self.source_state_tile, self.source_state_value = self._create_stat_tile("Activity", "Idle")

        for widget in (
            self.synced_count_tile,
            self.present_count_tile,
            self.columns_count_tile,
            self.source_state_tile,
        ):
            stats_row.addWidget(widget, 1)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search across the synced sheet data")

        self.user_table = QTableWidget(0, 0)
        self.user_table.setObjectName("userTable")
        self.user_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.user_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.user_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.user_table.verticalHeader().setVisible(False)
        self.user_table.horizontalHeader().setStretchLastSection(False)
        self.user_table.setAlternatingRowColors(True)

        layout.addLayout(actions_row)
        layout.addLayout(stats_row)
        layout.addWidget(self.search_input)
        layout.addWidget(self.user_table, 1)
        return page

    def _build_status_tab(self) -> QWidget:
        page = self._create_card("System Status", "")
        layout = page.layout()
        assert isinstance(layout, QVBoxLayout)
        layout.setSpacing(12)

        self.status_label = self._create_value_label("")
        self.status_message_label = QLabel("")
        self.status_message_label.setObjectName("statusMessage")
        self.status_message_label.setWordWrap(True)

        layout.addWidget(self._create_field("Status Snapshot", self.status_label))
        layout.addWidget(self._create_field("Recent Activity", self.status_message_label))
        layout.addStretch()
        return page

    def _build_sync_tab(self) -> QWidget:
        page = self._create_card("Data Sources", "")
        layout = page.layout()
        assert isinstance(layout, QVBoxLayout)
        layout.setSpacing(14)

        self.csv_url_input = QLineEdit()
        self.csv_url_input.setPlaceholderText("Paste the normal Google Sheets link or a CSV export URL")
        self.export_url_input = QLineEdit()
        self.export_url_input.setPlaceholderText("https://script.google.com/macros/s/.../exec")

        self.open_csv_url_button = QToolButton()
        self.open_csv_url_button.setText("Open")
        self.open_csv_url_button.setObjectName("linkButton")
        self.test_csv_url_button = QPushButton("Sync Now")
        self.test_csv_url_button.setObjectName("accentButton")
        self.csv_loader_label = QLabel("Idle")
        self.csv_loader_label.setObjectName("loaderLabel")

        self.open_export_url_button = QToolButton()
        self.open_export_url_button.setText("Open")
        self.open_export_url_button.setObjectName("linkButton")
        self.test_export_url_button = QPushButton("Export Now")
        self.test_export_url_button.setObjectName("secondaryButton")
        self.export_loader_label = QLabel("Idle")
        self.export_loader_label.setObjectName("loaderLabel")

        layout.addWidget(
            self._create_data_source_field(
                "Google Sheets Link or CSV URL",
                self.csv_url_input,
                self.open_csv_url_button,
                self.test_csv_url_button,
                self.csv_loader_label,
            )
        )
        layout.addWidget(
            self._create_data_source_field(
                "Google Apps Script Export URL",
                self.export_url_input,
                self.open_export_url_button,
                self.test_export_url_button,
                self.export_loader_label,
            )
        )
        layout.addStretch()
        return page

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow { background: #ebe7de; }
            QWidget#mainContainer {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #f5f1e8,
                    stop: 1 #e8e2d7
                );
                color: #18272b;
            }
            QSplitter::handle { background: transparent; width: 10px; }
            QLabel { color: #1c2e33; }
            QWidget#mainContentShell {
                background: transparent;
            }
            QFrame#appSidebar {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #14343a,
                    stop: 1 #10292f
                );
                border: 1px solid #18363c;
                border-radius: 24px;
            }
            QFrame#sidebarBrand {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 18px;
            }
            QFrame#cameraToolbar {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #14343a,
                    stop: 0.55 #1b4850,
                    stop: 1 #245965
                );
                border: 1px solid #20454c;
                border-radius: 26px;
            }
            QLabel#pageTitle { color: #f7f1e7; font-size: 26px; font-weight: 700; }
            QLabel#onlineBadge, QLabel#offlineBadge {
                border-radius: 17px;
                padding: 0 16px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
                min-width: 110px;
            }
            QLabel#onlineBadge {
                background: #dff0d8;
                color: #1d6a47;
                border: 1px solid #8ebf9b;
            }
            QLabel#offlineBadge {
                background: #f5dfd4;
                color: #9b4e29;
                border: 1px solid #e8b59c;
            }
            QFrame#statTile {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
            }
            QLabel#statCaption {
                color: #bed2cf;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.8px;
                text-transform: uppercase;
            }
            QLabel#statValue {
                color: #fff7ed;
                font-size: 24px;
                font-weight: 700;
            }
            QFrame[card="true"] {
                background: rgba(255, 252, 247, 0.96);
                border: 1px solid #d8d0c4;
                border-radius: 22px;
            }
            QLabel[cardTitle="true"] { color: #183238; font-size: 20px; font-weight: 700; }
            QLabel[cardSubtitle="true"] { color: #6d7b7f; font-size: 12px; }
            QLabel#previewPanel {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #0f262b,
                    stop: 0.45 #16353a,
                    stop: 1 #20484e
                );
                border: 1px solid #24484e;
                border-radius: 18px;
                color: #f7f2ea;
                font-size: 18px;
                font-weight: 600;
                padding: 0px;
            }
            QLabel#subtleChip {
                background: #f3ebde;
                border: 1px solid #ddd2c2;
                border-radius: 14px;
                padding: 8px 12px;
                color: #42575d;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.7px;
            }
            QLabel#mutedText, QLabel#tabSummary { color: #76858a; font-size: 12px; }
            QStackedWidget#workspaceStack {
                background: transparent;
            }
            QLabel#sidebarTitle {
                color: #f6efe5;
                font-size: 24px;
                font-weight: 700;
            }
            QPushButton#navButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 16px;
                color: #c6d9d7;
                padding: 14px 14px;
                text-align: left;
                font-size: 13px;
                font-weight: 700;
                min-width: 140px;
                min-height: 20px;
            }
            QPushButton#navButton:hover {
                background: rgba(255, 255, 255, 0.08);
                color: #fff6ea;
            }
            QPushButton#navButton:checked {
                background: #f6f0e6;
                border: 1px solid #f6f0e6;
                color: #17343a;
            }
            QLabel#fieldLabel {
                color: #62757b;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.8px;
                text-transform: uppercase;
            }
            QLabel#valueLabel {
                background: #f8f5ef;
                border: 1px solid #ddd4c7;
                border-radius: 16px;
                padding: 14px 16px;
                color: #183238;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel#loaderLabel {
                color: #62757b;
                font-size: 12px;
                font-weight: 700;
            }
            QLabel#statusMessage {
                background: #fff3dd;
                border: 1px solid #ebd39b;
                border-radius: 16px;
                padding: 14px 16px;
                color: #765720;
                font-size: 13px;
            }
            QLineEdit {
                background: #fcfbf7;
                border: 1px solid #d7cec2;
                border-radius: 14px;
                padding: 10px 12px;
                color: #173338;
                font-size: 13px;
                selection-background-color: #214e55;
                min-height: 18px;
            }
            QLineEdit:focus { border: 2px solid #214e55; }
            QPushButton {
                border-radius: 14px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 700;
                min-height: 20px;
            }
            QPushButton#primaryButton {
                background: #f6f1e6;
                border: 1px solid #efe2c8;
                color: #17343a;
            }
            QPushButton#primaryButton:hover { background: #fff8eb; }
            QPushButton#secondaryButton {
                background: #c28f33;
                border: 1px solid #c28f33;
                color: #1d1811;
            }
            QPushButton#secondaryButton:hover { background: #ae7d29; }
            QPushButton#dangerButton {
                background: #9f4032;
                border: 1px solid #9f4032;
                color: #fff4ef;
            }
            QPushButton#dangerButton:hover { background: #873629; }
            QPushButton#accentButton {
                background: #1b4f56;
                border: 1px solid #1b4f56;
                color: #f8f2ea;
            }
            QPushButton#accentButton:hover { background: #153f45; }
            QToolButton#linkButton {
                background: #f6f1e6;
                border: 1px solid #d7cec2;
                border-radius: 14px;
                color: #17343a;
                padding: 10px 14px;
                font-size: 12px;
                font-weight: 700;
                min-height: 20px;
            }
            QToolButton#linkButton:hover { background: #fff8eb; }
            QPushButton#ghostButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                color: #f7f1e7;
            }
            QPushButton#ghostButton:hover { background: rgba(255, 255, 255, 0.14); }
            QPushButton:disabled {
                background: #ddd6ca;
                border: 1px solid #ddd6ca;
                color: #8e9b9f;
            }
            QTableWidget#userTable {
                background: #fcfbf7;
                alternate-background-color: #f4efe7;
                border: 1px solid #ddd5c8;
                border-radius: 16px;
                gridline-color: #ece4d9;
                color: #173338;
                font-size: 13px;
            }
            QTableWidget::item { padding: 8px; }
            QHeaderView::section {
                background: #efe6d8;
                color: #274247;
                border: none;
                border-right: 1px solid #ddd3c6;
                border-bottom: 1px solid #ddd3c6;
                padding: 10px 8px;
                font-size: 12px;
                font-weight: 700;
            }
            """
        )

    def _create_card(self, title: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setProperty("card", True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setProperty("cardTitle", True)

        layout.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setProperty("cardSubtitle", True)
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)
        return card

    def _create_field(self, title: str, widget: QWidget) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(title)
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        layout.addWidget(widget)
        return wrapper

    def _create_data_source_field(
        self,
        title: str,
        input_widget: QWidget,
        open_button: QWidget,
        action_button: QWidget,
        loader_label: QLabel,
    ) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        label = QLabel(title)
        label.setObjectName("fieldLabel")

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(8)
        action_row.addWidget(input_widget, 1)
        action_row.addWidget(open_button)
        action_row.addWidget(action_button)

        layout.addWidget(label)
        layout.addLayout(action_row)
        layout.addWidget(loader_label, 0, Qt.AlignRight)
        return wrapper

    def _create_nav_button(self, label: str, index: int) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName("navButton")
        button.setCheckable(True)
        button.clicked.connect(lambda checked=False, target=index: self._set_sidebar_index(target))
        return button

    def _create_value_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("valueLabel")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        label.setMinimumHeight(76)
        return label

    def _create_stat_tile(self, caption: str, value: str) -> tuple[QFrame, QLabel]:
        tile = QFrame()
        tile.setObjectName("statTile")
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        caption_label = QLabel(caption)
        caption_label.setObjectName("statCaption")
        value_label = QLabel(value)
        value_label.setObjectName("statValue")

        layout.addWidget(caption_label)
        layout.addWidget(value_label)
        return tile, value_label

    def _load_saved_settings(self) -> None:
        self.csv_url_input.setText(self.database.get_csv_url())
        self.export_url_input.setText(self.database.get_export_url())

    @Slot()
    def refresh_user_table(self) -> None:
        if not hasattr(self, "user_table"):
            return

        self.sheet_headers = self.database.get_sync_headers()
        display_headers = self.sheet_headers + ["Attendance", "Last Scanned"]
        self.attendance_column_index = len(self.sheet_headers)
        self.last_scanned_column_index = len(self.sheet_headers) + 1

        self.user_table.clear()
        self.user_table.setColumnCount(len(display_headers))
        self.user_table.setHorizontalHeaderLabels(display_headers)
        self._configure_user_table_columns()

        users = self.database.get_users(self.search_input.text())
        self._updating_user_table = True
        self.user_table.setRowCount(len(users))

        present_count = 0
        for row_index, user in enumerate(users):
            attendance_item = QTableWidgetItem()
            last_scanned_item = QTableWidgetItem(str(user["last_scanned"]))
            raw_data = user.get("raw_data", {})

            for column_index, header in enumerate(self.sheet_headers):
                value = ""
                if isinstance(raw_data, dict):
                    value = str(raw_data.get(header, ""))
                self.user_table.setItem(row_index, column_index, QTableWidgetItem(value))

            attendance_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
            attendance_item.setData(Qt.UserRole, str(user["id"]))
            attendance_item.setCheckState(
                Qt.Checked if str(user["attendance_status"]) == "Present" else Qt.Unchecked
            )
            attendance_text = "Present"
            if str(user["attendance_status"]) == "Absent":
                attendance_text = "Absent"
            if str(user["manual_status"]):
                attendance_text += " (Manual)"
            attendance_item.setText(attendance_text)

            if user["attendance_status"] == "Present":
                attendance_item.setForeground(Qt.darkGreen)
                present_count += 1
            else:
                attendance_item.setForeground(Qt.darkRed)

            self.user_table.setItem(row_index, self.attendance_column_index, attendance_item)
            self.user_table.setItem(row_index, self.last_scanned_column_index, last_scanned_item)

        self._updating_user_table = False
        self.synced_count_value.setText(str(len(users)))
        self.present_count_value.setText(str(present_count))
        self.columns_count_value.setText(str(len(self.sheet_headers)))

    def start_scan(self) -> None:
        if self.scanner_thread and self.scanner_thread.isRunning():
            return

        self.scanner_thread = QRScannerThread()
        self.scanner_thread.frame_ready.connect(self._update_preview)
        self.scanner_thread.qr_detected.connect(self._handle_qr_detected)
        self.scanner_thread.error.connect(self._handle_scanner_error)
        self.scanner_thread.camera_state_changed.connect(self._handle_camera_state)
        self.scanner_thread.finished.connect(self._clear_scanner_reference)
        self.scanner_thread.start()

        self.result_label.setText("Scanner starting...")
        self.user_info_label.setText("Ready to scan a registered QR code.")
        self._set_status_message("Camera initialization in progress.")
        self.camera_state_chip.setText("CAMERA STARTING")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self._set_sidebar_index(self.camera_tab_index)

    def stop_scan(self) -> None:
        if not self.scanner_thread:
            return

        self.scanner_thread.stop()
        self._latest_preview_image = None
        self.preview_label.clear()
        self.preview_label.setText("Camera stopped.")
        self.result_label.setText("Scanner stopped.")
        self._set_status_message("Scanner paused. You can restart the camera at any time.")
        self.camera_state_chip.setText("CAMERA IDLE")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def sync_data(self) -> None:
        if self.sync_thread and self.sync_thread.isRunning():
            return

        csv_url = self.csv_url_input.text().strip()
        if not csv_url:
            self._show_styled_warning(
                "Missing CSV URL",
                "Enter a public Google Sheets link or CSV export URL before syncing.",
            )
            return

        self.sync_button.setEnabled(False)
        self.test_csv_url_button.setEnabled(False)
        self.csv_loader_label.setText("Syncing...")
        self._set_status_message("Checking connection and preparing the Google Sheets sync.")
        self._refresh_status_label()
        self._set_sidebar_index(self.sync_tab_index)

        self.sync_thread = QThread(self)
        self.sync_worker = SyncWorker(self.database, csv_url)
        self.sync_worker.moveToThread(self.sync_thread)

        self.sync_thread.started.connect(self.sync_worker.run)
        self.sync_worker.online_checked.connect(self._set_online_status)
        self.sync_worker.finished.connect(self._on_sync_finished)
        self.sync_worker.failed.connect(self._on_sync_failed)
        self.sync_worker.finished.connect(self.sync_thread.quit)
        self.sync_worker.failed.connect(self.sync_thread.quit)
        self.sync_worker.finished.connect(self.sync_worker.deleteLater)
        self.sync_worker.failed.connect(self.sync_worker.deleteLater)
        self.sync_thread.finished.connect(self.sync_thread.deleteLater)
        self.sync_thread.finished.connect(self._cleanup_sync_thread)
        self.sync_thread.start()

    def export_attendance(self) -> None:
        if self.export_thread and self.export_thread.isRunning():
            return

        web_app_url = self.export_url_input.text().strip()
        if not web_app_url:
            self._show_styled_warning(
                "Missing Export URL",
                "Enter a Google Apps Script Web App URL before exporting attendance.",
            )
            return

        self.export_button.setEnabled(False)
        self.test_export_url_button.setEnabled(False)
        self.export_loader_label.setText("Exporting...")
        self._set_status_message("Preparing the attendance export for Google Sheets.")
        self._refresh_status_label()
        self._set_sidebar_index(self.sync_tab_index)

        self.export_thread = QThread(self)
        self.export_worker = ExportWorker(self.database, web_app_url)
        self.export_worker.moveToThread(self.export_thread)

        self.export_thread.started.connect(self.export_worker.run)
        self.export_worker.online_checked.connect(self._set_online_status)
        self.export_worker.finished.connect(self._on_export_finished)
        self.export_worker.failed.connect(self._on_export_failed)
        self.export_worker.finished.connect(self.export_thread.quit)
        self.export_worker.failed.connect(self.export_thread.quit)
        self.export_worker.finished.connect(self.export_worker.deleteLater)
        self.export_worker.failed.connect(self.export_worker.deleteLater)
        self.export_thread.finished.connect(self.export_thread.deleteLater)
        self.export_thread.finished.connect(self._cleanup_export_thread)
        self.export_thread.start()

    def delete_local_records(self) -> None:
        confirmed = self._show_styled_question(
            "Delete Local Records",
            (
                "Delete all locally synced users, saved attendance logs, and manual attendance overrides?\n\n"
                "Saved Google Sheets URLs will be kept so you can sync again later."
            ),
        )
        if not confirmed:
            return

        self.database.clear_local_records()
        self.result_label.setText("Waiting for scan...")
        self.user_info_label.setText("No local record loaded.")
        self._set_status_message("Local synced records were deleted. Sync a sheet to load a new roster.")
        self._refresh_status_label()
        self.refresh_user_table()
        self._set_sidebar_index(self.users_tab_index)
        self._show_styled_info(
            "Local Records Deleted",
            "The local synced roster and attendance data were removed successfully.",
        )

    def open_csv_url(self) -> None:
        url = self.csv_url_input.text().strip()
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def open_export_url(self) -> None:
        url = self.export_url_input.text().strip()
        if url:
            QDesktopServices.openUrl(QUrl(url))

    @Slot(QImage)
    def _update_preview(self, image: QImage) -> None:
        self._latest_preview_image = image
        self._render_preview()

    def _render_preview(self) -> None:
        if self._latest_preview_image is None:
            return

        target_size = self.preview_label.size()
        if not target_size.isValid() or target_size.width() <= 0 or target_size.height() <= 0:
            return

        pixmap = QPixmap.fromImage(self._latest_preview_image)
        scaled = pixmap.scaled(
            target_size,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        x_offset = max(0, (scaled.width() - target_size.width()) // 2)
        y_offset = max(0, (scaled.height() - target_size.height()) // 2)
        cropped = scaled.copy(x_offset, y_offset, target_size.width(), target_size.height())
        self.preview_label.setPixmap(cropped)

    @Slot(str)
    def _handle_qr_detected(self, qr_value: str) -> None:
        self.result_label.setText(qr_value)
        user = self.database.find_user_by_scan_value(qr_value)
        if user is None:
            self.user_info_label.setText("Not Registered")
            self._set_status_message("The scanned QR code could not be matched to any registered ID in the local database.")
            self._set_sidebar_index(self.camera_tab_index)
            return

        scanned_at = self.database.record_attendance(user["id"])
        self.user_info_label.setText(self._format_user_info(user, scanned_at))
        self._set_status_message("Attendance recorded successfully in the offline database.")
        self.refresh_user_table()
        self._set_sidebar_index(self.camera_tab_index)

    @Slot(str)
    def _handle_scanner_error(self, message: str) -> None:
        self.result_label.setText(message)
        if message == "Camera not available.":
            self.user_info_label.setText("Check if the webcam is connected and not being used by another app.")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self._latest_preview_image = None
            self.preview_label.clear()
            self.preview_label.setText("Camera preview unavailable.")
            self.camera_state_chip.setText("CAMERA ERROR")
        elif message == "Invalid QR code data.":
            self.user_info_label.setText("The QR content could not be decoded into a valid ID.")
        self._set_status_message(message)
        self._set_sidebar_index(self.status_tab_index)

    @Slot(bool)
    def _handle_camera_state(self, active: bool) -> None:
        self.start_button.setEnabled(not active)
        self.stop_button.setEnabled(active)
        self.camera_state_chip.setText("CAMERA LIVE" if active else "CAMERA IDLE")
        if active:
            self._set_status_message("Camera is live and ready for scanning.")

    @Slot(bool)
    def _set_online_status(self, online: bool) -> None:
        self.online_status = online
        self._refresh_status_label()

    @Slot(object)
    def _on_sync_finished(self, result: SyncResult) -> None:
        self.online_status = True
        self._refresh_status_label(records_synced=result.records_synced)
        self._set_status_message(f"Sync completed successfully at {result.synced_at}.")
        self.refresh_user_table()
        self._set_sidebar_index(self.status_tab_index)
        self._show_styled_info(
            "Sync Complete",
            f"Downloaded {result.records_synced} user records from Google Sheets.",
        )

    @Slot(str)
    def _on_sync_failed(self, message: str) -> None:
        if "No internet" in message or "unreachable" in message:
            self.online_status = False
        self._refresh_status_label()
        self._set_status_message(message)
        self._set_sidebar_index(self.status_tab_index)
        self._show_styled_warning("Sync Failed", message)

    @Slot(object)
    def _on_export_finished(self, result: ExportResult) -> None:
        self.online_status = True
        self._refresh_status_label(records_exported=result.records_exported)
        self._set_status_message(
            f"Attendance export completed at {result.exported_at} for {result.attendance_date}."
        )
        self._set_sidebar_index(self.status_tab_index)
        self._show_styled_info(
            "Export Complete",
            f"Exported {result.records_exported} attendance rows to Google Sheets.",
        )

    @Slot(str)
    def _on_export_failed(self, message: str) -> None:
        if "No internet" in message or "unreachable" in message:
            self.online_status = False
        self._refresh_status_label()
        self._set_status_message(message)
        self._set_sidebar_index(self.status_tab_index)
        self._show_styled_warning("Export Failed", message)

    def _refresh_status_label(
        self,
        records_synced: int | None = None,
        records_exported: int | None = None,
    ) -> None:
        state = "Online" if self.online_status else "Offline"
        status_lines = [
            f"Connection: {state}",
            f"Last Sync: {self.database.get_last_sync()}",
            f"Last Export: {self.database.get_last_export()}",
        ]
        if records_synced is not None:
            status_lines.append(f"Records Synced: {records_synced}")
        if records_exported is not None:
            status_lines.append(f"Records Exported: {records_exported}")
        self.status_label.setText("\n".join(status_lines))

        self.network_badge.setText(state.upper())
        self.network_badge.setObjectName("onlineBadge" if self.online_status else "offlineBadge")
        self.style().unpolish(self.network_badge)
        self.style().polish(self.network_badge)

    def _set_status_message(self, message: str) -> None:
        self.status_message_label.setText(message)
        short_message = message[:42] + ("..." if len(message) > 42 else "")
        self.source_state_value.setText(short_message or "Idle")

    def _show_styled_info(self, title: str, message: str, text_color: str = "#00FF00") -> None:
        """Show a styled info message box with custom text color.
        
        Args:
            title: Dialog title
            message: Dialog message
            text_color: Text color (hex or color name). Default: green (#00FF00)
        """
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStyleSheet(f"QMessageBox {{ color: {text_color}; }} QMessageBox QLabel {{ color: {text_color}; }}")
        msg_box.exec()

    def _show_styled_warning(self, title: str, message: str, text_color: str = "#FFFF00") -> None:
        """Show a styled warning message box with custom text color.
        
        Args:
            title: Dialog title
            message: Dialog message
            text_color: Text color (hex or color name). Default: yellow (#FFFF00)
        """
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStyleSheet(f"QMessageBox {{ color: {text_color}; }} QMessageBox QLabel {{ color: {text_color}; }}")
        msg_box.exec()

    def _show_styled_question(self, title: str, message: str, text_color: str = "#FFFFFF") -> bool:
        """Show a styled question message box with custom text color.
        
        Args:
            title: Dialog title
            message: Dialog message
            text_color: Text color (hex or color name). Default: white (#FFFFFF)
            
        Returns:
            True if user clicked Yes, False if user clicked No
        """
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        msg_box.setStyleSheet(f"QMessageBox {{ color: {text_color}; }} QMessageBox QLabel {{ color: {text_color}; }}")
        return msg_box.exec() == QMessageBox.Yes

    def _set_sidebar_index(self, index: int) -> None:
        self.tabs.setCurrentIndex(index)
        buttons = (
            self.camera_nav_button,
            self.users_nav_button,
            self.status_nav_button,
            self.sync_nav_button,
        )
        for button_index, button in enumerate(buttons):
            button.setChecked(button_index == index)

    @Slot(QTableWidgetItem)
    def _handle_user_table_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating_user_table or item.column() != self.attendance_column_index:
            return

        user_id = item.data(Qt.UserRole)
        if not user_id:
            return

        status = "Present" if item.checkState() == Qt.Checked else "Absent"
        self._updating_user_table = True
        item.setText(f"{status} (Manual)")
        item.setForeground(Qt.darkGreen if status == "Present" else Qt.darkRed)
        self._updating_user_table = False
        self.database.set_attendance_status(str(user_id), status)
        self._set_status_message(
            f"Manual attendance override saved: user ID {user_id} marked {status.lower()} for today."
        )

    def _configure_user_table_columns(self) -> None:
        header = self.user_table.horizontalHeader()
        if not self.sheet_headers:
            return

        for column_index, header_name in enumerate(self.sheet_headers):
            normalized = header_name.strip().lower()
            if "name" in normalized or "email" in normalized or "address" in normalized:
                header.setSectionResizeMode(column_index, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(column_index, QHeaderView.ResizeToContents)

        header.setSectionResizeMode(self.attendance_column_index, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.last_scanned_column_index, QHeaderView.ResizeToContents)

    def _format_user_info(self, user: dict[str, str], scanned_at: str) -> str:
        raw_data = user.get("raw_data", {})
        lines: list[str] = []
        if isinstance(raw_data, dict) and raw_data:
            for key, value in raw_data.items():
                if value:
                    lines.append(f"{key}: {value}")
        else:
            lines.append(f"ID: {user['id']}")
            lines.append(f"Name: {user['name']}")
            if user["course"]:
                lines.append(f"Course: {user['course']}")
        lines.append(f"Attendance saved at {scanned_at}")
        return "\n".join(lines)

    @Slot()
    def _cleanup_sync_thread(self) -> None:
        self.sync_thread = None
        self.sync_worker = None
        self.sync_button.setEnabled(True)
        self.test_csv_url_button.setEnabled(True)
        self.csv_loader_label.setText("Idle")

    @Slot()
    def _cleanup_export_thread(self) -> None:
        self.export_thread = None
        self.export_worker = None
        self.export_button.setEnabled(True)
        self.test_export_url_button.setEnabled(True)
        self.export_loader_label.setText("Idle")

    @Slot()
    def _clear_scanner_reference(self) -> None:
        self.scanner_thread = None

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._render_preview()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.stop_scan()
        if self.sync_thread and self.sync_thread.isRunning():
            self.sync_thread.quit()
            self.sync_thread.wait(2000)
        if self.export_thread and self.export_thread.isRunning():
            self.export_thread.quit()
            self.export_thread.wait(2000)
        super().closeEvent(event)

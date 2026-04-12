from __future__ import annotations

import time

import cv2
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from pyzbar.pyzbar import decode


class QRScannerThread(QThread):
    frame_ready = Signal(QImage)
    qr_detected = Signal(str)
    error = Signal(str)
    camera_state_changed = Signal(bool)

    def __init__(
        self,
        camera_index: int = 0,
        cooldown_seconds: float = 2.0,
        preferred_width: int = 1280,
        preferred_height: int = 720,
    ) -> None:
        super().__init__()
        self.camera_index = camera_index
        self.cooldown_seconds = cooldown_seconds
        self.preferred_width = preferred_width
        self.preferred_height = preferred_height
        self._running = False
        self._last_value = ""
        self._last_scan_time = 0.0
        self._last_error_time = 0.0

    def run(self) -> None:
        self._running = True
        capture = cv2.VideoCapture(self.camera_index)
        if not capture.isOpened():
            self.error.emit("Camera not available.")
            self.camera_state_changed.emit(False)
            return

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.preferred_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.preferred_height)

        self.camera_state_changed.emit(True)

        while self._running:
            success, frame = capture.read()
            if not success:
                now = time.time()
                if now - self._last_error_time >= 2:
                    self.error.emit("Unable to read from the camera.")
                    self._last_error_time = now
                self.msleep(100)
                continue

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channels = rgb_frame.shape
            image = QImage(
                rgb_frame.data,
                width,
                height,
                channels * width,
                QImage.Format_RGB888,
            ).copy()
            self.frame_ready.emit(image)

            self._decode_frame(frame)
            self.msleep(30)

        capture.release()
        self.camera_state_changed.emit(False)

    def stop(self) -> None:
        self._running = False
        self.wait(1500)

    def _decode_frame(self, frame) -> None:
        for barcode in decode(frame):
            raw_data = barcode.data or b""
            try:
                value = raw_data.decode("utf-8").strip()
            except UnicodeDecodeError:
                self._emit_invalid_qr()
                continue

            if not value:
                self._emit_invalid_qr()
                continue

            now = time.time()
            if value != self._last_value or now - self._last_scan_time >= self.cooldown_seconds:
                self._last_value = value
                self._last_scan_time = now
                self.qr_detected.emit(value)
            break

    def _emit_invalid_qr(self) -> None:
        now = time.time()
        if now - self._last_error_time >= 2:
            self.error.emit("Invalid QR code data.")
            self._last_error_time = now

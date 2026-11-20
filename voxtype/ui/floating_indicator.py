"""
Compact floating recording indicator (overlay pill) for VoxType.
Appears on screen during push-to-talk recording and transcription,
displaying animated waveform feedback, live timer, and status.
Uses non-activating window flags to prevent stealing application focus.
"""

import math
import sys
import time
from typing import List, Optional

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QWidget


class FloatingIndicator(QWidget):
    """Sleek desktop overlay pill that displays voice typing status."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Window flags: stays on top, tool window, frameless, translucent, non-focus-stealing
        flags = (
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.setFixedSize(310, 52)

        self._state = "idle"  # 'listening', 'processing', 'success', 'error', 'idle'
        self._status_text = "Listening..."
        self._start_time: float = 0.0
        self._elapsed_str = "00:00"
        self._audio_level = 0.0
        self._wave_bars = [0.1] * 8
        self._phase = 0.0
        self._drag_pos = QPoint()

        # Stopwatch & animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(33)

        # Auto-hide timer for success/error messages
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_indicator)

        self._reposition_to_default()

    def _reposition_to_default(self) -> None:
        """Positions pill near the bottom center of primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            x = geom.x() + (geom.width() - self.width()) // 2
            y = geom.y() + geom.height() - self.height() - 70
            self.move(x, y)

    def show_listening(self) -> None:
        """Transitions into recording/listening state."""
        self._hide_timer.stop()
        self._state = "listening"
        self._status_text = "Listening..."
        self._start_time = time.time()
        self._elapsed_str = "00:00"
        self._reposition_to_default()
        self.show()
        self.update()

    def show_processing(self) -> None:
        """Transitions into model inference / transcribing state."""
        self._hide_timer.stop()
        self._state = "processing"
        self._status_text = "Transcribing..."
        self.show()
        self.update()

    def show_success(self, word_count: int, latency_s: float) -> None:
        """Shows confirmation pill and schedules auto-hide."""
        self._state = "success"
        self._status_text = f"Typed {word_count} words ({latency_s:.2f}s)"
        self.update()
        self._hide_timer.start(1800)

    def show_completed(self, word_count: int, latency_s: float) -> None:
        self.show_success(word_count, latency_s)

    def show_error(self, message: str) -> None:
        """Shows error alert pill and schedules auto-hide."""
        self._state = "error"
        self._status_text = message
        self.update()
        self._hide_timer.start(2200)

    def hide_indicator(self) -> None:
        self._state = "idle"
        self.hide()

    def update_audio_level(self, level: float, wave_samples: Optional[List[float]] = None) -> None:
        """Feeds microphone audio energy into the floating waveform."""
        self._audio_level = level
        if wave_samples and len(wave_samples) >= 8:
            for i in range(8):
                val = max(0.1, min(1.0, wave_samples[i % len(wave_samples)] * 2.5))
                self._wave_bars[i] = val
        else:
            for i in range(8):
                curve = math.sin((i / 7.0) * math.pi)
                self._wave_bars[i] = max(0.1, min(1.0, (level + 0.1) * curve))

    def _on_tick(self) -> None:
        if self._state == "listening":
            elapsed = int(time.time() - self._start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self._elapsed_str = f"{mins:02d}:{secs:02d}"

        self._phase = (self._phase + 0.14) % (2.0 * math.pi)
        if self.isVisible():
            self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        w = float(self.width())
        h = float(self.height())
        r = h / 2.0

        # Background pill
        bg_brush = QBrush(QColor(11, 15, 25, 240))
        p.setPen(Qt.NoPen)
        p.setBrush(bg_brush)
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), r, r)

        # Border outline based on state
        if self._state == "listening":
            pulse_a = int(180 + 75 * math.sin(self._phase))
            border_pen = QPen(QColor(56, 189, 248, pulse_a), 1.6)
        elif self._state == "processing":
            border_pen = QPen(QColor(99, 102, 241, 220), 1.6)
        elif self._state == "success":
            border_pen = QPen(QColor(16, 185, 129, 230), 1.6)
        elif self._state == "error":
            border_pen = QPen(QColor(239, 68, 68, 230), 1.6)
        else:
            border_pen = QPen(QColor(36, 48, 72, 180), 1.0)

        p.setPen(border_pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), r, r)

        # State indicator circle / icon at left
        dot_x = 24.0
        dot_y = h / 2.0

        if self._state == "listening":
            # Pulsing recording dot
            dot_r = 5.0 + 1.5 * math.sin(self._phase)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(56, 189, 248, 80)))
            p.drawEllipse(QPoint(int(dot_x), int(dot_y)), int(dot_r + 4), int(dot_r + 4))

            p.setBrush(QBrush(QColor(56, 189, 248)))
            p.drawEllipse(QPoint(int(dot_x), int(dot_y)), int(dot_r), int(dot_r))

        elif self._state == "processing":
            # Spinning arc
            p.setPen(QPen(QColor(99, 102, 241), 2.5, Qt.SolidLine, Qt.RoundCap))
            arc_r = 7.0
            angle = int((self._phase / (2.0 * math.pi)) * 360 * 16)
            p.drawArc(
                QRectF(dot_x - arc_r, dot_y - arc_r, arc_r * 2, arc_r * 2),
                angle,
                240 * 16,
            )

        elif self._state == "success":
            p.setPen(QPen(QColor(16, 185, 129), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            path = QPainterPath()
            path.moveTo(dot_x - 5, dot_y)
            path.lineTo(dot_x - 1, dot_y + 4)
            path.lineTo(dot_x + 6, dot_y - 4)
            p.drawPath(path)

        elif self._state == "error":
            p.setPen(QPen(QColor(239, 68, 68), 2.5, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPoint(int(dot_x), int(dot_y - 5)), QPoint(int(dot_x), int(dot_y + 1)))
            p.setBrush(QBrush(QColor(239, 68, 68)))
            p.drawEllipse(QPoint(int(dot_x), int(dot_y + 5)), 1, 1)

        # Status text
        p.setPen(QColor(241, 245, 249))
        font = QFont("-apple-system, Segoe UI, Inter", 10, QFont.Medium)
        p.setFont(font)
        p.drawText(
            QRectF(40, 0, 140, h),
            Qt.AlignVCenter | Qt.AlignLeft,
            self._status_text,
        )

        # Right side: mini waveform or timer
        if self._state == "listening":
            # Draw 8 mini waveform bars
            bars_start_x = w - 85.0
            bar_w = 3.0
            for i in range(8):
                bx = bars_start_x + i * 5.0
                bh = max(4.0, self._wave_bars[i] * 22.0)
                by = dot_y - bh / 2.0
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(QColor(56, 189, 248)))
                p.drawRoundedRect(QRectF(bx, by, bar_w, bh), 1.5, 1.5)

            # Live timer
            p.setPen(QColor(148, 163, 184))
            p.setFont(QFont("Consolas, monospace", 9))
            p.drawText(
                QRectF(w - 44, 0, 36, h),
                Qt.AlignVCenter | Qt.AlignRight,
                self._elapsed_str,
            )

        p.end()

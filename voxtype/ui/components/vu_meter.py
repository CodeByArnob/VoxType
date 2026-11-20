"""
Precision VU level meter for microphone testing and audio calibration.
"""

from typing import Optional

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QWidget


class VUMeter(QWidget):
    """Horizontal audio level meter with peak hold and color gradient."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(14)
        self.setMinimumWidth(180)

        self._level = 0.0  # 0.0 to 1.0
        self._peak = 0.0
        self._peak_hold_ticks = 0

        self._decay_timer = QTimer(self)
        self._decay_timer.timeout.connect(self._decay)
        self._decay_timer.start(33)

    def set_level(self, level: float) -> None:
        lvl = max(0.0, min(1.0, level))
        self._level = lvl
        if lvl > self._peak:
            self._peak = lvl
            self._peak_hold_ticks = 15
        self.update()

    def _decay(self) -> None:
        changed = False
        if self._level > 0.01:
            self._level *= 0.88
            changed = True
        else:
            self._level = 0.0

        if self._peak_hold_ticks > 0:
            self._peak_hold_ticks -= 1
        elif self._peak > 0.01:
            self._peak -= 0.03
            changed = True
        else:
            self._peak = 0.0

        if changed:
            self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        r = h / 2.0

        # Background track
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(15, 23, 42)))
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        # Active fill width
        fill_w = max(0.0, min(w, w * self._level))
        if fill_w > 4.0:
            grad = QLinearGradient(0, 0, w, 0)
            grad.setColorAt(0.0, QColor(16, 185, 129))  # Normal green
            grad.setColorAt(0.7, QColor(56, 189, 248))  # Good cyan
            grad.setColorAt(0.9, QColor(245, 158, 11))  # Amber
            grad.setColorAt(1.0, QColor(239, 68, 68))   # Clip red

            p.setBrush(QBrush(grad))
            p.drawRoundedRect(QRectF(0, 0, fill_w, h), r, r)

        # Peak indicator line
        if self._peak > 0.05:
            px = min(w - 3.0, w * self._peak)
            p.setBrush(QBrush(QColor(255, 255, 255, 230)))
            p.drawRoundedRect(QRectF(px - 1.5, 1.0, 3.0, h - 2.0), 1.5, 1.5)

        p.end()

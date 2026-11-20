"""
Smooth real-time waveform visualizer for VoxType.
Renders lively audio bars that react to microphone input levels.
"""

import math
from typing import List, Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget


class WaveformWidget(QWidget):
    """Audio reactive waveform visualization widget."""

    def __init__(self, num_bars: int = 24, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.num_bars = num_bars
        self.setFixedHeight(48)
        self.setMinimumWidth(160)

        self._active = False
        self._levels: List[float] = [0.08] * num_bars
        self._target_levels: List[float] = [0.08] * num_bars
        self._phase = 0.0

        # Smooth animation timer (60 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(16)

    def set_active(self, active: bool) -> None:
        self._active = active
        if not active:
            self._target_levels = [0.08] * self.num_bars
        self.update()

    def update_audio_data(self, rms: float, wave_samples: Optional[List[float]] = None) -> None:
        """Injects new microphone audio frames."""
        self._active = True
        base_rms = max(0.05, min(1.0, rms * 1.5))

        if wave_samples and len(wave_samples) >= 8:
            # Map samples across bars with symmetric bell curve
            samples_len = len(wave_samples)
            for i in range(self.num_bars):
                # Sample index
                idx = int((i / self.num_bars) * samples_len) % samples_len
                sample_val = min(1.0, wave_samples[idx] * 2.5)
                # Combine sample with sine dispersion
                curve = math.sin((i / (self.num_bars - 1)) * math.pi)
                val = max(0.06, sample_val * curve * 1.2)
                self._target_levels[i] = min(1.0, val)
        else:
            for i in range(self.num_bars):
                curve = math.sin((i / (self.num_bars - 1)) * math.pi)
                noise = 0.2 * math.sin(self._phase + i * 0.4)
                self._target_levels[i] = max(0.06, min(1.0, (base_rms + noise) * curve))

    def _animate(self) -> None:
        self._phase = (self._phase + 0.12) % (2.0 * math.pi)

        # Smooth interpolation towards target levels
        has_movement = False
        for i in range(self.num_bars):
            if not self._active:
                target = 0.08 + 0.04 * math.sin(self._phase + i * 0.3)
            else:
                target = self._target_levels[i]

            diff = target - self._levels[i]
            if abs(diff) > 0.005:
                has_movement = True
                self._levels[i] += diff * 0.28
            else:
                self._levels[i] = target

        if has_movement or self._active:
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cy = h / 2.0

        bar_spacing = w / self.num_bars
        bar_width = max(3.0, bar_spacing * 0.55)
        corner_r = bar_width / 2.0

        for i in range(self.num_bars):
            bx = i * bar_spacing + (bar_spacing - bar_width) / 2.0
            val = self._levels[i]
            bar_h = max(6.0, val * (h - 8.0))
            by = cy - bar_h / 2.0

            # Dynamic gradient per bar
            grad = QLinearGradient(bx, by, bx, by + bar_h)
            if self._active:
                grad.setColorAt(0.0, QColor(56, 189, 248))  # Sky cyan
                grad.setColorAt(1.0, QColor(99, 102, 241))  # Indigo
            else:
                grad.setColorAt(0.0, QColor(100, 116, 139, 140))
                grad.setColorAt(1.0, QColor(71, 85, 105, 80))

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(QRectF(bx, by, bar_width, bar_h), corner_r, corner_r)

        painter.end()

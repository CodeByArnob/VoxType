"""
Animated microphone button with professional motion graphics.
Supports Idle, Listening, Processing, Success, and Error states,
live audio reactive pulsation, and manual click-to-record interaction.
"""

import math
from typing import List, Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget


class AnimatedMicButton(QWidget):
    """Hero interactive microphone button widget with real-time motion graphics."""

    clicked = Signal()

    STATE_IDLE = "idle"
    STATE_LISTENING = "listening"
    STATE_PROCESSING = "processing"
    STATE_SUCCESS = "success"
    STATE_COMPLETED = "completed"
    STATE_ERROR = "error"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(160, 160)
        self.setCursor(Qt.PointingHandCursor)

        self._state = self.STATE_IDLE
        self._audio_level = 0.0  # 0.0 to 1.0
        self._waveform_points: List[float] = [0.0] * 12
        self._pulse_phase = 0.0
        self._spin_angle = 0.0
        self._is_hovered = False

        # Animation timer (60 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_animation_tick)
        self._timer.start(16)

    def set_state(self, state: str) -> None:
        """Transitions button visual state."""
        if self._state != state:
            self._state = state
            self.update()

    def get_state(self) -> str:
        return self._state

    def set_audio_level(self, level: float, wave_points: Optional[List[float]] = None) -> None:
        """Updates live audio reactivity."""
        self._audio_level = max(0.0, min(1.0, level))
        if wave_points:
            self._waveform_points = wave_points[:12]
        self.update()

    def _on_animation_tick(self) -> None:
        """Frame update for procedural animations."""
        if self._state == self.STATE_LISTENING:
            self._pulse_phase = (self._pulse_phase + 0.08) % (2.0 * math.pi)
            self.update()
        elif self._state == self.STATE_PROCESSING:
            self._spin_angle = (self._spin_angle + 6.0) % 360.0
            self.update()
        elif self._is_hovered and self._state == self.STATE_IDLE:
            self._pulse_phase = (self._pulse_phase + 0.04) % (2.0 * math.pi)
            self.update()

    def enterEvent(self, event) -> None:
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        base_radius = min(w, h) * 0.36

        # Draw states
        if self._state == self.STATE_LISTENING:
            self._draw_listening_state(painter, cx, cy, base_radius)
        elif self._state == self.STATE_PROCESSING:
            self._draw_processing_state(painter, cx, cy, base_radius)
        elif self._state in (self.STATE_SUCCESS, self.STATE_COMPLETED):
            self._draw_success_state(painter, cx, cy, base_radius)
        elif self._state == self.STATE_ERROR:
            self._draw_error_state(painter, cx, cy, base_radius)
        else:
            self._draw_idle_state(painter, cx, cy, base_radius)

        painter.end()

    def _draw_idle_state(self, p: QPainter, cx: float, cy: float, r: float) -> None:
        # Hover glow
        if self._is_hovered:
            glow_r = r + 8.0 + 3.0 * math.sin(self._pulse_phase)
            glow_grad = QRadialGradient(cx, cy, glow_r)
            glow_grad.setColorAt(0.0, QColor(56, 189, 248, 60))
            glow_grad.setColorAt(1.0, QColor(56, 189, 248, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(glow_grad))
            p.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

        # Base circle
        base_grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
        base_grad.setColorAt(0.0, QColor(26, 36, 56))
        base_grad.setColorAt(1.0, QColor(15, 23, 42))

        border_color = QColor(56, 189, 248, 180) if self._is_hovered else QColor(36, 48, 72)
        p.setPen(QPen(border_color, 2.0))
        p.setBrush(QBrush(base_grad))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Draw Microphone Icon (Neutral White/Cyan)
        self._draw_microphone_icon(p, cx, cy, r * 0.52, QColor(241, 245, 249))

    def _draw_listening_state(self, p: QPainter, cx: float, cy: float, r: float) -> None:
        # Audio reactive pulse radius
        boost = self._audio_level * 18.0
        pulse1 = r + 6.0 + boost + 4.0 * math.sin(self._pulse_phase)
        pulse2 = r + 16.0 + boost * 1.4 + 6.0 * math.sin(self._pulse_phase + 1.0)

        # Outer animated ripple 2
        p.setPen(QPen(QColor(56, 189, 248, 40), 1.5))
        p.setBrush(QBrush(QColor(56, 189, 248, 20)))
        p.drawEllipse(QPointF(cx, cy), pulse2, pulse2)

        # Outer animated ripple 1
        p.setPen(QPen(QColor(56, 189, 248, 120), 2.0))
        p.setBrush(QBrush(QColor(56, 189, 248, 45)))
        p.drawEllipse(QPointF(cx, cy), pulse1, pulse1)

        # Core active circle
        core_grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
        core_grad.setColorAt(0.0, QColor(2, 132, 199))
        core_grad.setColorAt(1.0, QColor(14, 165, 233))

        p.setPen(QPen(QColor(255, 255, 255, 220), 2.5))
        p.setBrush(QBrush(core_grad))
        p.drawEllipse(QPointF(cx, cy), r + boost * 0.3, r + boost * 0.3)

        # Draw Microphone Icon
        self._draw_microphone_icon(p, cx, cy, r * 0.52, QColor(255, 255, 255))

    def _draw_processing_state(self, p: QPainter, cx: float, cy: float, r: float) -> None:
        # Spinner ring
        spinner_grad = QConicalGradient(cx, cy, self._spin_angle)
        spinner_grad.setColorAt(0.0, QColor(99, 102, 241, 240))
        spinner_grad.setColorAt(0.5, QColor(56, 189, 248, 180))
        spinner_grad.setColorAt(0.8, QColor(99, 102, 241, 40))
        spinner_grad.setColorAt(1.0, QColor(99, 102, 241, 0))

        p.setPen(QPen(QBrush(spinner_grad), 4.0))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r + 8.0, r + 8.0)

        # Inner body
        base_grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
        base_grad.setColorAt(0.0, QColor(30, 27, 75))
        base_grad.setColorAt(1.0, QColor(15, 23, 42))

        p.setPen(QPen(QColor(99, 102, 241, 140), 2.0))
        p.setBrush(QBrush(base_grad))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Draw Microphone Icon (Indigo/Violet)
        self._draw_microphone_icon(p, cx, cy, r * 0.52, QColor(165, 180, 252))

    def _draw_success_state(self, p: QPainter, cx: float, cy: float, r: float) -> None:
        # Emerald glow
        p.setPen(QPen(QColor(16, 185, 129, 160), 3.0))
        p.setBrush(QBrush(QColor(16, 185, 129, 40)))
        p.drawEllipse(QPointF(cx, cy), r + 6.0, r + 6.0)

        core_grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
        core_grad.setColorAt(0.0, QColor(5, 150, 105))
        core_grad.setColorAt(1.0, QColor(16, 185, 129))

        p.setPen(QPen(QColor(255, 255, 255, 220), 2.0))
        p.setBrush(QBrush(core_grad))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Draw Checkmark
        p.setPen(QPen(QColor(255, 255, 255), 4.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        check_path = QPainterPath()
        check_path.moveTo(cx - r * 0.32, cy)
        check_path.lineTo(cx - r * 0.08, cy + r * 0.24)
        check_path.lineTo(cx + r * 0.36, cy - r * 0.22)
        p.drawPath(check_path)

    def _draw_error_state(self, p: QPainter, cx: float, cy: float, r: float) -> None:
        p.setPen(QPen(QColor(239, 68, 68, 160), 3.0))
        p.setBrush(QBrush(QColor(239, 68, 68, 40)))
        p.drawEllipse(QPointF(cx, cy), r + 6.0, r + 6.0)

        core_grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
        core_grad.setColorAt(0.0, QColor(220, 38, 38))
        core_grad.setColorAt(1.0, QColor(239, 68, 68))

        p.setPen(QPen(QColor(255, 255, 255, 220), 2.0))
        p.setBrush(QBrush(core_grad))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Draw Exclamation mark
        p.setPen(QPen(QColor(255, 255, 255), 4.0, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx, cy - r * 0.30), QPointF(cx, cy + r * 0.06))
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawEllipse(QPointF(cx, cy + r * 0.26), 2.5, 2.5)

    def _draw_microphone_icon(
        self, p: QPainter, cx: float, cy: float, size: float, color: QColor
    ) -> None:
        """Renders vector microphone capsule and cradle."""
        capsule_w = size * 0.44
        capsule_h = size * 0.85
        cap_r = capsule_w / 2.0
        capsule_top = cy - capsule_h * 0.65

        # Capsule fill
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(color))
        p.drawRoundedRect(
            QRectF(cx - cap_r, capsule_top, capsule_w, capsule_h),
            cap_r,
            cap_r,
        )

        # Cradle U-arc
        cradle_r = size * 0.38
        cradle_y = cy - capsule_h * 0.15
        pen = QPen(color, 3.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        cradle_rect = QRectF(cx - cradle_r, cradle_y, cradle_r * 2.0, cradle_r * 2.0)
        p.drawArc(cradle_rect, 0 * 16, -180 * 16)

        # Stem & Base
        stem_top = cradle_y + cradle_r
        stem_bottom = stem_top + size * 0.28
        p.drawLine(QPointF(cx, stem_top), QPointF(cx, stem_bottom))

        base_w = size * 0.50
        p.drawLine(QPointF(cx - base_w / 2.0, stem_bottom), QPointF(cx + base_w / 2.0, stem_bottom))

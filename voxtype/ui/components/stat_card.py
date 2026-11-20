"""
Metric stat card component for VoxType dashboard.
Displays key performance metrics, latencies, and transcription stats.
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class StatCard(QFrame):
    """Refined stat card with title, primary value, and subtitle."""

    def __init__(
        self,
        title: str,
        value: str = "-",
        subtitle: str = "",
        accent_color: str = "#38BDF8",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setProperty("class", "CardFrame")

        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background-color: #131B2E;
                border: 1px solid #243048;
                border-radius: 12px;
                padding: 12px 16px;
            }}
            QFrame#StatCard:hover {{
                border-color: {accent_color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8; letter-spacing: 0.5px;")

        self.val_lbl = QLabel(value)
        self.val_lbl.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {accent_color};")

        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setStyleSheet("font-size: 11px; color: #64748B;")

        layout.addWidget(self.title_lbl)
        layout.addWidget(self.val_lbl)
        layout.addWidget(self.sub_lbl)

    def set_value(self, value: str) -> None:
        self.val_lbl.setText(value)

    def set_subtitle(self, subtitle: str) -> None:
        self.sub_lbl.setText(subtitle)

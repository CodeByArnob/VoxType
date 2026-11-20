"""
Interactive keyboard shortcut recorder and tester widget for VoxType.
Supports live key capture with Left/Right modifier discrimination,
conflict validation, and interactive hardware testing.
"""

import threading
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voxtype.core.hotkey_manager import (
    detect_shortcut_conflicts,
    format_shortcut_display,
    get_canonical_key,
)


class ShortcutRecorderWidget(QFrame):
    """Component for capturing, testing, and verifying global keyboard shortcuts."""

    shortcut_changed = Signal(str, str)  # (shortcut_str, mode)

    def __init__(
        self,
        current_shortcut: str = "ctrl_l",
        current_mode: str = "push_to_talk",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setProperty("class", "SurfaceCard")

        self._shortcut = current_shortcut
        self._mode = current_mode
        self._is_recording_keys = False
        self._captured_keys = set()
        self._capture_listener = None

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Title and mode description
        header = QHBoxLayout()
        title = QLabel("Keyboard Shortcut Configuration")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #F8FAFC;")
        header.addWidget(title)
        header.addStretch()

        layout.addLayout(header)

        # Mode Selection: Hold-to-Talk vs Toggle-to-Talk
        mode_box = QHBoxLayout()
        mode_box.setSpacing(8)

        self.btn_hold_mode = QPushButton("Hold-to-Talk (Default)")
        self.btn_hold_mode.setCheckable(True)
        self.btn_hold_mode.setChecked(self._mode == "push_to_talk")
        self.btn_hold_mode.clicked.connect(lambda: self._select_mode("push_to_talk"))

        self.btn_toggle_mode = QPushButton("Toggle-to-Talk")
        self.btn_toggle_mode.setCheckable(True)
        self.btn_toggle_mode.setChecked(self._mode == "toggle")
        self.btn_toggle_mode.clicked.connect(lambda: self._select_mode("toggle"))

        self._update_mode_button_styles()

        mode_box.addWidget(self.btn_hold_mode)
        mode_box.addWidget(self.btn_toggle_mode)
        mode_box.addStretch()
        layout.addLayout(mode_box)

        mode_help = QLabel(
            "• Hold-to-Talk: Hold key to record, release immediately to type.\n"
            "• Toggle-to-Talk: Press key once to start recording, press again to stop."
        )
        mode_help.setStyleSheet("font-size: 11px; color: #94A3B8; line-height: 1.4;")
        layout.addWidget(mode_help)

        # Shortcut Display & Recording Row
        rec_row = QHBoxLayout()
        rec_row.setSpacing(10)

        # Badge showing current key
        self.key_badge = QLabel(format_shortcut_display(self._shortcut))
        self.key_badge.setStyleSheet("""
            background-color: #0A0F1D;
            color: #38BDF8;
            font-size: 14px;
            font-weight: 700;
            padding: 8px 16px;
            border: 1px solid #1E2B45;
            border-radius: 8px;
            min-width: 140px;
        """)
        self.key_badge.setAlignment(Qt.AlignCenter)
        rec_row.addWidget(self.key_badge)

        self.record_btn = QPushButton("Capture Key")
        self.record_btn.setStyleSheet("padding: 8px 16px; font-weight: 700;")
        self.record_btn.clicked.connect(self._toggle_capture)
        rec_row.addWidget(self.record_btn)

        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.clicked.connect(self._reset_to_default)
        rec_row.addWidget(self.reset_btn)

        rec_row.addStretch()
        layout.addLayout(rec_row)

        # Conflict Warning Label
        self.conflict_lbl = QLabel("")
        self.conflict_lbl.setWordWrap(True)
        self.conflict_lbl.setStyleSheet("font-size: 11px; color: #F59E0B; font-weight: 600;")
        self.conflict_lbl.setVisible(False)
        layout.addWidget(self.conflict_lbl)

        # Interactive Test Area
        test_frame = QFrame()
        test_frame.setStyleSheet("""
            background-color: #0A0F1D;
            border: 1px dashed #1E2B45;
            border-radius: 8px;
            padding: 10px;
        """)
        tf_layout = QHBoxLayout(test_frame)
        tf_layout.setContentsMargins(12, 6, 12, 6)

        test_title = QLabel("Shortcut Test Pad:")
        test_title.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 600;")
        tf_layout.addWidget(test_title)

        self.test_status_lbl = QLabel("Press your shortcut anywhere to test response")
        self.test_status_lbl.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 500;")
        tf_layout.addWidget(self.test_status_lbl)
        tf_layout.addStretch()

        layout.addWidget(test_frame)

    def _select_mode(self, mode: str) -> None:
        self._mode = mode
        self.btn_hold_mode.setChecked(mode == "push_to_talk")
        self.btn_toggle_mode.setChecked(mode == "toggle")
        self._update_mode_button_styles()
        self.shortcut_changed.emit(self._shortcut, self._mode)

    def _update_mode_button_styles(self) -> None:
        active_style = """
            background-color: #38BDF8;
            color: #080C14;
            border: 1px solid #38BDF8;
            font-weight: 700;
            padding: 6px 14px;
        """
        inactive_style = """
            background-color: #131C31;
            color: #94A3B8;
            border: 1px solid #1E2B45;
            font-weight: 500;
            padding: 6px 14px;
        """
        self.btn_hold_mode.setStyleSheet(active_style if self._mode == "push_to_talk" else inactive_style)
        self.btn_toggle_mode.setStyleSheet(active_style if self._mode == "toggle" else inactive_style)

    def _toggle_capture(self) -> None:
        if self._is_recording_keys:
            self._stop_capture()
        else:
            self._start_capture()

    def _start_capture(self) -> None:
        self._is_recording_keys = True
        self._captured_keys.clear()
        self.record_btn.setText("Press Key(s)...")
        self.record_btn.setStyleSheet("background-color: #EF4444; color: #FFFFFF; font-weight: 700; padding: 8px 16px;")
        self.key_badge.setText("Listening...")

        # Start pynput capture listener
        from pynput import keyboard

        def on_press(key):
            if not self._is_recording_keys:
                return
            c_key = get_canonical_key(key)
            self._captured_keys.add(c_key)
            # Update display immediately
            combo_str = "+".join(sorted(self._captured_keys))
            QTimer.singleShot(0, lambda: self.key_badge.setText(format_shortcut_display(combo_str)))

        def on_release(key):
            if not self._is_recording_keys:
                return
            # On release, finalize captured keys
            if self._captured_keys:
                final_str = "+".join(sorted(self._captured_keys))
                QTimer.singleShot(0, lambda: self._finalize_captured_shortcut(final_str))

        self._capture_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self._capture_listener.daemon = True
        self._capture_listener.start()

    def _stop_capture(self) -> None:
        self._is_recording_keys = False
        if self._capture_listener:
            try:
                self._capture_listener.stop()
            except Exception:
                pass
            self._capture_listener = None
        self.record_btn.setText("Capture Key")
        self.record_btn.setStyleSheet("padding: 8px 16px; font-weight: 700;")

    def _finalize_captured_shortcut(self, shortcut_str: str) -> None:
        self._stop_capture()
        self._shortcut = shortcut_str
        self.key_badge.setText(format_shortcut_display(shortcut_str))

        # Check conflicts
        conflict = detect_shortcut_conflicts(shortcut_str)
        if conflict:
            self.conflict_lbl.setText(f"⚠️ {conflict}")
            self.conflict_lbl.setVisible(True)
        else:
            self.conflict_lbl.setVisible(False)

        self.shortcut_changed.emit(self._shortcut, self._mode)

    def _reset_to_default(self) -> None:
        self._stop_capture()
        self._shortcut = "ctrl_l"
        self._mode = "push_to_talk"
        self._select_mode("push_to_talk")
        self.key_badge.setText(format_shortcut_display("ctrl_l"))
        self.conflict_lbl.setVisible(False)
        self.shortcut_changed.emit(self._shortcut, self._mode)

    def set_test_feedback(self, is_pressed: bool, is_matched: bool) -> None:
        """Called by HotkeyManager test callback."""
        if is_matched:
            self.test_status_lbl.setText("[Active] Shortcut detected and verified.")
            self.test_status_lbl.setStyleSheet("font-size: 12px; color: #10B981; font-weight: 700;")
        elif is_pressed:
            self.test_status_lbl.setText("Key detected...")
            self.test_status_lbl.setStyleSheet("font-size: 12px; color: #38BDF8; font-weight: 600;")
        else:
            self.test_status_lbl.setText("Ready: Press your shortcut to test response")
            self.test_status_lbl.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 500;")

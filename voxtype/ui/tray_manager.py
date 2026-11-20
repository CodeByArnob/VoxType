"""
System tray integration for VoxType.
Runs quietly in the background with quick access menu and status indicators.
"""

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget


class TrayManager:
    """Manages the Windows taskbar notification tray icon and context menu."""

    def __init__(
        self,
        icon_path: Path,
        on_toggle_window: Callable[[], None],
        on_toggle_recording: Callable[[], None],
        on_quit: Callable[[], None],
        parent: Optional[QWidget] = None,
    ):
        self.on_toggle_window = on_toggle_window
        self.on_toggle_recording = on_toggle_recording
        self.on_quit = on_quit

        self.tray_icon = QSystemTrayIcon(parent)
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))

        self.tray_icon.setToolTip("VoxType")
        self._create_menu()
        self.tray_icon.activated.connect(self._on_activated)
        self.tray_icon.show()

    def _create_menu(self) -> None:
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #0D1322;
                color: #F8FAFC;
                border: 1px solid #1E2B45;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #131C31;
                color: #38BDF8;
            }
            QMenu::separator {
                height: 1px;
                background-color: #1E2B45;
                margin: 4px 8px;
            }
        """)

        title_action = QAction("VoxType", menu)
        title_action.setEnabled(False)
        menu.addAction(title_action)
        menu.addSeparator()

        rec_action = QAction("Toggle Recording", menu)
        rec_action.triggered.connect(self.on_toggle_recording)
        menu.addAction(rec_action)

        show_action = QAction("Open Dashboard", menu)
        show_action.triggered.connect(self.on_toggle_window)
        menu.addAction(show_action)

        menu.addSeparator()

        quit_action = QAction("Quit VoxType", menu)
        quit_action.triggered.connect(self.on_quit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.Trigger,
            QSystemTrayIcon.DoubleClick,
        ):
            self.on_toggle_window()

    def show_message(self, title: str, message: str) -> None:
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                title, message, QSystemTrayIcon.Information, 2000
            )

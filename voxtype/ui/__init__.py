"""
UI modules for VoxType application.
"""

from voxtype.ui.floating_indicator import FloatingIndicator
from voxtype.ui.main_window import MainWindow
from voxtype.ui.theme import DARK_PALETTE, LIGHT_PALETTE, get_stylesheet
from voxtype.ui.tray_manager import TrayManager

__all__ = [
    "FloatingIndicator",
    "MainWindow",
    "DARK_PALETTE",
    "LIGHT_PALETTE",
    "get_stylesheet",
    "TrayManager",
]

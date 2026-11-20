"""
Theme system and stylesheet definitions for VoxType.
Sophisticated dark-first design with cyan/blue accents, refined surfaces,
balanced spacing, and high contrast typography.
"""

from dataclasses import dataclass


@dataclass
class ColorPalette:
    bg_primary: str
    bg_surface: str
    bg_elevated: str
    bg_input: str
    border: str
    border_subtle: str
    border_focus: str
    accent_primary: str
    accent_secondary: str
    accent_hover: str
    text_primary: str
    text_secondary: str
    text_muted: str
    success: str
    warning: str
    error: str
    accent_glow: str


DARK_PALETTE = ColorPalette(
    bg_primary="#080C14",
    bg_surface="#0D1322",
    bg_elevated="#131C31",
    bg_input="#0A0F1D",
    border="#1E2B45",
    border_subtle="#162238",
    border_focus="#38BDF8",
    accent_primary="#38BDF8",
    accent_secondary="#2563EB",
    accent_hover="#0284C7",
    text_primary="#F8FAFC",
    text_secondary="#94A3B8",
    text_muted="#64748B",
    success="#10B981",
    warning="#F59E0B",
    error="#EF4444",
    accent_glow="rgba(56, 189, 248, 0.25)",
)

LIGHT_PALETTE = ColorPalette(
    bg_primary="#F8FAFC",
    bg_surface="#FFFFFF",
    bg_elevated="#F1F5F9",
    bg_input="#FFFFFF",
    border="#E2E8F0",
    border_subtle="#CBD5E1",
    border_focus="#0284C7",
    accent_primary="#0284C7",
    accent_secondary="#2563EB",
    accent_hover="#0369A1",
    text_primary="#0F172A",
    text_secondary="#475569",
    text_muted="#94A3B8",
    success="#059669",
    warning="#D97706",
    error="#DC2626",
    accent_glow="rgba(2, 132, 199, 0.15)",
)


def get_stylesheet(theme_name: str = "dark") -> str:
    palette = DARK_PALETTE if theme_name == "dark" else LIGHT_PALETTE

    return f"""
    * {{
        font-family: -apple-system, "Segoe UI Variable Display", "Segoe UI", "Inter", sans-serif;
        font-size: 13px;
        color: {palette.text_primary};
    }}

    QMainWindow, QDialog {{
        background-color: {palette.bg_primary};
    }}

    QWidget#centralWidget {{
        background-color: {palette.bg_primary};
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        border: none;
        background: {palette.bg_surface};
        width: 6px;
        border-radius: 3px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {palette.border};
        min-height: 24px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {palette.text_muted};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* Card & Surface Frames */
    QFrame.SurfaceCard {{
        background-color: {palette.bg_surface};
        border: 1px solid {palette.border};
        border-radius: 12px;
        padding: 14px;
    }}

    QFrame.ElevatedCard {{
        background-color: {palette.bg_elevated};
        border: 1px solid {palette.border_subtle};
        border-radius: 10px;
        padding: 12px;
    }}

    QFrame.HeaderFrame {{
        background-color: {palette.bg_surface};
        border-bottom: 1px solid {palette.border};
    }}

    /* Typography */
    QLabel.AppTitle {{
        font-size: 18px;
        font-weight: 800;
        color: {palette.text_primary};
        letter-spacing: -0.4px;
    }}

    QLabel.Subtitle {{
        font-size: 12px;
        color: {palette.text_secondary};
        font-weight: 500;
    }}

    QLabel.SectionHeader {{
        font-size: 14px;
        font-weight: 700;
        color: {palette.text_primary};
    }}

    QLabel.MutedText {{
        font-size: 11px;
        color: {palette.text_muted};
    }}

    /* Buttons */
    QPushButton {{
        background-color: {palette.bg_elevated};
        color: {palette.text_primary};
        border: 1px solid {palette.border};
        border-radius: 8px;
        padding: 7px 14px;
        font-weight: 600;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {palette.border};
        border-color: {palette.accent_primary};
    }}
    QPushButton:pressed {{
        background-color: {palette.bg_surface};
    }}
    QPushButton:disabled {{
        opacity: 0.4;
        color: {palette.text_muted};
        border-color: {palette.border_subtle};
    }}

    QPushButton.PrimaryButton {{
        background: {palette.accent_primary};
        color: #080C14;
        border: none;
        font-weight: 700;
        padding: 8px 16px;
    }}
    QPushButton.PrimaryButton:hover {{
        background: {palette.accent_hover};
        color: #FFFFFF;
    }}

    QPushButton.DangerButton {{
        background-color: rgba(239, 68, 68, 0.12);
        color: {palette.error};
        border: 1px solid rgba(239, 68, 68, 0.3);
    }}
    QPushButton.DangerButton:hover {{
        background-color: rgba(239, 68, 68, 0.25);
    }}

    /* Inputs, Combos, Spinners */
    QLineEdit, QComboBox, QSpinBox {{
        background-color: {palette.bg_input};
        color: {palette.text_primary};
        border: 1px solid {palette.border};
        border-radius: 8px;
        padding: 7px 11px;
        selection-background-color: {palette.accent_primary};
        selection-color: #080C14;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border: 1px solid {palette.border_focus};
    }}

    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: none;
    }}
    QComboBox QAbstractItemView {{
        background-color: {palette.bg_surface};
        color: {palette.text_primary};
        border: 1px solid {palette.border};
        selection-background-color: {palette.bg_elevated};
        selection-color: {palette.accent_primary};
        outline: none;
        border-radius: 6px;
        padding: 4px;
    }}

    /* Checkboxes */
    QCheckBox {{
        spacing: 10px;
        color: {palette.text_primary};
        font-size: 13px;
    }}
    QCheckBox::indicator {{
        width: 17px;
        height: 17px;
        border-radius: 4px;
        border: 1px solid {palette.border};
        background: {palette.bg_input};
    }}
    QCheckBox::indicator:hover {{
        border-color: {palette.accent_primary};
    }}
    QCheckBox::indicator:checked {{
        background-color: {palette.accent_primary};
        border-color: {palette.accent_primary};
    }}

    /* Sliders */
    QSlider::groove:horizontal {{
        border: none;
        height: 5px;
        background: {palette.border};
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {palette.accent_primary};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: #FFFFFF;
        border: 2px solid {palette.accent_primary};
        width: 15px;
        margin: -5px 0;
        border-radius: 7px;
    }}

    /* Top Navigation Tabs */
    QTabWidget::pane {{
        border: none;
        background-color: transparent;
    }}
    QTabBar::tab {{
        background-color: transparent;
        color: {palette.text_secondary};
        padding: 9px 16px;
        font-weight: 600;
        font-size: 12px;
        border-bottom: 2px solid transparent;
        margin-right: 4px;
    }}
    QTabBar::tab:hover {{
        color: {palette.text_primary};
    }}
    QTabBar::tab:selected {{
        color: {palette.accent_primary};
        border-bottom: 2px solid {palette.accent_primary};
    }}

    /* Table / List */
    QTableWidget, QListWidget {{
        background-color: {palette.bg_surface};
        border: 1px solid {palette.border};
        border-radius: 8px;
        gridline-color: {palette.border_subtle};
        color: {palette.text_primary};
    }}
    QHeaderView::section {{
        background-color: {palette.bg_elevated};
        color: {palette.text_secondary};
        padding: 6px;
        border: none;
        border-bottom: 1px solid {palette.border};
        font-weight: 600;
        font-size: 11px;
    }}
    """

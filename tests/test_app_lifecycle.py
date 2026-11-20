"""
Tests for VoxTypeApp lifecycle and coordinator.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from voxtype.app import VoxTypeApp


def test_voxtype_app_initialization(qapp):
    with patch("voxtype.core.hotkey_manager.HotkeyManager.start"), \
         patch("voxtype.core.whisper_engine.WhisperEngine.load_model_async"):

        app = VoxTypeApp()
        icon_path = Path("assets") / "icon.ico"
        app.init_ui(qapp, icon_path)

        assert app.main_window is not None
        assert app.floating_indicator is not None
        assert app.tray_manager is not None

        # Test toggle recording state transitions
        app.start_recording()
        app.stop_recording()

        # Clean shutdown of listeners and widgets
        app.hotkey_manager.stop()
        if app.main_window:
            app.main_window.deleteLater()
        if app.floating_indicator:
            app.floating_indicator.deleteLater()
        qapp.processEvents()

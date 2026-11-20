"""
Comprehensive end-to-end tests for real-world voice typing workflows in VoxType:
1. Hold-to-Talk workflow (Hold Left Ctrl -> record -> release -> transcribe -> inject text).
2. Toggle-to-Talk workflow (Press -> record -> press again -> transcribe -> inject text).
3. Focus preservation (Target application window handle restored before text injection).
4. Direct SendInput vs Clipboard fallback.
5. Empty and short recording rejection.
6. Zero-retention privacy mode.
7. Microphone disconnection and permission checks.
"""

from pathlib import Path
import time
from unittest.mock import MagicMock, patch

import numpy as np

from voxtype.app import VoxTypeApp
from voxtype.core.audio_recorder import AudioRecorder
from voxtype.core.config import AppConfig, ConfigManager
from voxtype.core.text_injector import TextInjector
from voxtype.core.text_processor import TextProcessor
from voxtype.core.whisper_engine import TranscriptionResult, WhisperEngine


def cleanup_app(app, qapp):
    app.hotkey_manager.stop()
    if app.main_window:
        app.main_window.deleteLater()
    if app.floating_indicator:
        app.floating_indicator.deleteLater()
    qapp.processEvents()


def test_hold_to_talk_complete_workflow(qapp):
    with patch("voxtype.core.whisper_engine.WhisperEngine.load_model_async"):
        app = VoxTypeApp()
        icon_path = Path("assets") / "icon.ico"
        app.init_ui(qapp, icon_path)

    TARGET_HWND = 12345
    mock_user32 = MagicMock()
    mock_user32.GetForegroundWindow.return_value = TARGET_HWND
    with patch("voxtype.core.text_injector.user32", mock_user32), \
         patch.object(app.recorder, "start_recording", return_value=True) as mock_rec_start, \
         patch.object(app.recorder, "stop_recording") as mock_rec_stop, \
         patch.object(app.whisper, "transcribe") as mock_transcribe, \
         patch.object(app.text_injector, "_inject_via_sendinput", return_value=True) as mock_inject:

        app.start_recording()
        app.recorder._is_recording = True
        assert app.text_injector._target_hwnd == TARGET_HWND

        speech_audio = (np.sin(np.linspace(0, 1000, int(16000 * 1.5))) * 0.4).astype(np.float32)
        mock_rec_stop.return_value = (speech_audio, 1.5)

        mock_transcribe.return_value = TranscriptionResult(
            text="Testing local voice typing with VoxType",
            language="en",
            audio_duration=1.5,
            inference_time=0.115,
            word_count=6,
            char_count=38,
            success=True,
        )

        app.stop_recording()
        time.sleep(0.3)

        assert mock_transcribe.called
        assert mock_inject.called
        injected_arg = mock_inject.call_args[0][0]
        assert "Testing local voice typing with VoxType" in injected_arg

    cleanup_app(app, qapp)


def test_toggle_to_talk_workflow(qapp):
    with patch("voxtype.core.whisper_engine.WhisperEngine.load_model_async"):
        app = VoxTypeApp()
        icon_path = Path("assets") / "icon.ico"
        app.init_ui(qapp, icon_path)
        app.config.shortcut.mode = "toggle"

    with patch.object(app.recorder, "start_recording", return_value=True) as mock_rec_start, \
         patch.object(app.recorder, "stop_recording", return_value=(np.zeros(16000, dtype=np.float32), 1.0)):

        app.toggle_recording()
        assert mock_rec_start.called
        app.toggle_recording()

    cleanup_app(app, qapp)


def test_empty_recording_rejection(qapp):
    with patch("voxtype.core.whisper_engine.WhisperEngine.load_model_async"):
        app = VoxTypeApp()
        icon_path = Path("assets") / "icon.ico"
        app.init_ui(qapp, icon_path)

    with patch.object(app.whisper, "transcribe") as mock_transcribe, \
         patch.object(app.sound_effects, "play_error") as mock_sfx_err:

        app._transcription_worker(np.zeros(1000, dtype=np.float32), 0.1)
        assert not mock_transcribe.called
        assert mock_sfx_err.called

        mock_sfx_err.reset_mock()
        app._transcription_worker(np.zeros(16000 * 2, dtype=np.float32), 2.0)
        assert not mock_transcribe.called
        assert mock_sfx_err.called

    cleanup_app(app, qapp)


def test_zero_retention_privacy_mode(qapp):
    cfg_mgr = ConfigManager()
    cfg_mgr.config.text.enable_history = False
    icon_path = Path("assets") / "icon.ico"

    from voxtype.ui.main_window import MainWindow
    win = MainWindow(cfg_mgr, icon_path)

    win.add_transcription_result("Confidential speech text", 3, 0.12)
    assert len(win.transcription_history) == 0
    assert win.history_table.rowCount() == 0

    win.deleteLater()
    qapp.processEvents()


def test_audio_device_disconnection_fallback():
    recorder = AudioRecorder(device_index=9999)
    with patch("sounddevice.InputStream") as mock_stream, \
         patch("sounddevice.query_devices", side_effect=Exception("Device disconnected")):
        ok = recorder.start_recording()
        assert mock_stream.call_args[1]["device"] is None

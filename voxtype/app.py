"""
Application coordinator and entry point for VoxType.
Manages application lifecycle, inter-thread signaling, voice typing pipelines,
tray integration, and desktop window events.
"""

from pathlib import Path
import sys
import threading
import time
from typing import List, Optional

import numpy as np
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication

from voxtype.core.audio_recorder import AudioRecorder
from voxtype.core.config import ConfigManager
from voxtype.core.hardware import get_hardware_profile
from voxtype.core.hotkey_manager import HotkeyManager
from voxtype.core.sound_effects import SoundEffects
from voxtype.core.text_injector import TextInjector
from voxtype.core.text_processor import TextProcessor
from voxtype.core.whisper_engine import WhisperEngine
from voxtype.ui.floating_indicator import FloatingIndicator
from voxtype.ui.main_window import MainWindow
from voxtype.ui.tray_manager import TrayManager


class AppBridge(QObject):
    """Qt signal bridge for inter-thread communication."""

    recording_started = Signal()
    recording_stopped = Signal()
    audio_level_updated = Signal(float, list)
    transcription_success = Signal(str, int, float)  # text, word_count, latency
    transcription_error = Signal(str)
    model_status_changed = Signal(str, str)


class VoxTypeApp:
    """Primary application orchestrator for VoxType desktop utility."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config

        # Signal bridge
        self.bridge = AppBridge()

        # Core subsystems
        self.text_processor = TextProcessor(self.config.text)
        self.text_injector = TextInjector(
            mode=self.config.text.insertion_mode,
            delay_ms=self.config.text.typing_delay_ms,
        )
        self.sound_effects = SoundEffects(enabled=self.config.audio.sound_feedback)

        # Audio recorder
        self.recorder = AudioRecorder(
            sample_rate=self.config.audio.sample_rate,
            channels=self.config.audio.channels,
            device_index=self.config.audio.device_index,
            on_level=self._on_audio_level,
            on_error=self._on_audio_error,
        )

        # Whisper engine
        profile = get_hardware_profile()
        self.whisper = WhisperEngine(
            model_name=self.config.model.model_name,
            models_dir=self.config.model.models_dir,
            compute_type=self.config.model.compute_type,
            device=self.config.model.device,
            threads=self.config.model.threads or profile.recommended_threads,
            on_status_change=self._on_engine_status,
        )

        # Hotkey manager
        self.hotkey_manager = HotkeyManager(
            shortcut=self.config.shortcut.push_to_talk_key,
            mode=self.config.shortcut.mode,
            on_start_recording=self.start_recording,
            on_stop_recording=self.stop_recording,
        )

        # UI instances
        self.main_window: Optional[MainWindow] = None
        self.floating_indicator: Optional[FloatingIndicator] = None
        self.tray_manager: Optional[TrayManager] = None

        self._is_processing = False
        self._lock = threading.Lock()

    def _on_audio_level(self, level: float, wave_points: List[float]) -> None:
        self.bridge.audio_level_updated.emit(level, wave_points)

    def _on_audio_error(self, message: str) -> None:
        self.bridge.transcription_error.emit(message)

    def _on_engine_status(self, state: str, message: str) -> None:
        self.bridge.model_status_changed.emit(state, message)

    def init_ui(self, app: QApplication, icon_path: Path) -> None:
        """Initializes GUI windows, tray, and event connections."""
        self.main_window = MainWindow(self.config_manager, icon_path)
        self.floating_indicator = FloatingIndicator()

        # Connect bridge signals to UI slots
        self.bridge.recording_started.connect(self._ui_on_recording_started)
        self.bridge.recording_stopped.connect(self._ui_on_recording_stopped)
        self.bridge.audio_level_updated.connect(self._ui_on_audio_level)
        self.bridge.transcription_success.connect(self._ui_on_transcription_success)
        self.bridge.transcription_error.connect(self._ui_on_transcription_error)
        self.bridge.model_status_changed.connect(self._ui_on_model_status)

        # Connect Main Window user requests
        self.main_window.request_toggle_recording.connect(self.toggle_recording)
        self.main_window.request_model_change.connect(self.switch_model)
        self.main_window.request_device_change.connect(self.switch_audio_device)
        self.main_window.request_test_mic.connect(self.test_mic)
        self.main_window.request_shortcut_change.connect(self.update_shortcut)

        # Wire up hotkey test callback to UI tester pad
        self.hotkey_manager.test_callback = self.main_window.on_hotkey_test_event

        # Tray integration
        self.tray_manager = TrayManager(
            icon_path=icon_path,
            on_toggle_window=self.toggle_main_window,
            on_toggle_recording=self.toggle_recording,
            on_quit=self.quit,
            parent=self.main_window,
        )

        if not self.config.ui.start_in_tray:
            self.main_window.show()

        # Start hotkey listener
        self.hotkey_manager.start()

        # Pre-load model asynchronously so first transcription is instantaneous
        self.whisper.load_model_async()

    def toggle_main_window(self) -> None:
        if self.main_window:
            if self.main_window.isVisible():
                self.main_window.hide()
            else:
                self.main_window.showNormal()
                self.main_window.activateWindow()

    def start_recording(self) -> None:
        """Begins voice capture."""
        with self._lock:
            if self.recorder.is_recording or self._is_processing:
                return

            # Capture foreground window handle right now
            self.text_injector.capture_foreground_window()

            ok = self.recorder.start_recording()
            if ok:
                self.sound_effects.enabled = self.config.audio.sound_feedback
                self.sound_effects.play_start()
                self.bridge.recording_started.emit()

    def stop_recording(self) -> None:
        """Ends voice capture and kicks off background transcription pipeline."""
        with self._lock:
            if not self.recorder.is_recording:
                return

            self.hotkey_manager.notify_external_stop()
            audio_data, duration = self.recorder.stop_recording()
            self._is_processing = True

        self.sound_effects.enabled = self.config.audio.sound_feedback
        self.sound_effects.play_stop()
        self.bridge.recording_stopped.emit()

        # Execute transcription in worker thread to keep UI completely responsive
        threading.Thread(
            target=self._transcription_worker,
            args=(audio_data, duration),
            daemon=True,
        ).start()

    def toggle_recording(self) -> None:
        if self.recorder.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def test_mic(self, enable: bool) -> None:
        if enable:
            if not self.recorder.is_recording:
                self.recorder.start_recording()
        else:
            if self.recorder.is_recording and not self._is_processing:
                self.recorder.stop_recording()

    def _transcription_worker(self, audio_data: Optional[np.ndarray], duration: float) -> None:
        """Background worker thread for Faster-Whisper inference and text injection."""
        try:
            # Check minimum speech duration or empty audio
            if audio_data is None or len(audio_data) < 16000 * 0.25:  # < 0.25s
                self.sound_effects.play_error()
                self.bridge.transcription_error.emit("Audio too short or empty")
                return

            # Check silence threshold
            if self.recorder.is_silent(audio_data, threshold=0.004):
                self.sound_effects.play_error()
                self.bridge.transcription_error.emit("No speech detected")
                return

            # Run Faster-Whisper local inference
            result = self.whisper.transcribe(
                audio_data=audio_data,
                language=self.config.model.language,
                beam_size=self.config.model.beam_size,
                vad_filter=self.config.audio.vad_enabled,
            )

            if not result.success or not result.text:
                if result.error:
                    self.sound_effects.play_error()
                    self.bridge.transcription_error.emit(result.error)
                else:
                    self.sound_effects.play_error()
                    self.bridge.transcription_error.emit("No clear speech recognized")
                return

            # Text normalization and cleanup
            self.text_processor.update_config(self.config.text)
            cleaned_text = self.text_processor.clean(result.text)

            if not cleaned_text.strip():
                self.sound_effects.play_error()
                self.bridge.transcription_error.emit("Filtered empty phrase")
                return

            # Automatically inject text into target window
            self.text_injector.mode = self.config.text.insertion_mode
            inject_ok = self.text_injector.inject(cleaned_text)

            if inject_ok:
                self.sound_effects.play_success()
                self.bridge.transcription_success.emit(
                    cleaned_text, result.word_count, result.inference_time
                )
            else:
                self.sound_effects.play_error()
                self.bridge.transcription_error.emit("Failed to inject text into active window")

        except Exception as e:
            err = f"Transcription failure: {e}"
            print(f"[VoxTypeApp] {err}")
            self.sound_effects.play_error()
            self.bridge.transcription_error.emit(err)
        finally:
            with self._lock:
                self._is_processing = False

    def switch_model(self, model_name: str, compute_type: str) -> None:
        self.whisper.load_model_async(model_name, compute_type)

    def switch_audio_device(self, device_index: int) -> None:
        idx = None if device_index < 0 else device_index
        self.recorder.set_device(idx)

    def update_shortcut(self, shortcut_str: str, mode: str) -> None:
        self.config.shortcut.push_to_talk_key = shortcut_str
        self.config.shortcut.mode = mode
        self.config_manager.save()
        self.hotkey_manager.set_shortcut(shortcut_str)
        self.hotkey_manager.set_mode(mode)

    # UI Slot Handlers
    def _ui_on_recording_started(self) -> None:
        if self.main_window:
            self.main_window.update_recording_state("listening")
        if self.floating_indicator and self.config.ui.show_floating_indicator:
            self.floating_indicator.show_listening()

    def _ui_on_recording_stopped(self) -> None:
        if self.main_window:
            self.main_window.update_recording_state("processing")
        if self.floating_indicator and self.config.ui.show_floating_indicator:
            self.floating_indicator.show_processing()

    def _ui_on_audio_level(self, level: float, wave_points: List[float]) -> None:
        if self.main_window:
            self.main_window.update_audio_level(level, wave_points)
        if self.floating_indicator and self.floating_indicator.isVisible():
            self.floating_indicator.update_audio_level(level, wave_points)

    def _ui_on_transcription_success(self, text: str, word_count: int, latency_s: float) -> None:
        if self.main_window:
            self.main_window.update_recording_state("success")
            self.main_window.add_transcription_result(text, word_count, latency_s)
            QTimer.singleShot(1800, lambda: self.main_window.update_recording_state("idle"))

        if self.floating_indicator and self.config.ui.show_floating_indicator:
            self.floating_indicator.show_success(word_count, latency_s)

    def _ui_on_transcription_error(self, message: str) -> None:
        if self.main_window:
            self.main_window.update_recording_state("error", message)
            QTimer.singleShot(2200, lambda: self.main_window.update_recording_state("idle"))

        if self.floating_indicator and self.config.ui.show_floating_indicator:
            self.floating_indicator.show_error(message)

    def _ui_on_model_status(self, state: str, message: str) -> None:
        if self.main_window:
            self.main_window.engine_status_lbl.setText(message)
            if state == "ready":
                self.main_window.engine_status_lbl.setStyleSheet(
                    "font-size: 11px; color: #10B981; font-weight: 600;"
                )
            elif state == "loading":
                self.main_window.engine_status_lbl.setStyleSheet(
                    "font-size: 11px; color: #38BDF8; font-weight: 600;"
                )
            elif state == "error":
                self.main_window.engine_status_lbl.setStyleSheet(
                    "font-size: 11px; color: #EF4444; font-weight: 600;"
                )

    def quit(self) -> None:
        """Gracefully shuts down background listeners and terminates process."""
        self.hotkey_manager.stop()
        if self.recorder.is_recording:
            self.recorder.stop_recording()
        QApplication.quit()


def main():
    # High-DPI support
    app = QApplication(sys.argv)
    app.setApplicationName("VoxType")
    app.setApplicationDisplayName("VoxType")
    app.setOrganizationName("VoxType")

    icon_path = Path(__file__).parent / "resources" / "icon.ico"
    if not icon_path.exists():
        icon_path = Path("assets") / "icon.ico"

    voxtype = VoxTypeApp()
    voxtype.init_ui(app, icon_path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

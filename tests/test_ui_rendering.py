"""
Tests for UI components and Qt widget rendering.
"""

from pathlib import Path
from voxtype.core.config import ConfigManager
from voxtype.ui.components.animated_mic_button import AnimatedMicButton
from voxtype.ui.components.vu_meter import VUMeter
from voxtype.ui.components.waveform_widget import WaveformWidget
from voxtype.ui.floating_indicator import FloatingIndicator
from voxtype.ui.main_window import MainWindow


def test_animated_mic_button_states(qapp):
    btn = AnimatedMicButton()
    assert btn.get_state() == AnimatedMicButton.STATE_IDLE

    for state in [
        AnimatedMicButton.STATE_LISTENING,
        AnimatedMicButton.STATE_PROCESSING,
        AnimatedMicButton.STATE_SUCCESS,
        AnimatedMicButton.STATE_COMPLETED,
        AnimatedMicButton.STATE_ERROR,
        AnimatedMicButton.STATE_IDLE,
    ]:
        btn.set_state(state)
        assert btn.get_state() == state

    btn.set_audio_level(0.75, [0.1, 0.4, 0.8, 0.2])
    btn.repaint()
    btn.deleteLater()
    qapp.processEvents()


def test_waveform_widget_rendering(qapp):
    wave = WaveformWidget(num_bars=16)
    wave.set_active(True)
    wave.update_audio_data(0.5, [0.1, 0.5, 0.9])
    wave.repaint()
    wave.set_active(False)
    wave.repaint()
    wave.deleteLater()
    qapp.processEvents()


def test_vu_meter_rendering(qapp):
    vu = VUMeter()
    vu.set_level(0.85)
    vu.repaint()
    vu.deleteLater()
    qapp.processEvents()


def test_floating_indicator(qapp):
    indicator = FloatingIndicator()
    indicator.show_listening()
    assert indicator._state == "listening"
    indicator.update_audio_level(0.6)
    indicator.repaint()

    indicator.show_processing()
    assert indicator._state == "processing"
    indicator.repaint()

    indicator.show_success(15, 0.2)
    assert indicator._state == "success"
    indicator.repaint()

    indicator.show_completed(15, 0.2)
    assert indicator._state == "success"

    indicator.show_error("Microphone error")
    assert indicator._state == "error"
    indicator.repaint()

    indicator.hide_indicator()
    assert indicator._state == "idle"
    indicator.deleteLater()
    qapp.processEvents()


def test_main_window_tabs_and_state(qapp):
    cfg_mgr = ConfigManager()
    icon_path = Path("assets") / "icon.ico"
    win = MainWindow(cfg_mgr, icon_path)

    assert win.tabs.count() == 6
    win.update_recording_state("listening")
    win.update_recording_state("processing")
    win.update_recording_state("completed")
    win.update_recording_state("error")
    win.update_recording_state("idle")

    win.add_transcription_result("Testing transcription pipeline", 3, 0.15)
    assert win.total_words_typed == 3
    assert len(win.transcription_history) == 1

    win.deleteLater()
    qapp.processEvents()

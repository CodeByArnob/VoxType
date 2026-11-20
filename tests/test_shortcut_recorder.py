"""
Tests for ShortcutRecorderWidget UI component.
"""

import pytest
from voxtype.ui.components.shortcut_recorder import ShortcutRecorderWidget


@pytest.fixture
def recorder_widget(qapp):
    widget = ShortcutRecorderWidget()
    yield widget
    widget.deleteLater()
    qapp.processEvents()


def test_shortcut_recorder_initialization(recorder_widget):
    assert recorder_widget._shortcut == "ctrl_l"
    assert recorder_widget._mode == "push_to_talk"
    assert recorder_widget.key_badge.text() == "Left Ctrl"
    assert recorder_widget.btn_hold_mode.isChecked() is True
    assert recorder_widget.btn_toggle_mode.isChecked() is False


def test_shortcut_recorder_mode_switch(recorder_widget):
    received = []
    recorder_widget.shortcut_changed.connect(lambda s, m: received.append((s, m)))

    recorder_widget._select_mode("toggle")
    assert recorder_widget._mode == "toggle"
    assert recorder_widget.btn_toggle_mode.isChecked() is True
    assert received[-1] == ("ctrl_l", "toggle")

    recorder_widget._select_mode("push_to_talk")
    assert recorder_widget._mode == "push_to_talk"
    assert received[-1] == ("ctrl_l", "push_to_talk")


def test_shortcut_recorder_conflict_display(recorder_widget):
    # Finalize with a conflicting shortcut
    recorder_widget._finalize_captured_shortcut("ctrl+c")
    assert "Copy" in recorder_widget.conflict_lbl.text()

    # Finalize with safe shortcut
    recorder_widget._finalize_captured_shortcut("ctrl_l")
    assert recorder_widget.conflict_lbl.text() == "" or not recorder_widget.conflict_lbl.isVisibleTo(recorder_widget)


def test_shortcut_recorder_reset(recorder_widget):
    recorder_widget._shortcut = "alt_l+space"
    recorder_widget._mode = "toggle"
    recorder_widget._reset_to_default()
    assert recorder_widget._shortcut == "ctrl_l"
    assert recorder_widget._mode == "push_to_talk"
    assert recorder_widget.key_badge.text() == "Left Ctrl"


def test_shortcut_recorder_test_feedback(recorder_widget):
    recorder_widget.set_test_feedback(is_pressed=True, is_matched=True)
    assert "[Active]" in recorder_widget.test_status_lbl.text()

    recorder_widget.set_test_feedback(is_pressed=False, is_matched=False)
    assert "Ready" in recorder_widget.test_status_lbl.text()

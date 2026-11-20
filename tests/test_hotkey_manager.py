"""
Tests for intelligent global hotkey manager and conflict detection.
"""

from unittest.mock import MagicMock
from pynput.keyboard import Key, KeyCode
from voxtype.core.hotkey_manager import (
    HotkeyManager,
    detect_shortcut_conflicts,
    format_shortcut_display,
    get_canonical_key,
)


def test_canonical_key_discrimination():
    # Left Ctrl vs Right Ctrl
    assert get_canonical_key(Key.ctrl_l) == "ctrl_l"
    assert get_canonical_key(Key.ctrl_r) == "ctrl_r"
    assert get_canonical_key(Key.alt_l) == "alt_l"
    assert get_canonical_key(Key.alt_r) == "alt_r"
    assert get_canonical_key(Key.shift_l) == "shift_l"
    assert get_canonical_key(Key.shift_r) == "shift_r"
    assert get_canonical_key(Key.caps_lock) == "caps_lock"


def test_format_shortcut_display():
    assert format_shortcut_display("ctrl_l") == "Left Ctrl"
    assert format_shortcut_display("ctrl_r") == "Right Ctrl"
    assert format_shortcut_display("ctrl_l+space") == "Left Ctrl + Space"
    assert format_shortcut_display("alt_l+f8") == "Left Alt + F8"


def test_conflict_detection():
    # Standard conflict
    assert detect_shortcut_conflicts("ctrl+c") is not None
    assert detect_shortcut_conflicts("ctrl_l+c") is not None
    assert detect_shortcut_conflicts("alt+f4") is not None

    # Single character warning
    assert detect_shortcut_conflicts("a") is not None

    # Safe shortcut
    assert detect_shortcut_conflicts("ctrl_l") is None
    assert detect_shortcut_conflicts("ctrl_l+space") is None
    assert detect_shortcut_conflicts("f8") is None


def test_hold_to_talk_workflow():
    start_mock = MagicMock()
    stop_mock = MagicMock()

    hm = HotkeyManager(
        shortcut="ctrl_l",
        mode="push_to_talk",
        on_start_recording=start_mock,
        on_stop_recording=stop_mock,
    )
    hm._is_running = True

    # 1. Press Left Ctrl
    hm._on_press(Key.ctrl_l)
    assert start_mock.call_count == 1
    assert hm._is_recording_active is True

    # 2. Key repeat (holding down)
    hm._on_press(Key.ctrl_l)
    assert start_mock.call_count == 1  # Should not duplicate

    # 3. Release Left Ctrl
    hm._on_release(Key.ctrl_l)
    assert stop_mock.call_count == 1
    assert hm._is_recording_active is False


def test_toggle_to_talk_workflow():
    start_mock = MagicMock()
    stop_mock = MagicMock()

    hm = HotkeyManager(
        shortcut="f8",
        mode="toggle",
        on_start_recording=start_mock,
        on_stop_recording=stop_mock,
    )
    hm._is_running = True

    # First press toggles ON
    hm._on_press(Key.f8)
    assert start_mock.call_count == 1
    assert hm._is_recording_active is True
    hm._on_release(Key.f8)
    assert stop_mock.call_count == 0  # Releasing in toggle mode does NOT stop

    # Second press toggles OFF
    hm._on_press(Key.f8)
    assert stop_mock.call_count == 1
    assert hm._is_recording_active is False

"""
Tests for text injection and active window handling.
"""

from voxtype.core.text_injector import TextInjector


def test_text_injector_initialization():
    injector = TextInjector(mode="sendinput", delay_ms=2)
    assert injector.mode == "sendinput"
    assert injector.delay_ms == 2

    # Test empty injection
    assert injector.inject("") is True


def test_capture_window():
    injector = TextInjector()
    hwnd = injector.capture_foreground_window()
    assert isinstance(hwnd, int)

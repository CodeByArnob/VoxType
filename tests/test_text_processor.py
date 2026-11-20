"""
Tests for text processing, normalization, and cleanup.
"""

from voxtype.core.config import TextConfig
from voxtype.core.text_processor import TextProcessor


def test_auto_capitalization():
    tp = TextProcessor()
    raw = "hello world. this is a test. here we go!"
    cleaned = tp.clean(raw)
    assert cleaned.startswith("Hello world. This is a test. Here we go!")


def test_filler_word_removal():
    cfg = TextConfig(remove_filler_words=True, filler_words=["um", "uh", "er"])
    tp = TextProcessor(cfg)

    raw = "um, I would like to, uh, test the system, er, today."
    cleaned = tp.clean(raw)
    # Check that um, uh, er are removed
    assert "um" not in cleaned.lower()
    assert "uh" not in cleaned.lower()
    assert "er" not in cleaned.lower()
    assert "test the system" in cleaned.lower()


def test_whisper_silence_artifacts_removal():
    tp = TextProcessor()
    for artifact in ["[BLANK_AUDIO]", "(silence)", "Thank you for watching.", "[music]"]:
        result = tp.clean(artifact)
        assert result == ""


def test_custom_replacements():
    cfg = TextConfig(
        custom_replacements={
            "smiley face": ":-)",
            "new line": "\n",
            "at the rate": "@",
        }
    )
    tp = TextProcessor(cfg)
    raw = "Please send email to john at the rate example.com smiley face"
    cleaned = tp.clean(raw)
    assert "@" in cleaned
    assert ":-)" in cleaned


def test_punctuation_spacing():
    tp = TextProcessor()
    raw = "hello ,world ! how are you ?fine"
    cleaned = tp.clean(raw)
    assert "Hello, world!" in cleaned
    assert "How are you? Fine" in cleaned

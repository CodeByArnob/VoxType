"""
Integration tests for the complete VoxType voice typing pipeline.
Tests end-to-end audio processing, silence handling, text cleanup,
and clipboard preservation during injection.
"""

from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from voxtype.core.audio_recorder import AudioRecorder
from voxtype.core.config import AppConfig
from voxtype.core.sound_effects import SoundEffects
from voxtype.core.text_injector import TextInjector
from voxtype.core.text_processor import TextProcessor
from voxtype.core.whisper_engine import TranscriptionResult, WhisperEngine


def test_full_pipeline_with_mocked_whisper():
    """Verifies complete dataflow from audio array to cleaned text injection."""
    config = AppConfig()
    processor = TextProcessor(config.text)
    injector = TextInjector(mode="sendinput")

    # 1. Simulate recorded audio
    sample_rate = 16000
    duration = 2.0
    audio_data = (np.sin(np.linspace(0, 440 * 2 * np.pi, int(sample_rate * duration))) * 0.3).astype(np.float32)

    recorder = AudioRecorder(sample_rate=sample_rate)
    assert recorder.is_silent(audio_data, threshold=0.005) is False

    # 2. Mock Whisper inference output
    raw_whisper_output = "um, hello world this is a test of the voxtype engine"
    mock_engine = MagicMock(spec=WhisperEngine)
    mock_engine.transcribe.return_value = TranscriptionResult(
        text=raw_whisper_output,
        language="en",
        audio_duration=duration,
        inference_time=0.12,
        word_count=10,
        char_count=len(raw_whisper_output),
        success=True,
    )

    res = mock_engine.transcribe(audio_data)
    assert res.success is True

    # 3. Text Processor cleans raw output
    cleaned = processor.clean(res.text)
    assert "um" not in cleaned.lower()
    assert cleaned.startswith("Hello world this is a test of the voxtype engine")

    # 4. Injector simulates typing
    with patch.object(injector, "_inject_via_sendinput", return_value=True) as mock_send:
        ok = injector.inject(cleaned)
        assert ok is True
        assert mock_send.call_count == 1


def test_clipboard_fallback_preserves_user_clipboard():
    """Ensures clipboard paste fallback restores user's existing clipboard contents."""
    injector = TextInjector(mode="clipboard_paste")

    with patch("pyperclip.paste", return_value="PREVIOUS_USER_DATA"), \
         patch("pyperclip.copy") as mock_copy, \
         patch.object(injector, "_send_ctrl_v"):

        success = injector._inject_via_clipboard("New Transcribed Text")
        assert success is True
        # Verify first copy was transcribed text, and final copy was original user data
        assert mock_copy.call_args_list[0][0][0] == "New Transcribed Text"
        assert mock_copy.call_args_list[1][0][0] == "PREVIOUS_USER_DATA"


def test_silence_rejection_workflow():
    """Verifies that pure silence is safely rejected before reaching the engine."""
    recorder = AudioRecorder()
    silence = np.zeros(16000 * 2, dtype=np.float32)
    assert recorder.is_silent(silence) is True

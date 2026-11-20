"""
Tests for audio recorder functions and silence detection.
"""

import numpy as np
from voxtype.core.audio_recorder import AudioRecorder


def test_silence_detection():
    recorder = AudioRecorder()

    # Zero array
    silence = np.zeros(16000, dtype=np.float32)
    assert recorder.is_silent(silence, threshold=0.005) is True

    # High energy audio
    tone = (np.sin(np.linspace(0, 100, 16000)) * 0.5).astype(np.float32)
    assert recorder.is_silent(tone, threshold=0.005) is False


def test_device_enumeration():
    devices = AudioRecorder.list_input_devices()
    assert isinstance(devices, list)

"""
Tests for sound effect synthesis and WAV generation.
"""

import io
import wave
from voxtype.core.sound_effects import SoundEffects, _generate_wav


def test_wav_generation():
    wav_bytes = _generate_wav([440.0, 880.0], [0.05, 0.05], sample_rate=22050, volume=0.2)
    assert len(wav_bytes) > 44  # WAV header is 44 bytes

    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 22050
        n_frames = wf.getnframes()
        assert abs(n_frames - int(22050 * 0.10)) <= 2


def test_sound_effects_cache():
    sfx = SoundEffects(enabled=False)
    assert "start" in sfx._cache
    assert "stop" in sfx._cache
    assert "success" in sfx._cache
    assert "error" in sfx._cache

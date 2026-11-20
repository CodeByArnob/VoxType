"""
Auditory feedback system for VoxType.
Generates and plays lightweight, pleasant chimes for state transitions
using native Windows in-memory WAV synthesis.
"""

import io
import math
import struct
import sys
import threading
import wave
from typing import Optional


def _generate_wav(
    frequencies: list,
    durations: list,
    sample_rate: int = 22050,
    volume: float = 0.25,
) -> bytes:
    """Generates an in-memory WAV byte buffer with smooth attack/decay envelope."""
    total_samples = []
    for freq, duration in zip(frequencies, durations):
        n_samples = int(sample_rate * duration)
        for i in range(n_samples):
            t = i / sample_rate
            # Smooth sine wave with attack and decay to eliminate audio clicking
            envelope = 1.0
            attack_samples = int(sample_rate * 0.01)
            decay_samples = int(sample_rate * 0.02)
            if i < attack_samples:
                envelope = i / attack_samples
            elif i > n_samples - decay_samples:
                envelope = (n_samples - i) / decay_samples

            sample = math.sin(2.0 * math.pi * freq * t) * envelope * volume
            # Clamp sample
            clamped = max(-1.0, min(1.0, sample))
            total_samples.append(int(clamped * 32767))

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw_frames = struct.pack(f"<{len(total_samples)}h", *total_samples)
        wf.writeframes(raw_frames)

    return buf.getvalue()


class SoundEffects:
    """Manages playback of synthesized UI sounds."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._cache = {}
        self._init_sounds()

    def _init_sounds(self) -> None:
        try:
            # Gentle ascending blip on record start
            self._cache["start"] = _generate_wav([520.0, 780.0], [0.04, 0.05], volume=0.20)
            # Soft descending blip on record stop / start processing
            self._cache["stop"] = _generate_wav([780.0, 520.0], [0.03, 0.04], volume=0.18)
            # Delicate double chime on successful text insertion
            self._cache["success"] = _generate_wav([659.25, 880.0], [0.05, 0.07], volume=0.22)
            # Soft warm low alert on silence or error
            self._cache["error"] = _generate_wav([320.0, 240.0], [0.06, 0.07], volume=0.25)
        except Exception as e:
            print(f"[SoundEffects] Error pre-generating audio: {e}")

    def play(self, sound_name: str) -> None:
        if not self.enabled:
            return

        wav_bytes = self._cache.get(sound_name)
        if not wav_bytes:
            return

        def _play_worker():
            if sys.platform == "win32":
                try:
                    import winsound
                    winsound.PlaySound(
                        wav_bytes, winsound.SND_MEMORY | winsound.SND_NODEFAULT
                    )
                except Exception:
                    pass

        threading.Thread(target=_play_worker, daemon=True).start()

    def play_start(self) -> None:
        self.play("start")

    def play_stop(self) -> None:
        self.play("stop")

    def play_success(self) -> None:
        self.play("success")

    def play_error(self) -> None:
        self.play("error")

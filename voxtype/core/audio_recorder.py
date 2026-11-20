"""
Audio recorder module for VoxType.
Captures microphone input using sounddevice, computes real-time RMS/waveform levels,
checks hardware permissions, and packages normalized 16kHz float32 audio for Faster-Whisper.
"""

import collections
import threading
import time
from typing import Callable, List, Optional, Tuple

import numpy as np


class AudioRecorder:
    """Manages microphone audio capture and real-time level monitoring."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device_index: Optional[int] = None,
        on_level: Optional[Callable[[float, List[float]], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_index = device_index
        self.on_level = on_level  # callback(rms, waveform_points)
        self.on_error = on_error

        self._stream = None
        self._is_recording = False
        self._audio_frames: List[np.ndarray] = []
        self._lock = threading.Lock()
        self._start_time: float = 0.0
        self._recent_levels = collections.deque(maxlen=32)

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @classmethod
    def list_input_devices(cls) -> List[Tuple[int, str, bool]]:
        """Returns list of (device_index, name, is_default) for input devices."""
        devices = []
        try:
            import sounddevice as sd
            default_input = sd.default.device[0]
            for idx, dev in enumerate(sd.query_devices()):
                if dev.get("max_input_channels", 0) > 0:
                    is_default = (idx == default_input)
                    devices.append((idx, dev.get("name", f"Microphone {idx}"), is_default))
        except Exception as e:
            print(f"[AudioRecorder] Failed to list devices: {e}")
        return devices

    @classmethod
    def check_microphone_permission(cls) -> Tuple[bool, str]:
        """Tests whether the microphone is accessible and permission is granted."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            has_input = any(d.get("max_input_channels", 0) > 0 for d in devices)
            if not has_input:
                return False, "No microphone or audio input device found."

            # Quick probe
            stream = sd.InputStream(samplerate=16000, channels=1, blocksize=512)
            stream.start()
            time.sleep(0.04)
            stream.stop()
            stream.close()
            return True, "Microphone access verified and working."
        except Exception as e:
            err_str = str(e)
            if "permission" in err_str.lower() or "denied" in err_str.lower():
                return False, "Microphone access denied in Windows Privacy Settings."
            return False, f"Microphone check failed: {err_str}"

    def set_device(self, device_index: Optional[int]) -> None:
        """Changes active input device."""
        self.device_index = device_index

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for every audio chunk."""
        if not self._is_recording:
            return

        # indata is float32 numpy array with shape (frames, channels)
        chunk = indata[:, 0].copy()
        with self._lock:
            self._audio_frames.append(chunk)

        # Compute RMS volume level (0.0 to 1.0)
        rms = float(np.sqrt(np.mean(chunk**2)))
        # Normalize RMS visually with soft compression
        normalized_rms = min(1.0, rms * 10.0)
        self._recent_levels.append(normalized_rms)

        if self.on_level:
            # Downsample chunk to ~16 points for smooth waveform animation
            step = max(1, len(chunk) // 16)
            wave_points = [float(abs(chunk[i])) for i in range(0, len(chunk), step)][:16]
            self.on_level(normalized_rms, wave_points)

    def start_recording(self) -> bool:
        """Begins streaming audio from microphone with auto-fallback on device disconnection."""
        if self._is_recording:
            return True

        with self._lock:
            self._audio_frames.clear()
            self._recent_levels.clear()
            self._start_time = time.time()

        try:
            import sounddevice as sd

            target_device = self.device_index
            # Check if target device exists; if disconnected, fallback to default
            if target_device is not None:
                try:
                    dev_info = sd.query_devices(target_device)
                    if dev_info.get("max_input_channels", 0) <= 0:
                        target_device = None
                except Exception:
                    print(f"[AudioRecorder] Device index {target_device} not found. Falling back to default.")
                    target_device = None

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                device=target_device,
                blocksize=1024,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._is_recording = True
            return True
        except Exception as e:
            self._is_recording = False
            msg = f"Failed to start recording: {e}"
            print(f"[AudioRecorder] {msg}")
            if self.on_error:
                self.on_error(msg)
            return False

    def stop_recording(self) -> Tuple[Optional[np.ndarray], float]:
        """Stops recording and returns (audio_array, duration_seconds)."""
        if not self._is_recording and not self._audio_frames:
            return None, 0.0

        self._is_recording = False
        duration = time.time() - self._start_time

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        with self._lock:
            if not self._audio_frames:
                return None, duration
            audio_data = np.concatenate(self._audio_frames, axis=0)
            self._audio_frames.clear()

        return audio_data, duration

    def is_silent(self, audio: np.ndarray, threshold: float = 0.005) -> bool:
        """Determines if the recorded audio is silence or background noise."""
        if audio is None or len(audio) == 0:
            return True
        rms = float(np.sqrt(np.mean(audio**2)))
        return rms < threshold

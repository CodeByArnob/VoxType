"""
Whisper transcription engine for VoxType.
Manages local Faster-Whisper models, multi-threaded inference,
download progress tracking, and hardware-accelerated transcription.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np


AVAILABLE_MODELS = {
    "tiny": {
        "name": "Tiny",
        "size_mb": 75,
        "speed": "Fastest (~50ms)",
        "accuracy": "Good",
        "vram_ram": "~400MB",
        "description": "Ultra-lightweight, ideal for older CPUs or battery saving.",
    },
    "base": {
        "name": "Base",
        "size_mb": 145,
        "speed": "Very Fast (~100ms)",
        "accuracy": "Great",
        "vram_ram": "~600MB",
        "description": "Recommended balance of speed and accuracy for everyday voice typing.",
    },
    "small": {
        "name": "Small",
        "size_mb": 490,
        "speed": "Fast (~250ms)",
        "accuracy": "High",
        "vram_ram": "~1.2GB",
        "description": "High accuracy for multilingual typing and complex jargon.",
    },
    "medium": {
        "name": "Medium",
        "size_mb": 1500,
        "speed": "Moderate (~600ms)",
        "accuracy": "Very High",
        "vram_ram": "~2.8GB",
        "description": "Professional accuracy for technical, legal, and medical dictation.",
    },
    "large-v3": {
        "name": "Large (v3)",
        "size_mb": 3100,
        "speed": "Standard (~1200ms)",
        "accuracy": "Maximum",
        "vram_ram": "~4.5GB",
        "description": "State-of-the-art multilingual recognition for demanding transcription.",
    },
}

SUPPORTED_LANGUAGES = [
    ("auto", "Auto-Detect"),
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("nl", "Dutch"),
    ("ru", "Russian"),
    ("zh", "Chinese"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("ar", "Arabic"),
    ("hi", "Hindi"),
    ("bn", "Bengali"),
    ("tr", "Turkish"),
    ("pl", "Polish"),
    ("uk", "Ukrainian"),
    ("vi", "Vietnamese"),
    ("id", "Indonesian"),
    ("sv", "Swedish"),
    ("cs", "Czech"),
    ("ro", "Romanian"),
    ("hu", "Hungarian"),
    ("el", "Greek"),
    ("da", "Danish"),
    ("fi", "Finnish"),
    ("no", "Norwegian"),
    ("he", "Hebrew"),
    ("th", "Thai"),
]


@dataclass
class TranscriptionResult:
    text: str
    language: str
    audio_duration: float
    inference_time: float
    word_count: int
    char_count: int
    success: bool
    error: Optional[str] = None


class WhisperEngine:
    """Manages the Faster-Whisper model instance and executes audio transcription."""

    def __init__(
        self,
        model_name: str = "base",
        models_dir: Optional[str] = None,
        compute_type: str = "int8",
        device: str = "cpu",
        threads: int = 4,
        on_status_change: Optional[Callable[[str, str], None]] = None,
    ):
        self.model_name = model_name
        self.models_dir = Path(models_dir) if models_dir else Path.home() / ".voxtype" / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.compute_type = compute_type
        self.device = device
        self.threads = threads
        self.on_status_change = on_status_change  # callback(state, message)

        self._model = None
        self._is_loading = False
        self._load_lock = threading.Lock()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def is_model_downloaded(self, model_name: str) -> bool:
        """Checks whether model files already exist locally."""
        # HuggingFace hub creates directory structures named models--Systran--faster-whisper-<name>
        prefix = f"models--Systran--faster-whisper-{model_name}"
        for item in self.models_dir.glob(f"{prefix}*"):
            if item.is_dir():
                # Check for snapshots folder
                snapshots = item / "snapshots"
                if snapshots.exists() and any(snapshots.iterdir()):
                    return True
        # Also check direct folder named model_name
        direct = self.models_dir / model_name
        if direct.is_dir() and (direct / "model.bin").exists():
            return True
        return False

    def get_downloaded_models_info(self) -> Dict[str, Dict]:
        """Returns details on each model variant and its local status."""
        info = {}
        for key, meta in AVAILABLE_MODELS.items():
            is_dl = self.is_model_downloaded(key)
            local_size = self._get_model_disk_size(key) if is_dl else 0
            info[key] = {
                **meta,
                "downloaded": is_dl,
                "local_size_mb": local_size,
                "is_active": (key == self.model_name and self.is_loaded),
            }
        return info

    def _get_model_disk_size(self, model_name: str) -> int:
        """Returns disk usage of model in MB."""
        prefix = f"models--Systran--faster-whisper-{model_name}"
        total_bytes = 0
        for item in self.models_dir.glob(f"{prefix}*"):
            if item.is_dir():
                for root, _, files in os.walk(item):
                    for f in files:
                        try:
                            total_bytes += os.path.getsize(os.path.join(root, f))
                        except Exception:
                            pass
        return int(total_bytes / (1024 * 1024))

    def delete_local_model(self, model_name: str) -> bool:
        """Removes downloaded model to free space."""
        if model_name == self.model_name and self.is_loaded:
            self.unload_model()

        prefix = f"models--Systran--faster-whisper-{model_name}"
        deleted = False
        for item in self.models_dir.glob(f"{prefix}*"):
            if item.is_dir():
                try:
                    shutil.rmtree(item)
                    deleted = True
                except Exception as e:
                    print(f"[WhisperEngine] Failed to delete {item}: {e}")
        return deleted

    def unload_model(self) -> None:
        """Unloads current model from memory."""
        with self._load_lock:
            self._model = None

    def load_model_async(
        self,
        model_name: Optional[str] = None,
        compute_type: Optional[str] = None,
        callback: Optional[Callable[[bool, str], None]] = None,
    ) -> None:
        """Loads Whisper model in a separate thread."""
        target_model = model_name or self.model_name
        target_compute = compute_type or self.compute_type

        def _worker():
            success, msg = self.load_model(target_model, target_compute)
            if callback:
                callback(success, msg)

        threading.Thread(target=_worker, daemon=True).start()

    def load_model(
        self, model_name: Optional[str] = None, compute_type: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Loads Faster-Whisper model into memory."""
        if model_name:
            self.model_name = model_name
        if compute_type:
            self.compute_type = compute_type

        with self._load_lock:
            self._is_loading = True
            if self.on_status_change:
                self.on_status_change(
                    "loading", f"Loading model '{self.model_name}' ({self.compute_type})..."
                )

            start_t = time.time()
            try:
                from faster_whisper import WhisperModel

                print(
                    f"[WhisperEngine] Loading {self.model_name} on {self.device} ({self.compute_type}) with {self.threads} threads..."
                )
                self._model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type,
                    download_root=str(self.models_dir),
                    cpu_threads=self.threads,
                )
                elapsed = time.time() - start_t
                msg = f"Model '{self.model_name}' ready in {elapsed:.2f}s"
                print(f"[WhisperEngine] {msg}")
                self._is_loading = False
                if self.on_status_change:
                    self.on_status_change("ready", msg)
                return True, msg
            except Exception as e:
                self._model = None
                self._is_loading = False
                err_msg = f"Failed to load Whisper model: {e}"
                print(f"[WhisperEngine] {err_msg}")
                if self.on_status_change:
                    self.on_status_change("error", err_msg)
                return False, err_msg

    def transcribe(
        self,
        audio_data: np.ndarray,
        language: str = "auto",
        beam_size: int = 5,
        vad_filter: bool = True,
    ) -> TranscriptionResult:
        """Transcribes 16kHz float32 audio numpy array."""
        if audio_data is None or len(audio_data) == 0:
            return TranscriptionResult(
                text="",
                language=language,
                audio_duration=0.0,
                inference_time=0.0,
                word_count=0,
                char_count=0,
                success=True,
            )

        if self._model is None:
            # Attempt on-demand load
            ok, msg = self.load_model()
            if not ok:
                return TranscriptionResult(
                    text="",
                    language=language,
                    audio_duration=len(audio_data) / 16000.0,
                    inference_time=0.0,
                    word_count=0,
                    char_count=0,
                    success=False,
                    error=msg,
                )

        audio_duration = len(audio_data) / 16000.0
        start_time = time.time()

        try:
            lang_param = None if language == "auto" else language

            # Transcribe with faster-whisper
            segments, info = self._model.transcribe(
                audio_data,
                beam_size=beam_size,
                language=lang_param,
                vad_filter=vad_filter,
                vad_parameters=dict(min_silence_duration_ms=250),
            )

            # Consume generator
            transcribed_segments = []
            for segment in segments:
                transcribed_segments.append(segment.text)

            full_text = " ".join(transcribed_segments).strip()
            inference_time = time.time() - start_time
            detected_lang = info.language if hasattr(info, "language") else language
            words = full_text.split() if full_text else []

            return TranscriptionResult(
                text=full_text,
                language=detected_lang,
                audio_duration=audio_duration,
                inference_time=inference_time,
                word_count=len(words),
                char_count=len(full_text),
                success=True,
            )
        except Exception as e:
            inference_time = time.time() - start_time
            err_msg = f"Transcription error: {e}"
            print(f"[WhisperEngine] {err_msg}")
            return TranscriptionResult(
                text="",
                language=language,
                audio_duration=audio_duration,
                inference_time=inference_time,
                word_count=0,
                char_count=0,
                success=False,
                error=err_msg,
            )

"""
Core functional modules for VoxType voice typing.
"""

from voxtype.core.audio_recorder import AudioRecorder
from voxtype.core.config import AppConfig, ConfigManager
from voxtype.core.hardware import get_hardware_profile
from voxtype.core.hotkey_manager import HotkeyManager
from voxtype.core.sound_effects import SoundEffects
from voxtype.core.text_injector import TextInjector
from voxtype.core.text_processor import TextProcessor
from voxtype.core.whisper_engine import WhisperEngine

__all__ = [
    "AudioRecorder",
    "AppConfig",
    "ConfigManager",
    "get_hardware_profile",
    "HotkeyManager",
    "SoundEffects",
    "TextInjector",
    "TextProcessor",
    "WhisperEngine",
]

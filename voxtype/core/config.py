"""
Configuration manager for VoxType desktop application.
Persists application settings, hotkeys, audio preferences, and model parameters.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_default_config_dir() -> Path:
    """Returns the persistent directory for VoxType settings and models."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        base = Path(appdata) / "VoxType"
    else:
        base = Path.home() / ".voxtype"
    base.mkdir(parents=True, exist_ok=True)
    return base


@dataclass
class ShortcutConfig:
    push_to_talk_key: str = "ctrl_l"  # Default: Left Control
    toggle_recording_key: str = "ctrl+alt+space"
    mode: str = "push_to_talk"  # 'push_to_talk' or 'toggle'


@dataclass
class AudioConfig:
    device_index: Optional[int] = None
    device_name: Optional[str] = None
    sample_rate: int = 16000
    channels: int = 1
    vad_enabled: bool = True
    vad_threshold: float = 0.5
    min_speech_duration_ms: int = 250
    sound_feedback: bool = True


@dataclass
class ModelConfig:
    model_name: str = "base"  # tiny, base, small, medium, large-v3
    language: str = "auto"
    compute_type: str = "int8"  # int8, float16, float32
    device: str = "cpu"
    threads: int = 4
    beam_size: int = 5
    models_dir: Optional[str] = None


@dataclass
class TextConfig:
    auto_capitalize: bool = True
    auto_punctuate: bool = True
    remove_filler_words: bool = True
    filler_words: List[str] = field(
        default_factory=lambda: ["um", "uh", "er", "ah", "hmm"]
    )
    custom_replacements: Dict[str, str] = field(default_factory=dict)
    insertion_mode: str = "sendinput"  # 'sendinput' or 'clipboard_paste'
    typing_delay_ms: int = 2
    add_trailing_space: bool = True
    enable_history: bool = True  # Can be disabled for maximum privacy
    max_history_entries: int = 100


@dataclass
class UIConfig:
    theme: str = "dark"  # 'dark' or 'light'
    show_floating_indicator: bool = True
    floating_position: str = "bottom_center"  # 'bottom_center', 'top_center', 'cursor'
    minimize_to_tray: bool = True
    start_in_tray: bool = False
    start_with_system: bool = False
    window_opacity: float = 0.95


@dataclass
class AppConfig:
    shortcut: ShortcutConfig = field(default_factory=ShortcutConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    text: TextConfig = field(default_factory=TextConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        def filter_kwargs(dataclass_cls, raw_dict):
            valid_keys = dataclass_cls.__dataclass_fields__.keys()
            return {k: v for k, v in raw_dict.items() if k in valid_keys}

        return cls(
            shortcut=ShortcutConfig(**filter_kwargs(ShortcutConfig, data.get("shortcut", {}))),
            audio=AudioConfig(**filter_kwargs(AudioConfig, data.get("audio", {}))),
            model=ModelConfig(**filter_kwargs(ModelConfig, data.get("model", {}))),
            text=TextConfig(**filter_kwargs(TextConfig, data.get("text", {}))),
            ui=UIConfig(**filter_kwargs(UIConfig, data.get("ui", {}))),
        )


class ConfigManager:
    """Handles loading, updating, and saving application settings."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_dir = get_default_config_dir()
        self.config_file = config_path or (self.config_dir / "config.json")
        self.models_dir = self.config_dir / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.config = self.load()

    def load(self) -> AppConfig:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cfg = AppConfig.from_dict(data)
                    if not cfg.model.models_dir:
                        cfg.model.models_dir = str(self.models_dir)
                    return cfg
            except Exception as e:
                print(f"[ConfigManager] Error reading config file: {e}. Using defaults.")

        cfg = AppConfig()
        cfg.model.models_dir = str(self.models_dir)
        self.save(cfg)
        return cfg

    def save(self, config: Optional[AppConfig] = None) -> None:
        if config is not None:
            self.config = config
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config.to_dict(), f, indent=2)
        except Exception as e:
            print(f"[ConfigManager] Failed to save config: {e}")

    def update(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        self.save()

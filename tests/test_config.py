"""
Tests for configuration management and serialization.
"""

import json
from pathlib import Path
import tempfile
from voxtype.core.config import AppConfig, ConfigManager


def test_default_config_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_file = Path(tmpdir) / "config.json"
        mgr = ConfigManager(config_path=cfg_file)

        assert mgr.config.shortcut.push_to_talk_key == "ctrl_l"
        assert mgr.config.shortcut.mode == "push_to_talk"
        assert mgr.config.model.model_name == "base"
        assert mgr.config.model.compute_type == "int8"
        assert mgr.config.ui.theme == "dark"
        assert mgr.config.text.auto_capitalize is True
        assert cfg_file.exists()


def test_config_update_and_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_file = Path(tmpdir) / "config.json"
        mgr = ConfigManager(config_path=cfg_file)

        mgr.config.model.model_name = "tiny"
        mgr.config.shortcut.push_to_talk_key = "caps_lock"
        mgr.config.text.filler_words.append("like")
        mgr.save()

        # Reload from disk
        mgr2 = ConfigManager(config_path=cfg_file)
        assert mgr2.config.model.model_name == "tiny"
        assert mgr2.config.shortcut.push_to_talk_key == "caps_lock"
        assert "like" in mgr2.config.text.filler_words


def test_config_dict_roundtrip():
    cfg = AppConfig()
    d = cfg.to_dict()
    assert isinstance(d, dict)
    reloaded = AppConfig.from_dict(d)
    assert reloaded.shortcut.push_to_talk_key == cfg.shortcut.push_to_talk_key
    assert reloaded.audio.sample_rate == 16000

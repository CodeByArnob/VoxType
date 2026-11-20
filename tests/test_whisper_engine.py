"""
Tests for Whisper model manager and configuration.
"""

from pathlib import Path
import tempfile
from voxtype.core.whisper_engine import AVAILABLE_MODELS, SUPPORTED_LANGUAGES, WhisperEngine


def test_available_models_metadata():
    assert "tiny" in AVAILABLE_MODELS
    assert "base" in AVAILABLE_MODELS
    assert "small" in AVAILABLE_MODELS
    assert "medium" in AVAILABLE_MODELS
    assert "large-v3" in AVAILABLE_MODELS

    for key, info in AVAILABLE_MODELS.items():
        assert "size_mb" in info
        assert "speed" in info
        assert "accuracy" in info


def test_supported_languages():
    lang_dict = dict(SUPPORTED_LANGUAGES)
    assert "auto" in lang_dict
    assert "en" in lang_dict
    assert "es" in lang_dict
    assert "fr" in lang_dict
    assert "de" in lang_dict
    assert "ja" in lang_dict


def test_whisper_engine_init():
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = WhisperEngine(model_name="tiny", models_dir=tmpdir)
        assert engine.model_name == "tiny"
        assert engine.models_dir == Path(tmpdir)
        info = engine.get_downloaded_models_info()
        assert "tiny" in info
        assert info["tiny"]["downloaded"] is False

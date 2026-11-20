"""
Tests for hardware detection.
"""

from voxtype.core.hardware import get_hardware_profile


def test_hardware_profile_detection():
    profile = get_hardware_profile()
    assert profile.logical_cores >= 1
    assert profile.cpu_cores >= 1
    assert profile.os_name in ["Windows", "Linux", "Darwin"]
    assert profile.recommended_model in ["tiny", "base", "small", "medium", "large-v3"]
    assert profile.recommended_compute_type in ["int8", "float16", "float32"]
    assert profile.recommended_threads >= 1

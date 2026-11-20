"""
Hardware detection and performance tuning for VoxType.
Determines optimal CPU threads, compute types, and model suggestions.
"""

import os
import platform
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class HardwareProfile:
    os_name: str
    os_version: str
    cpu_architecture: str
    cpu_cores: int
    logical_cores: int
    has_cuda: bool
    recommended_model: str
    recommended_compute_type: str
    recommended_threads: int
    supported_compute_types: List[str]


def detect_cuda() -> bool:
    """Checks if CUDA is supported and available."""
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        pass

    try:
        import ctranslate2
        return "cuda" in ctranslate2.get_supported_devices()
    except Exception:
        pass

    return False


def get_hardware_profile() -> HardwareProfile:
    """Inspects host machine and recommends optimal settings."""
    os_name = platform.system()
    os_version = platform.release()
    cpu_arch = platform.machine()
    logical_cores = os.cpu_count() or 4
    # Physical cores approximation
    physical_cores = max(1, logical_cores // 2)

    has_cuda = detect_cuda()

    supported_types = ["int8", "float32"]
    if has_cuda:
        supported_types.insert(0, "float16")
        recommended_model = "small"
        recommended_compute_type = "float16"
        recommended_threads = 4
    else:
        # High core CPU (e.g. Ryzen 7 5700G or i7/i9)
        if logical_cores >= 8:
            recommended_model = "base"
            recommended_compute_type = "int8"
            recommended_threads = min(8, logical_cores)
        else:
            recommended_model = "tiny"
            recommended_compute_type = "int8"
            recommended_threads = max(2, logical_cores)

    return HardwareProfile(
        os_name=os_name,
        os_version=os_version,
        cpu_architecture=cpu_arch,
        cpu_cores=physical_cores,
        logical_cores=logical_cores,
        has_cuda=has_cuda,
        recommended_model=recommended_model,
        recommended_compute_type=recommended_compute_type,
        recommended_threads=recommended_threads,
        supported_compute_types=supported_types,
    )

"""
Shared pytest fixtures for VoxType testing.
"""

import os
from pathlib import Path
import sys

# Ensure workspace root is always in sys.path across all platforms and shells
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.processEvents()

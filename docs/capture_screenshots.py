"""
Script to capture genuine, high-resolution screenshots and an animated demonstration GIF
directly from the live VoxType PySide6 application.
"""

import io
import os
import sys
import time
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtCore import QBuffer, QIODevice, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from voxtype.core.config import ConfigManager
from voxtype.ui.floating_indicator import FloatingIndicator
from voxtype.ui.main_window import MainWindow
from voxtype.ui.theme import get_stylesheet

from PIL import Image


def pixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    """Converts a QPixmap to a PIL Image cleanly via QBuffer."""
    buffer = QBuffer()
    buffer.open(QIODevice.ReadWrite)
    pixmap.save(buffer, "PNG")
    data = bytes(buffer.data())
    return Image.open(io.BytesIO(data)).convert("RGBA")


def capture_widget(widget, filepath: Path) -> QPixmap:
    """Captures a high-resolution image of a QWidget directly from Qt rendering."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    widget.repaint()
    QApplication.processEvents()
    pixmap = widget.grab()
    pixmap.save(str(filepath), "PNG")
    print(f"Captured screenshot: {filepath.name} ({pixmap.width()}x{pixmap.height()})")
    return pixmap


def generate_screenshots():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    app.setStyleSheet(get_stylesheet("dark"))

    images_dir = ROOT_DIR / "docs" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Temporary test config
    cfg_mgr = ConfigManager()
    cfg_mgr.config.ui.theme = "dark"
    cfg_mgr.config.shortcut.push_to_talk_key = "ctrl_l"
    cfg_mgr.config.shortcut.mode = "push_to_talk"
    cfg_mgr.config.model.model_name = "base"
    cfg_mgr.config.model.language = "en"
    cfg_mgr.config.text.custom_replacements = {
        "smiley face": "😊",
        "new paragraph": "\n\n",
        "thumbs up": "👍",
    }

    icon_path = ROOT_DIR / "assets" / "icon.png"
    window = MainWindow(cfg_mgr, icon_path)
    window.resize(960, 680)
    window.show()
    QApplication.processEvents()

    # 1. Main Idle
    window.tabs.setCurrentIndex(0)
    window.update_recording_state("idle")
    QApplication.processEvents()
    capture_widget(window, images_dir / "01_main_idle.png")

    # 2. Main Recording / Listening
    window.update_recording_state("listening")
    wave_sample = [0.2, 0.45, 0.8, 0.95, 0.7, 0.4, 0.6, 0.85, 0.9, 0.5, 0.3, 0.75, 0.88, 0.6, 0.35, 0.2]
    window.update_audio_level(0.78, wave_sample)
    QApplication.processEvents()
    capture_widget(window, images_dir / "02_main_recording.png")

    # 3. Main Processing
    window.update_recording_state("processing")
    QApplication.processEvents()
    capture_widget(window, images_dir / "03_main_processing.png")

    # 4. Main Transcribed / Completed with populated history
    window.update_recording_state("success")
    window.add_transcription_result(
        "VoxType converts local speech to text with sub-second latency directly into any active application.",
        15,
        0.384,
    )
    window.add_transcription_result(
        "Holding Left Ctrl starts voice recording instantly without window switching.",
        11,
        0.312,
    )
    window.add_transcription_result(
        "Offline Faster-Whisper inference guarantees complete privacy with zero cloud dependencies.",
        10,
        0.298,
    )
    QApplication.processEvents()
    capture_widget(window, images_dir / "04_main_transcribed.png")

    # 5. Models Tab
    window.tabs.setCurrentIndex(1)
    QApplication.processEvents()
    capture_widget(window, images_dir / "05_models_manager.png")

    # 6. Audio Devices Tab with VU Meter
    window.tabs.setCurrentIndex(2)
    window._is_testing_mic = True
    window.vu_meter.set_level(0.68)
    QApplication.processEvents()
    capture_widget(window, images_dir / "06_audio_devices.png")

    # 7. Shortcuts Tab
    window.tabs.setCurrentIndex(3)
    QApplication.processEvents()
    capture_widget(window, images_dir / "07_shortcuts_config.png")

    # 8. Formatting Tab
    window.tabs.setCurrentIndex(4)
    QApplication.processEvents()
    capture_widget(window, images_dir / "08_formatting_rules.png")

    # 9. Settings & About Tab
    window.tabs.setCurrentIndex(5)
    QApplication.processEvents()
    capture_widget(window, images_dir / "09_settings_about.png")

    # Floating Indicator Captures
    indicator = FloatingIndicator()
    indicator.resize(320, 56)

    # 10. Floating Indicator - Listening
    indicator.show_listening()
    indicator.update_audio_level(0.72)
    indicator._wave_bars = [0.3, 0.6, 0.85, 0.95, 0.7, 0.45, 0.65, 0.8]
    indicator._elapsed_str = "00:03"
    indicator.show()
    QApplication.processEvents()
    capture_widget(indicator, images_dir / "10_floating_indicator_listening.png")

    # 11. Floating Indicator - Processing
    indicator.show_processing()
    QApplication.processEvents()
    capture_widget(indicator, images_dir / "11_floating_indicator_processing.png")

    # 12. Floating Indicator - Completed
    indicator.show_completed(18, 0.412)
    QApplication.processEvents()
    capture_widget(indicator, images_dir / "12_floating_indicator_completed.png")

    # Generate Animated Demo GIF: voxtype_demo.gif
    print("Generating animated demonstration GIF...")
    generate_demo_gif(window, images_dir / "voxtype_demo.gif")

    indicator.deleteLater()
    window.deleteLater()
    QApplication.processEvents()
    print("All genuine screenshots and demo GIF generated successfully!")


def generate_demo_gif(window: MainWindow, gif_path: Path):
    """Generates an authentic multi-frame animated GIF simulating a complete push-to-talk dictation cycle."""
    frames = []
    durations = []

    window.tabs.setCurrentIndex(0)
    window.resize(920, 660)

    # Phase 1: Idle state (5 frames)
    window.update_recording_state("idle")
    for _ in range(5):
        QApplication.processEvents()
        pix = window.grab()
        img = pixmap_to_pil(pix)
        frames.append(img)
        durations.append(180)

    # Phase 2: Key Down -> Listening (12 frames with varying waveforms)
    window.update_recording_state("listening")
    wave_frames = [
        [0.1, 0.2, 0.3, 0.25, 0.15, 0.2, 0.25, 0.3, 0.2, 0.1, 0.15, 0.2, 0.25, 0.2, 0.1, 0.05],
        [0.2, 0.4, 0.6, 0.5, 0.3, 0.45, 0.7, 0.65, 0.4, 0.3, 0.5, 0.6, 0.45, 0.3, 0.2, 0.1],
        [0.35, 0.65, 0.85, 0.75, 0.55, 0.7, 0.9, 0.8, 0.6, 0.5, 0.75, 0.85, 0.7, 0.5, 0.3, 0.2],
        [0.5, 0.8, 0.98, 0.9, 0.7, 0.85, 0.95, 0.9, 0.75, 0.65, 0.9, 0.95, 0.8, 0.6, 0.4, 0.25],
        [0.4, 0.7, 0.9, 0.8, 0.6, 0.75, 0.88, 0.82, 0.68, 0.55, 0.8, 0.88, 0.72, 0.52, 0.32, 0.18],
        [0.25, 0.5, 0.75, 0.65, 0.45, 0.6, 0.8, 0.72, 0.5, 0.4, 0.65, 0.75, 0.6, 0.4, 0.25, 0.15],
        [0.45, 0.75, 0.95, 0.88, 0.68, 0.8, 0.92, 0.86, 0.7, 0.6, 0.85, 0.92, 0.78, 0.58, 0.38, 0.22],
        [0.3, 0.6, 0.82, 0.72, 0.52, 0.68, 0.84, 0.76, 0.58, 0.48, 0.72, 0.82, 0.66, 0.46, 0.28, 0.16],
        [0.2, 0.4, 0.62, 0.52, 0.35, 0.48, 0.65, 0.58, 0.42, 0.32, 0.52, 0.62, 0.48, 0.32, 0.2, 0.1],
        [0.15, 0.3, 0.45, 0.38, 0.25, 0.35, 0.5, 0.42, 0.3, 0.22, 0.38, 0.48, 0.35, 0.22, 0.15, 0.08],
        [0.1, 0.2, 0.3, 0.25, 0.18, 0.22, 0.32, 0.28, 0.2, 0.15, 0.25, 0.3, 0.22, 0.15, 0.1, 0.05],
        [0.08, 0.15, 0.2, 0.18, 0.12, 0.15, 0.22, 0.18, 0.14, 0.1, 0.16, 0.2, 0.15, 0.1, 0.06, 0.03],
    ]
    for w in wave_frames:
        avg_lvl = sum(w) / len(w)
        window.update_audio_level(avg_lvl, w)
        QApplication.processEvents()
        pix = window.grab()
        img = pixmap_to_pil(pix)
        frames.append(img)
        durations.append(140)

    # Phase 3: Key Up -> Processing (8 frames)
    window.update_recording_state("processing")
    for _ in range(8):
        QApplication.processEvents()
        pix = window.grab()
        img = pixmap_to_pil(pix)
        frames.append(img)
        durations.append(150)

    # Phase 4: Success / Transcribed (12 frames)
    window.update_recording_state("success")
    window.add_transcription_result(
        "VoxType is fast, private, and types into any application with sub-second latency.",
        13,
        0.342,
    )
    for _ in range(12):
        QApplication.processEvents()
        pix = window.grab()
        img = pixmap_to_pil(pix)
        frames.append(img)
        durations.append(220)

    # Save as optimized GIF (downsampled to 820px width for fast loading on GitHub)
    processed_frames = []
    target_width = 820
    for frame in frames:
        rgb_frame = frame.convert("RGB")
        w, h = rgb_frame.size
        target_height = int(h * (target_width / w))
        resized = rgb_frame.resize((target_width, target_height), Image.Resampling.LANCZOS)
        quantized = resized.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
        processed_frames.append(quantized)

    if processed_frames:
        processed_frames[0].save(
            str(gif_path),
            save_all=True,
            append_images=processed_frames[1:],
            optimize=True,
            duration=durations,
            loop=0,
        )
        print(f"Generated demo GIF: {gif_path.name} ({len(processed_frames)} frames, {os.path.getsize(gif_path) / 1024:.1f} KB)")


if __name__ == "__main__":
    generate_screenshots()

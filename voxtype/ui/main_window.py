"""
Main desktop window for VoxType voice typing application.
Redesigned with senior desktop UX standards, focused voice typing view,
model manager with cancellation, real-time audio calibration,
interactive shortcut recorder, and privacy controls.
"""

from datetime import datetime
from pathlib import Path
import threading
from typing import Dict, List, Optional

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from voxtype.core.config import AppConfig, ConfigManager
from voxtype.core.hardware import get_hardware_profile
from voxtype.core.hotkey_manager import format_shortcut_display
from voxtype.core.whisper_engine import AVAILABLE_MODELS, SUPPORTED_LANGUAGES, WhisperEngine
from voxtype.ui.components.animated_mic_button import AnimatedMicButton
from voxtype.ui.components.shortcut_recorder import ShortcutRecorderWidget
from voxtype.ui.components.vu_meter import VUMeter
from voxtype.ui.components.waveform_widget import WaveformWidget
from voxtype.ui.theme import get_stylesheet


class MainWindow(QMainWindow):
    """Main VoxType application window."""

    request_toggle_recording = Signal()
    request_model_change = Signal(str, str)
    request_device_change = Signal(int)
    request_test_mic = Signal(bool)
    request_shortcut_change = Signal(str, str)
    request_reinject_text = Signal(str)

    def __init__(self, config_manager: ConfigManager, icon_path: Path):
        super().__init__()
        self.config_manager = config_manager
        self.config = config_manager.config
        self.icon_path = icon_path

        # Requirement 1: Native window title must be strictly "VoxType"
        self.setWindowTitle("VoxType")
        self.setMinimumSize(880, 640)
        self.resize(940, 680)

        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.total_words_typed = 0
        self.transcription_history: List[Dict] = []
        self._is_testing_mic = False
        self._download_cancel_events: Dict[str, threading.Event] = {}

        self._init_ui()
        self.apply_theme(self.config.ui.theme)

    def _init_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 14, 20, 14)
        main_layout.setSpacing(12)

        # Application Header
        header = self._create_header()
        main_layout.addWidget(header)

        # Top Navigation Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tab_dashboard = self._create_dashboard_tab()
        self.tab_models = self._create_models_tab()
        self.tab_audio = self._create_audio_tab()
        self.tab_shortcuts = self._create_shortcuts_tab()
        self.tab_text = self._create_text_tab()
        self.tab_about = self._create_about_tab()

        self.tabs.addTab(self.tab_dashboard, "Voice Typing")
        self.tabs.addTab(self.tab_models, "Models")
        self.tabs.addTab(self.tab_audio, "Audio Devices")
        self.tabs.addTab(self.tab_shortcuts, "Shortcuts")
        self.tabs.addTab(self.tab_text, "Formatting")
        self.tabs.addTab(self.tab_about, "Settings & About")

        main_layout.addWidget(self.tabs)

        # Status Bar
        status_bar = self._create_status_bar()
        main_layout.addWidget(status_bar)

    def _create_header(self) -> QWidget:
        header = QFrame()
        header.setProperty("class", "HeaderFrame")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(4, 4, 4, 8)

        # Logo and Title
        title_box = QVBoxLayout()
        title_box.setSpacing(1)

        app_title = QLabel("VoxType")
        app_title.setStyleSheet("font-size: 19px; font-weight: 800; color: #F8FAFC; letter-spacing: -0.4px;")

        subtitle = QLabel("Local Voice Typing")
        subtitle.setStyleSheet("font-size: 11px; color: #38BDF8; font-weight: 600; letter-spacing: 0.3px;")

        title_box.addWidget(app_title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        layout.addStretch()

        # Engine Status Pill
        self.engine_status_pill = QLabel("● Faster-Whisper Ready")
        self.engine_status_pill.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.12);
            color: #10B981;
            font-size: 11px;
            font-weight: 700;
            padding: 5px 12px;
            border-radius: 12px;
            border: 1px solid rgba(16, 185, 129, 0.3);
        """)
        layout.addWidget(self.engine_status_pill)

        # Active Shortcut Pill
        display_key = format_shortcut_display(self.config.shortcut.push_to_talk_key)
        mode_label = "Hold" if self.config.shortcut.mode == "push_to_talk" else "Toggle"
        self.shortcut_pill = QLabel(f"{display_key} [{mode_label}]")
        self.shortcut_pill.setStyleSheet("""
            background-color: #0F172A;
            color: #38BDF8;
            font-size: 11px;
            font-weight: 700;
            padding: 5px 12px;
            border-radius: 12px;
            border: 1px solid #1E2B45;
        """)
        layout.addWidget(self.shortcut_pill)

        # Local & Offline Badge
        offline_badge = QLabel("100% Offline")
        offline_badge.setStyleSheet("""
            background-color: #0F172A;
            color: #94A3B8;
            font-size: 11px;
            font-weight: 600;
            padding: 5px 10px;
            border-radius: 12px;
            border: 1px solid #1E2B45;
        """)
        layout.addWidget(offline_badge)

        return header

    def _create_dashboard_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(6, 14, 6, 6)
        layout.setSpacing(14)

        # Hero Voice Typing Panel
        hero_card = QFrame()
        hero_card.setObjectName("HeroCard")
        hero_card.setStyleSheet("""
            QFrame#HeroCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0D1424, stop:1 #080C14);
                border: 1px solid #1E2B45;
                border-radius: 16px;
                padding: 18px;
            }
        """)
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setAlignment(Qt.AlignCenter)
        hero_layout.setSpacing(10)

        # Animated Mic Button
        self.mic_button = AnimatedMicButton()
        self.mic_button.clicked.connect(self.request_toggle_recording.emit)
        hero_layout.addWidget(self.mic_button, alignment=Qt.AlignCenter)

        # Status text
        self.hero_status_lbl = QLabel(self._get_default_prompt_text())
        self.hero_status_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #F8FAFC;")
        hero_layout.addWidget(self.hero_status_lbl, alignment=Qt.AlignCenter)

        self.hero_sub_lbl = QLabel("Works in any focused application • Or click microphone to start")
        self.hero_sub_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")
        hero_layout.addWidget(self.hero_sub_lbl, alignment=Qt.AlignCenter)

        # Waveform Visualizer
        self.waveform_widget = WaveformWidget(num_bars=32)
        hero_layout.addWidget(self.waveform_widget)

        layout.addWidget(hero_card)

        # Context Info Strip (Real hardware status)
        info_strip = QFrame()
        info_strip.setProperty("class", "SurfaceCard")
        is_layout = QHBoxLayout(info_strip)
        is_layout.setContentsMargins(12, 8, 12, 8)
        is_layout.setSpacing(16)

        # Active Model
        self.strip_model_lbl = QLabel(f"<b>Model:</b> {self.config.model.model_name.capitalize()} ({self.config.model.compute_type})")
        self.strip_model_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")
        is_layout.addWidget(self.strip_model_lbl)

        # Active Device
        self.strip_device_lbl = QLabel("<b>Microphone:</b> System Default")
        self.strip_device_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")
        is_layout.addWidget(self.strip_device_lbl)

        # Mode
        self.strip_mode_lbl = QLabel(f"<b>Mode:</b> {'Hold-to-Talk' if self.config.shortcut.mode == 'push_to_talk' else 'Toggle-to-Talk'}")
        self.strip_mode_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")
        is_layout.addWidget(self.strip_mode_lbl)

        is_layout.addStretch()

        # Session Metrics (Displayed only when real data exists)
        self.session_metrics_lbl = QLabel("")
        self.session_metrics_lbl.setStyleSheet("font-size: 11px; color: #38BDF8; font-weight: 600;")
        is_layout.addWidget(self.session_metrics_lbl)

        layout.addWidget(info_strip)

        # Recent Transcriptions Log & Safe Recovery
        history_card = QFrame()
        history_card.setProperty("class", "SurfaceCard")
        h_layout = QVBoxLayout(history_card)
        h_layout.setContentsMargins(14, 10, 14, 10)
        h_layout.setSpacing(8)

        h_header = QHBoxLayout()
        h_title = QLabel("Recent Transcriptions (Local Recovery)")
        h_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #F8FAFC;")
        h_header.addWidget(h_title)
        h_header.addStretch()

        self.copy_last_btn = QPushButton("Copy Last")
        self.copy_last_btn.setEnabled(False)
        self.copy_last_btn.clicked.connect(self._copy_last_transcription)
        h_header.addWidget(self.copy_last_btn)

        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(self._clear_history)
        h_header.addWidget(clear_btn)

        h_layout.addLayout(h_header)

        # Empty state label or table
        self.empty_history_lbl = QLabel("No voice typings yet in this session. Hold your shortcut in any app to begin.")
        self.empty_history_lbl.setStyleSheet("font-size: 12px; color: #64748B; padding: 16px;")
        self.empty_history_lbl.setAlignment(Qt.AlignCenter)
        h_layout.addWidget(self.empty_history_lbl)

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["Time", "Words", "Speed", "Transcribed Text", "Action"])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SingleSelection)
        self.history_table.setMaximumHeight(130)
        self.history_table.setVisible(False)

        h_layout.addWidget(self.history_table)
        layout.addWidget(history_card)

        return tab

    def _get_default_prompt_text(self) -> str:
        key_str = format_shortcut_display(self.config.shortcut.push_to_talk_key)
        if self.config.shortcut.mode == "push_to_talk":
            return f"Hold {key_str} to speak, release to type"
        else:
            return f"Press {key_str} to start typing"

    def _create_models_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 14, 8, 14)
        layout.setSpacing(14)

        # Hardware Recommendation Banner
        profile = get_hardware_profile()
        hw_banner = QFrame()
        hw_banner.setProperty("class", "ElevatedCard")
        hw_banner.setStyleSheet("border-left: 3px solid #38BDF8;")
        hw_layout = QHBoxLayout(hw_banner)
        hw_text = QLabel(
            f"<b>Hardware Profile:</b> {profile.logical_cores} logical CPU cores ({profile.cpu_architecture}). "
            f"Optimized for <b>{profile.recommended_model.capitalize()} ({profile.recommended_compute_type})</b>"
        )
        hw_text.setStyleSheet("color: #F8FAFC; font-size: 12px;")
        hw_layout.addWidget(hw_text)
        layout.addWidget(hw_banner)

        # Model Config Row (Language & Quantization)
        cfg_frame = QFrame()
        cfg_frame.setProperty("class", "SurfaceCard")
        cf_grid = QGridLayout(cfg_frame)
        cf_grid.setSpacing(12)

        cf_grid.addWidget(QLabel("Spoken Language:"), 0, 0)
        self.lang_combo = QComboBox()
        for code, name in SUPPORTED_LANGUAGES:
            self.lang_combo.addItem(f"{name} ({code})", code)
        idx = self.lang_combo.findData(self.config.model.language)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        cf_grid.addWidget(self.lang_combo, 0, 1)

        cf_grid.addWidget(QLabel("Compute Quantization:"), 0, 2)
        self.compute_combo = QComboBox()
        for ct in ["int8", "float32", "float16"]:
            self.compute_combo.addItem(ct, ct)
        c_idx = self.compute_combo.findData(self.config.model.compute_type)
        if c_idx >= 0:
            self.compute_combo.setCurrentIndex(c_idx)
        self.compute_combo.currentIndexChanged.connect(self._on_compute_changed)
        cf_grid.addWidget(self.compute_combo, 0, 3)

        layout.addWidget(cfg_frame)

        # Available Whisper Models Cards
        models_lbl = QLabel("Faster-Whisper Model Variants")
        models_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #F8FAFC;")
        layout.addWidget(models_lbl)

        self.model_cards_layout = QVBoxLayout()
        self.model_cards_layout.setSpacing(10)
        layout.addLayout(self.model_cards_layout)

        self._populate_model_cards()

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _populate_model_cards(self) -> None:
        while self.model_cards_layout.count():
            item = self.model_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        engine = WhisperEngine(
            model_name=self.config.model.model_name,
            models_dir=self.config.model.models_dir,
        )
        models_info = engine.get_downloaded_models_info()

        for key, info in models_info.items():
            card = QFrame()
            card.setProperty("class", "SurfaceCard")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(14, 12, 14, 12)
            c_layout.setSpacing(8)

            row = QHBoxLayout()
            name_lbl = QLabel(f"Whisper {info['name']}")
            name_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #F8FAFC;")
            row.addWidget(name_lbl)

            if key == self.config.model.model_name:
                active_badge = QLabel("ACTIVE")
                active_badge.setStyleSheet("background: #38BDF8; color: #080C14; font-weight: 800; font-size: 10px; padding: 2px 7px; border-radius: 4px;")
                row.addWidget(active_badge)

            if info["downloaded"]:
                dl_badge = QLabel(f"Installed ({info['local_size_mb']} MB)")
                dl_badge.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 600;")
                row.addWidget(dl_badge)
            else:
                avail_badge = QLabel("Ready to Download")
                avail_badge.setStyleSheet("color: #94A3B8; font-size: 11px;")
                row.addWidget(avail_badge)

            row.addStretch()

            # Actions
            if key == self.config.model.model_name:
                ready_btn = QPushButton("Current Model")
                ready_btn.setEnabled(False)
                row.addWidget(ready_btn)
            else:
                select_btn = QPushButton("Select Model")
                select_btn.clicked.connect(lambda checked=False, m=key: self._switch_model(m))
                row.addWidget(select_btn)

            if info["downloaded"]:
                del_btn = QPushButton("Delete")
                del_btn.setProperty("class", "DangerButton")
                del_btn.clicked.connect(lambda checked=False, m=key: self._delete_model(m))
                row.addWidget(del_btn)
            else:
                dl_btn = QPushButton("Download")
                dl_btn.clicked.connect(lambda checked=False, m=key, c=card: self._download_model(m, c))
                row.addWidget(dl_btn)

            c_layout.addLayout(row)

            desc = QLabel(f"{info['description']} • Size: ~{info['size_mb']} MB • Speed: {info['speed']}")
            desc.setStyleSheet("font-size: 12px; color: #94A3B8;")
            c_layout.addWidget(desc)

            self.model_cards_layout.addWidget(card)

    def _switch_model(self, model_key: str) -> None:
        self.config.model.model_name = model_key
        self.config_manager.save()
        self.strip_model_lbl.setText(f"<b>Model:</b> {model_key.capitalize()} ({self.config.model.compute_type})")
        self._populate_model_cards()
        self.request_model_change.emit(model_key, self.config.model.compute_type)

    def _delete_model(self, model_key: str) -> None:
        engine = WhisperEngine(models_dir=self.config.model.models_dir)
        engine.delete_local_model(model_key)
        self._populate_model_cards()

    def _download_model(self, model_key: str, card_widget: QFrame) -> None:
        # Add live progress bar to card
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(10)
        card_widget.layout().addWidget(progress_bar)

        cancel_btn = QPushButton("Cancel")
        card_widget.layout().addWidget(cancel_btn)

        cancel_event = threading.Event()
        self._download_cancel_events[model_key] = cancel_event

        cancel_btn.clicked.connect(lambda: cancel_event.set())

        engine = WhisperEngine(models_dir=self.config.model.models_dir)

        def on_prog(pct, msg):
            QTimer.singleShot(0, lambda: progress_bar.setValue(pct))

        def on_done(success, msg):
            def _update():
                self._populate_model_cards()
                if success:
                    self.engine_status_pill.setText(f"● {model_key.capitalize()} Downloaded")
            QTimer.singleShot(0, _update)

        engine.download_model_async(
            model_key,
            on_progress=on_prog,
            on_finished=on_done,
            cancel_event=cancel_event,
        )

    def _on_language_changed(self) -> None:
        lang = self.lang_combo.currentData()
        self.config.model.language = lang
        self.config_manager.save()

    def _on_compute_changed(self) -> None:
        compute = self.compute_combo.currentData()
        self.config.model.compute_type = compute
        self.config_manager.save()
        self.strip_model_lbl.setText(f"<b>Model:</b> {self.config.model.model_name.capitalize()} ({compute})")
        self.request_model_change.emit(self.config.model.model_name, compute)

    def _create_audio_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 14, 8, 14)
        layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "SurfaceCard")
        dc_layout = QVBoxLayout(card)
        dc_layout.setSpacing(12)

        dc_title = QLabel("Microphone Selection & Calibration")
        dc_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #F8FAFC;")
        dc_layout.addWidget(dc_title)

        combo_row = QHBoxLayout()
        self.device_combo = QComboBox()
        self._populate_audio_devices()
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        combo_row.addWidget(self.device_combo, stretch=1)

        refresh_btn = QPushButton("Refresh Devices")
        refresh_btn.clicked.connect(self._populate_audio_devices)
        combo_row.addWidget(refresh_btn)

        perm_btn = QPushButton("Verify Permission")
        perm_btn.clicked.connect(self._check_permission)
        combo_row.addWidget(perm_btn)

        dc_layout.addLayout(combo_row)

        self.perm_status_lbl = QLabel("Microphone access ready")
        self.perm_status_lbl.setStyleSheet("font-size: 11px; color: #10B981; font-weight: 600;")
        dc_layout.addWidget(self.perm_status_lbl)

        # Real-time VU Meter Calibration
        meter_label = QLabel("Microphone Live Input Calibration:")
        meter_label.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 600;")
        dc_layout.addWidget(meter_label)

        self.vu_meter = VUMeter()
        dc_layout.addWidget(self.vu_meter)

        test_row = QHBoxLayout()
        self.test_mic_btn = QPushButton("Start Level Test")
        self.test_mic_btn.clicked.connect(self._toggle_mic_test)
        test_row.addWidget(self.test_mic_btn)
        test_row.addStretch()
        dc_layout.addLayout(test_row)

        layout.addWidget(card)

        # Audio options
        opts_card = QFrame()
        opts_card.setProperty("class", "SurfaceCard")
        o_layout = QVBoxLayout(opts_card)
        o_layout.setSpacing(10)

        o_title = QLabel("Audio Detection Options")
        o_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #F8FAFC;")
        o_layout.addWidget(o_title)

        self.cb_sound_feedback = QCheckBox("Auditory Feedback (Subtle synthesized chimes on start, stop, and success)")
        self.cb_sound_feedback.setChecked(self.config.audio.sound_feedback)
        self.cb_sound_feedback.stateChanged.connect(self._on_sound_feedback_changed)
        o_layout.addWidget(self.cb_sound_feedback)

        self.cb_vad = QCheckBox("Voice Activity Detection (Filter out background noise & silence)")
        self.cb_vad.setChecked(self.config.audio.vad_enabled)
        self.cb_vad.stateChanged.connect(self._on_vad_changed)
        o_layout.addWidget(self.cb_vad)

        layout.addWidget(opts_card)
        layout.addStretch()
        return tab

    def _populate_audio_devices(self) -> None:
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self.device_combo.addItem("Default System Microphone", None)

        from voxtype.core.audio_recorder import AudioRecorder
        devices = AudioRecorder.list_input_devices()
        selected_idx = 0

        for i, (idx, name, is_default) in enumerate(devices):
            label = f"{name} [Default]" if is_default else name
            self.device_combo.addItem(label, idx)
            if self.config.audio.device_index == idx:
                selected_idx = i + 1

        self.device_combo.setCurrentIndex(selected_idx)
        self.device_combo.blockSignals(False)

    def _on_device_changed(self) -> None:
        idx = self.device_combo.currentData()
        name = self.device_combo.currentText()
        self.config.audio.device_index = idx
        self.config.audio.device_name = name
        self.config_manager.save()
        self.strip_device_lbl.setText(f"<b>Microphone:</b> {name.split('[')[0].strip()}")
        self.request_device_change.emit(idx if idx is not None else -1)

    def _check_permission(self) -> None:
        from voxtype.core.audio_recorder import AudioRecorder
        ok, msg = AudioRecorder.check_microphone_permission()
        if ok:
            self.perm_status_lbl.setText(f"✓ {msg}")
            self.perm_status_lbl.setStyleSheet("font-size: 11px; color: #10B981; font-weight: 600;")
        else:
            self.perm_status_lbl.setText(f"⚠️ {msg}")
            self.perm_status_lbl.setStyleSheet("font-size: 11px; color: #EF4444; font-weight: 600;")

    def _toggle_mic_test(self) -> None:
        self._is_testing_mic = not self._is_testing_mic
        if self._is_testing_mic:
            self.test_mic_btn.setText("Stop Level Test")
            self.request_test_mic.emit(True)
        else:
            self.test_mic_btn.setText("Start Level Test")
            self.vu_meter.set_level(0.0)
            self.request_test_mic.emit(False)

    def _on_sound_feedback_changed(self, state: int) -> None:
        self.config.audio.sound_feedback = (state == Qt.Checked.value or state == 2)
        self.config_manager.save()

    def _on_vad_changed(self, state: int) -> None:
        self.config.audio.vad_enabled = (state == Qt.Checked.value or state == 2)
        self.config_manager.save()

    def _create_shortcuts_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 14, 8, 14)
        layout.setSpacing(14)

        # Embed Shortcut Recorder Component
        self.shortcut_recorder = ShortcutRecorderWidget(
            current_shortcut=self.config.shortcut.push_to_talk_key,
            current_mode=self.config.shortcut.mode,
        )
        self.shortcut_recorder.shortcut_changed.connect(self._on_shortcut_recorded)
        layout.addWidget(self.shortcut_recorder)

        # Operating System integration guide
        guide_card = QFrame()
        guide_card.setProperty("class", "SurfaceCard")
        g_layout = QVBoxLayout(guide_card)
        g_layout.setSpacing(6)

        g_title = QLabel("System Integration & Global Shortcut Rules")
        g_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #38BDF8;")
        g_layout.addWidget(g_title)

        body = QLabel(
            "• <b>Hold-to-Talk (Default):</b> Hold Left Ctrl while speaking in any application (Word, Chrome, Slack, VS Code). "
            "Releasing the key transcribes speech offline and inserts text directly at your active cursor.<br>"
            "• <b>Toggle-to-Talk:</b> Press the key once to record. Press it again to stop and type.<br>"
            "• <b>Left vs Right Ctrl:</b> Left Ctrl and Right Ctrl are distinguished automatically to prevent accidental triggers."
        )
        body.setTextFormat(Qt.RichText)
        body.setStyleSheet("font-size: 12px; color: #94A3B8; line-height: 1.5;")
        g_layout.addWidget(body)

        layout.addWidget(guide_card)
        layout.addStretch()
        return tab

    def _on_shortcut_recorded(self, shortcut_str: str, mode: str) -> None:
        self.config.shortcut.push_to_talk_key = shortcut_str
        self.config.shortcut.mode = mode
        self.config_manager.save()

        display_key = format_shortcut_display(shortcut_str)
        mode_label = "Hold" if mode == "push_to_talk" else "Toggle"
        self.shortcut_pill.setText(f"{display_key} [{mode_label}]")
        self.strip_mode_lbl.setText(f"<b>Mode:</b> {'Hold-to-Talk' if mode == 'push_to_talk' else 'Toggle-to-Talk'}")
        self.hero_status_lbl.setText(self._get_default_prompt_text())

        self.request_shortcut_change.emit(shortcut_str, mode)

    def on_hotkey_test_event(self, is_pressed: bool, is_matched: bool) -> None:
        if hasattr(self, "shortcut_recorder"):
            self.shortcut_recorder.set_test_feedback(is_pressed, is_matched)

    def _create_text_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 14, 8, 14)
        layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "SurfaceCard")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        title = QLabel("Formatting & Punctuation Rules")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #F8FAFC;")
        c_layout.addWidget(title)

        self.cb_capitalize = QCheckBox("Auto-capitalize first letter of sentences")
        self.cb_capitalize.setChecked(self.config.text.auto_capitalize)
        self.cb_capitalize.stateChanged.connect(self._on_text_opts_changed)
        c_layout.addWidget(self.cb_capitalize)

        self.cb_punctuate = QCheckBox("Auto-format punctuation and clean duplicate spaces")
        self.cb_punctuate.setChecked(self.config.text.auto_punctuate)
        self.cb_punctuate.stateChanged.connect(self._on_text_opts_changed)
        c_layout.addWidget(self.cb_punctuate)

        self.cb_fillers = QCheckBox("Remove filler words ('um', 'uh', 'er', 'ah', 'hmm')")
        self.cb_fillers.setChecked(self.config.text.remove_filler_words)
        self.cb_fillers.stateChanged.connect(self._on_text_opts_changed)
        c_layout.addWidget(self.cb_fillers)

        self.cb_trailing_space = QCheckBox("Add trailing space after transcribed text for continuous dictation")
        self.cb_trailing_space.setChecked(self.config.text.add_trailing_space)
        self.cb_trailing_space.stateChanged.connect(self._on_text_opts_changed)
        c_layout.addWidget(self.cb_trailing_space)

        # Insertion mode
        ins_row = QHBoxLayout()
        ins_row.addWidget(QLabel("Text Insertion Engine:"))
        self.ins_combo = QComboBox()
        self.ins_combo.addItem("Native Keystroke Simulation (SendInput Unicode)", "sendinput")
        self.ins_combo.addItem("Clipboard Paste Fallback (Ctrl+V with auto-restore)", "clipboard_paste")
        i_idx = self.ins_combo.findData(self.config.text.insertion_mode)
        if i_idx >= 0:
            self.ins_combo.setCurrentIndex(i_idx)
        self.ins_combo.currentIndexChanged.connect(self._on_ins_mode_changed)
        ins_row.addWidget(self.ins_combo, stretch=1)
        c_layout.addLayout(ins_row)

        layout.addWidget(card)

        # Custom Phrase Replacements Table
        rep_card = QFrame()
        rep_card.setProperty("class", "SurfaceCard")
        rc_layout = QVBoxLayout(rep_card)
        rc_layout.setSpacing(10)

        rc_title = QLabel("Custom Voice Shortcuts & Replacements")
        rc_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #F8FAFC;")
        rc_layout.addWidget(rc_title)

        self.rep_table = QTableWidget(0, 2)
        self.rep_table.setHorizontalHeaderLabels(["When I Speak", "Insert This Instead"])
        self.rep_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._populate_replacements_table()
        rc_layout.addWidget(self.rep_table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Voice Replacement")
        add_btn.clicked.connect(self._add_replacement_dialog)
        btn_row.addWidget(add_btn)

        del_btn = QPushButton("Remove Selected")
        del_btn.clicked.connect(self._remove_replacement)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()

        rc_layout.addLayout(btn_row)
        layout.addWidget(rep_card)

        layout.addStretch()
        return tab

    def _populate_replacements_table(self) -> None:
        self.rep_table.setRowCount(0)
        for phrase, rep in self.config.text.custom_replacements.items():
            row = self.rep_table.rowCount()
            self.rep_table.insertRow(row)
            self.rep_table.setItem(row, 0, QTableWidgetItem(phrase))
            self.rep_table.setItem(row, 1, QTableWidgetItem(rep))

    def _add_replacement_dialog(self) -> None:
        phrase, ok1 = QInputDialog_getText(self, "Add Voice Shortcut", "When I speak phrase:")
        if ok1 and phrase.strip():
            rep, ok2 = QInputDialog_getText(self, "Add Voice Shortcut", f"Insert this text for '{phrase}':")
            if ok2:
                self.config.text.custom_replacements[phrase.strip().lower()] = rep
                self.config_manager.save()
                self._populate_replacements_table()

    def _remove_replacement(self) -> None:
        selected = self.rep_table.currentRow()
        if selected >= 0:
            phrase_item = self.rep_table.item(selected, 0)
            if phrase_item:
                phrase = phrase_item.text().strip().lower()
                self.config.text.custom_replacements.pop(phrase, None)
                self.config_manager.save()
                self._populate_replacements_table()

    def _on_text_opts_changed(self) -> None:
        self.config.text.auto_capitalize = self.cb_capitalize.isChecked()
        self.config.text.auto_punctuate = self.cb_punctuate.isChecked()
        self.config.text.remove_filler_words = self.cb_fillers.isChecked()
        self.config.text.add_trailing_space = self.cb_trailing_space.isChecked()
        self.config_manager.save()

    def _on_ins_mode_changed(self) -> None:
        mode = self.ins_combo.currentData()
        self.config.text.insertion_mode = mode
        self.config_manager.save()

    def _create_about_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 14, 8, 14)
        layout.setSpacing(14)

        # Privacy and Retention Preferences
        privacy_card = QFrame()
        privacy_card.setProperty("class", "SurfaceCard")
        p_layout = QVBoxLayout(privacy_card)
        p_layout.setSpacing(10)

        p_title = QLabel("Privacy & History Retention")
        p_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #F8FAFC;")
        p_layout.addWidget(p_title)

        self.cb_history = QCheckBox("Save recent transcriptions in session history (for clipboard recovery)")
        self.cb_history.setChecked(self.config.text.enable_history)
        self.cb_history.stateChanged.connect(self._on_history_toggle)
        p_layout.addWidget(self.cb_history)

        p_desc = QLabel("If disabled, transcriptions are typed directly into your active application and immediately discarded from memory.")
        p_desc.setStyleSheet("font-size: 11px; color: #94A3B8;")
        p_layout.addWidget(p_desc)

        layout.addWidget(privacy_card)

        # Desktop Behavior Preferences
        pref_card = QFrame()
        pref_card.setProperty("class", "SurfaceCard")
        pc_layout = QVBoxLayout(pref_card)
        pc_layout.setSpacing(10)

        pc_title = QLabel("Desktop Experience")
        pc_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #F8FAFC;")
        pc_layout.addWidget(pc_title)

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Color Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark Theme (Default)", "dark")
        self.theme_combo.addItem("Light Theme", "light")
        t_idx = self.theme_combo.findData(self.config.ui.theme)
        if t_idx >= 0:
            self.theme_combo.setCurrentIndex(t_idx)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self.theme_combo, stretch=1)
        pc_layout.addLayout(theme_row)

        self.cb_indicator = QCheckBox("Show compact floating recording indicator pill overlay")
        self.cb_indicator.setChecked(self.config.ui.show_floating_indicator)
        self.cb_indicator.stateChanged.connect(self._on_ui_opts_changed)
        pc_layout.addWidget(self.cb_indicator)

        self.cb_tray = QCheckBox("Minimize to system tray on window close")
        self.cb_tray.setChecked(self.config.ui.minimize_to_tray)
        self.cb_tray.stateChanged.connect(self._on_ui_opts_changed)
        pc_layout.addWidget(self.cb_tray)

        layout.addWidget(pref_card)

        # About Card
        about_card = QFrame()
        about_card.setProperty("class", "SurfaceCard")
        ac_layout = QVBoxLayout(about_card)
        ac_layout.setSpacing(6)

        ac_title = QLabel("VoxType")
        ac_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #38BDF8;")
        ac_layout.addWidget(ac_title)

        author_lbl = QLabel("Created by Arnobrazz")
        author_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #60A5FA;")
        ac_layout.addWidget(author_lbl)

        meta_info = QLabel(
            "• Version: 1.0.0 Production Release\n"
            "• Open Source License: MIT License\n"
            "• GitHub Repository: github.com/CodeByArnob/VoxType\n"
            "• Core Engine: Faster-Whisper (Local & Private CTranslate2)\n"
            "• Privacy Architecture: 100% Offline, Zero Cloud Dependencies"
        )
        meta_info.setStyleSheet("font-size: 11px; color: #94A3B8; line-height: 1.6;")
        ac_layout.addWidget(meta_info)

        layout.addWidget(about_card)
        layout.addStretch()
        return tab

    def _on_history_toggle(self, state: int) -> None:
        enabled = (state == Qt.Checked.value or state == 2)
        self.config.text.enable_history = enabled
        self.config_manager.save()
        if not enabled:
            self._clear_history()

    def _on_theme_changed(self) -> None:
        theme = self.theme_combo.currentData()
        self.config.ui.theme = theme
        self.config_manager.save()
        self.apply_theme(theme)

    def _on_ui_opts_changed(self) -> None:
        self.config.ui.show_floating_indicator = self.cb_indicator.isChecked()
        self.config.ui.minimize_to_tray = self.cb_tray.isChecked()
        self.config_manager.save()

    def _create_status_bar(self) -> QWidget:
        bar = QFrame()
        bar.setStyleSheet("background-color: #0D1322; border-radius: 8px; padding: 4px 10px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(6, 2, 6, 2)

        self.status_lbl = QLabel("Ready • Hold Left Ctrl to type anywhere")
        self.status_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
        layout.addWidget(self.status_lbl)

        layout.addStretch()

        self.engine_status_lbl = QLabel("Faster-Whisper Ready")
        self.engine_status_lbl.setStyleSheet("font-size: 11px; color: #10B981; font-weight: 600;")
        layout.addWidget(self.engine_status_lbl)

        return bar

    def apply_theme(self, theme_name: str) -> None:
        self.setStyleSheet(get_stylesheet(theme_name))

    def update_recording_state(self, state: str, text: Optional[str] = None) -> None:
        self.mic_button.set_state(state)
        self.waveform_widget.set_active(state == "listening")

        if state == "listening":
            self.hero_status_lbl.setText("Listening... Speak clearly")
            self.hero_sub_lbl.setText("Release key (or click microphone) when finished speaking")
            self.status_lbl.setText("Recording in progress...")
        elif state == "processing":
            self.hero_status_lbl.setText("Transcribing speech locally with Faster-Whisper...")
            self.hero_sub_lbl.setText("Processing audio frame...")
            self.status_lbl.setText("Transcribing...")
        elif state in ("success", "completed"):
            self.hero_status_lbl.setText("✓ Text inserted at active cursor position!")
            self.hero_sub_lbl.setText("Ready for next phrase")
            self.status_lbl.setText("Success")
        elif state == "error":
            self.hero_status_lbl.setText(text or "No speech detected")
            self.hero_sub_lbl.setText("Check microphone or hold key while speaking")
            self.status_lbl.setText("Error / Silence")
        else:
            self.hero_status_lbl.setText(self._get_default_prompt_text())
            self.hero_sub_lbl.setText("Works in any focused application • Or click microphone to start")
            self.status_lbl.setText("Ready • Hold shortcut to type anywhere")

    def update_audio_level(self, level: float, wave_points: Optional[List[float]] = None) -> None:
        self.mic_button.set_audio_level(level, wave_points)
        self.waveform_widget.update_audio_data(level, wave_points)
        if self._is_testing_mic:
            self.vu_meter.set_level(level)

    def add_transcription_result(self, text: str, word_count: int, latency_s: float) -> None:
        if not text:
            return

        self.total_words_typed += word_count
        measured_ms = int(latency_s * 1000)
        self.session_metrics_lbl.setText(f"Session: {self.total_words_typed} words • Last: {measured_ms}ms")

        if not self.config.text.enable_history:
            return

        now_str = datetime.now().strftime("%H:%M:%S")

        self.empty_history_lbl.setVisible(False)
        self.history_table.setVisible(True)
        self.copy_last_btn.setEnabled(True)

        row = 0
        self.history_table.insertRow(row)
        self.history_table.setItem(row, 0, QTableWidgetItem(now_str))
        self.history_table.setItem(row, 1, QTableWidgetItem(f"{word_count}w"))
        self.history_table.setItem(row, 2, QTableWidgetItem(f"{measured_ms}ms"))
        self.history_table.setItem(row, 3, QTableWidgetItem(text))

        # Action button to copy
        action_btn = QPushButton("Copy")
        action_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        action_btn.clicked.connect(lambda checked=False, t=text: self._copy_text(t))
        self.history_table.setCellWidget(row, 4, action_btn)

        self.transcription_history.insert(0, {
            "time": now_str,
            "words": word_count,
            "latency": latency_s,
            "text": text,
        })

    def _copy_last_transcription(self) -> None:
        if self.transcription_history:
            self._copy_text(self.transcription_history[0]["text"])

    def _copy_text(self, text: str) -> None:
        import pyperclip
        pyperclip.copy(text)
        self.status_lbl.setText("✓ Copied to clipboard!")
        QTimer.singleShot(1500, lambda: self.status_lbl.setText("Ready • Hold shortcut to type anywhere"))

    def _clear_history(self) -> None:
        self.history_table.setRowCount(0)
        self.transcription_history.clear()
        self.history_table.setVisible(False)
        self.empty_history_lbl.setVisible(True)
        self.copy_last_btn.setEnabled(False)

    def closeEvent(self, event) -> None:
        if self.config.ui.minimize_to_tray:
            event.ignore()
            self.hide()
        else:
            event.accept()


def QInputDialog_getText(parent, title, prompt):
    """Simple dialog for capturing text phrases."""
    from PySide6.QtWidgets import QInputDialog
    return QInputDialog.getText(parent, title, prompt)

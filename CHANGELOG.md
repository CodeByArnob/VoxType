# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-20

### Added
- **Official Product Website**: Production-ready responsive website deployed to GitHub Pages (`https://codebyarnob.github.io/VoxType/`) with interactive push-to-talk playground, authentic screen captures, Faster-Whisper benchmarks, tabbed installer guide, FAQ accordion, SEO metadata, and automated GitHub Actions deployment.
- **Production Architecture**: Complete event-driven desktop voice typing application built with PySide6 and Faster-Whisper.
- **Physical Modifier Discrimination**: Global low-level keyboard hook distinguishing physical Left Ctrl (`VK_LCONTROL = 162`) from Right Ctrl (`VK_RCONTROL = 163`).
- **Push-to-Talk & Toggle Modes**: Reliable Hold-to-Talk (record while holding key, transcribe on release) and Toggle-to-Talk modes.
- **Offline Faster-Whisper Engine**: Full local CTranslate2 inference supporting Tiny, Base, Small, Medium, and Large Whisper variants.
- **Local Model Manager**: In-app download with cancellation support, local disk usage calculation, and model deletion.
- **Hardware-Aware Optimizer**: Automatic CPU thread profiling (optimal intra-threads) and compute quantization recommendation (`int8`, `float32`).
- **Universal Text Injection**: Active window tracking via Win32 `GetForegroundWindow`/`SetForegroundWindow`, native Unicode `SendInput` simulation, and non-destructive clipboard paste fallback.
- **Floating Overlay Pill**: Compact, non-focus-stealing floating indicator (`310x52`) with real-time audio waveform visualizer and stopwatch timer.
- **Audio Device & Calibration**: In-app microphone selector, microphone permission verification, and real-time VU meter calibration.
- **Interactive Shortcut Recorder**: Live key-combination capture widget with conflict detection and live press feedback test pad.
- **Custom Voice Shortcuts**: Formatting rules for capitalization, punctuation, filler word removal, and user-defined phrase replacements.
- **Privacy & Retention Settings**: Zero-retention option to discard transcriptions immediately from memory, with optional local recovery clipboard cache.
- **Synthesized Audio Feedback**: In-memory WAV chime feedback for recording start, stop, and insertion without external audio assets.
- **Comprehensive Test Suite**: 42 unit and integration tests covering application lifecycle, audio recording, hotkey triggers, text formatting, and engine management.

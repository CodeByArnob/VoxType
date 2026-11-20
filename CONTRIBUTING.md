# Contributing to VoxType

Thank you for your interest in contributing to VoxType! VoxType is an open-source, local, privacy-first desktop voice typing utility.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/CodeByArnob/VoxType.git
   cd VoxType
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies in editable mode:**
   ```bash
   pip install --upgrade pip
   pip install -e .
   pip install pytest pytest-cov
   ```

## Running the Test Suite

Run the full automated test suite using pytest:

```bash
pytest -v
```

Before submitting changes, ensure all tests pass cleanly.

## Running the Application Locally

```bash
python run.py
```

## Architecture Guidelines

- **Zero Cloud Leakage:** All speech recognition must run locally via Faster-Whisper. Never introduce network calls or remote API endpoints for transcription.
- **Physical Modifier Discrimination:** Modifier hotkeys (such as Left Ctrl vs Right Ctrl) must be explicitly discriminated using platform virtual key codes to prevent hotkey conflicts.
- **Strict Application Branding:** The application and native window title must be strictly `"VoxType"`. Never append em dashes or subtitle strings to the window title.
- **Safe Text Injection:** Direct keystroke simulation (`SendInput` Unicode) is the primary method, with non-destructive clipboard restore as the fallback. Never silently lose transcribed text.

## Pull Request Guidelines

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Keep commits concise and meaningful following conventional commits (`feat:`, `fix:`, `docs:`, `test:`).
3. Open a pull request against `main` describing your changes and verification steps.

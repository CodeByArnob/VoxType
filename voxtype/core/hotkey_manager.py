"""
Intelligent global keyboard shortcut manager for VoxType.
Distinguishes Left from Right modifiers (Ctrl, Alt, Shift), supports single-key
and combination shortcuts, implements Hold-to-Talk and Toggle-to-Talk modes,
and includes conflict detection and interactive recording support.
"""

import threading
import time
from typing import Callable, List, Optional, Set

from pynput import keyboard


KNOWN_CONFLICTS = {
    "ctrl+c": "Standard Windows Copy shortcut",
    "ctrl+v": "Standard Windows Paste shortcut",
    "ctrl+x": "Standard Windows Cut shortcut",
    "ctrl+z": "Standard Windows Undo shortcut",
    "ctrl+a": "Standard Windows Select All shortcut",
    "ctrl+s": "Standard Windows Save shortcut",
    "ctrl+f": "Standard Windows Find shortcut",
    "ctrl+w": "Standard Windows Close Window/Tab shortcut",
    "alt+f4": "Standard Windows Close Application shortcut",
    "alt+tab": "Windows Task Switcher",
    "ctrl+alt+delete": "Windows Security Attention Sequence",
    "ctrl+shift+esc": "Windows Task Manager shortcut",
}


def get_canonical_key(key) -> str:
    """Normalizes key events with strict Left vs Right discrimination."""
    # Virtual key code check for Windows Left/Right differentiation
    vk = getattr(key, "vk", None)
    if vk == 162:
        return "ctrl_l"
    if vk == 163:
        return "ctrl_r"
    if vk == 164:
        return "alt_l"
    if vk == 165:
        return "alt_r"
    if vk == 160:
        return "shift_l"
    if vk == 161:
        return "shift_r"
    if vk == 20:
        return "caps_lock"

    if hasattr(key, "name") and key.name:
        name = key.name.lower()
        if name in ("ctrl_l", "ctrl_r", "alt_l", "alt_r", "shift_l", "shift_r", "caps_lock"):
            return name
        if name == "ctrl":
            return "ctrl_l"
        if name in ("alt", "alt_gr"):
            return "alt_l"
        if name == "shift":
            return "shift_l"
        return name

    if hasattr(key, "char") and key.char:
        return key.char.lower()

    return str(key).lower().replace("key.", "").replace("'", "")


def format_shortcut_display(shortcut_str: str) -> str:
    """Formats a shortcut string for clean human-readable UI display."""
    if not shortcut_str:
        return "Not Set"

    tokens = [t.strip().lower() for t in shortcut_str.split("+") if t.strip()]
    labels = []
    for token in tokens:
        if token == "ctrl_l":
            labels.append("Left Ctrl")
        elif token == "ctrl_r":
            labels.append("Right Ctrl")
        elif token == "alt_l":
            labels.append("Left Alt")
        elif token == "alt_r":
            labels.append("Right Alt")
        elif token == "shift_l":
            labels.append("Left Shift")
        elif token == "shift_r":
            labels.append("Right Shift")
        elif token == "caps_lock":
            labels.append("Caps Lock")
        elif token.startswith("f") and token[1:].isdigit():
            labels.append(token.upper())
        elif token == "space":
            labels.append("Space")
        else:
            labels.append(token.capitalize())

    return " + ".join(labels)


def detect_shortcut_conflicts(shortcut_str: str) -> Optional[str]:
    """Checks whether a shortcut conflicts with common operating system bindings."""
    clean = shortcut_str.lower().replace("ctrl_l", "ctrl").replace("ctrl_r", "ctrl")
    clean = clean.replace("alt_l", "alt").replace("alt_r", "alt")
    clean = clean.replace("shift_l", "shift").replace("shift_r", "shift")

    # Check reserved shortcuts
    for conflict_key, reason in KNOWN_CONFLICTS.items():
        if clean == conflict_key:
            return f"Conflicts with {reason}."

    # Check bare single alphanumeric key
    if len(clean) == 1 and clean.isalnum():
        return (
            f"Using a single alphanumeric character '{clean.upper()}' will trigger voice typing "
            f"whenever you type that letter. A modifier key (such as Left Ctrl) is strongly recommended."
        )

    return None


class HotkeyManager:
    """System-wide keyboard shortcut listener for Hold-to-Talk and Toggle-to-Talk."""

    def __init__(
        self,
        shortcut: str = "ctrl_l",
        mode: str = "push_to_talk",  # 'push_to_talk' or 'toggle'
        on_start_recording: Optional[Callable[[], None]] = None,
        on_stop_recording: Optional[Callable[[], None]] = None,
    ):
        self.mode = mode  # 'push_to_talk' or 'toggle'
        self.on_start_recording = on_start_recording
        self.on_stop_recording = on_stop_recording

        self._listener: Optional[keyboard.Listener] = None
        self._target_keys: List[str] = []
        self.set_shortcut(shortcut)

        self._currently_held: Set[str] = set()
        self._is_recording_active = False
        self._is_running = False
        self._lock = threading.Lock()

        # Optional test callback for shortcut tester UI: callback(is_pressed, is_matched)
        self.test_callback: Optional[Callable[[bool, bool], None]] = None

    def set_shortcut(self, shortcut_str: str) -> None:
        """Sets target shortcut (single key or '+'-delimited combination)."""
        tokens = [t.strip().lower() for t in shortcut_str.split("+") if t.strip()]
        self._target_keys = tokens if tokens else ["ctrl_l"]

    def get_shortcut_str(self) -> str:
        return "+".join(self._target_keys)

    def set_mode(self, mode: str) -> None:
        """Configures 'push_to_talk' (Hold-to-Talk) or 'toggle' (Toggle-to-Talk)."""
        self.mode = mode

    def _is_target_fully_held(self) -> bool:
        """Returns True if every required key in the target shortcut is held down."""
        if not self._target_keys:
            return False
        return all(k in self._currently_held for k in self._target_keys)

    def _on_press(self, key):
        canonical = get_canonical_key(key)

        with self._lock:
            # Prevent OS key-repeat events while key is held down
            if canonical in self._currently_held:
                return
            self._currently_held.add(canonical)
            fully_held = self._is_target_fully_held()

        if self.test_callback:
            self.test_callback(True, fully_held)

        if not self._is_running or not fully_held:
            return

        with self._lock:
            if self.mode == "push_to_talk":
                if not self._is_recording_active:
                    self._is_recording_active = True
                    trigger_start = True
                else:
                    trigger_start = False
                trigger_stop = False

            elif self.mode == "toggle":
                if not self._is_recording_active:
                    self._is_recording_active = True
                    trigger_start = True
                    trigger_stop = False
                else:
                    self._is_recording_active = False
                    trigger_start = False
                    trigger_stop = True
            else:
                trigger_start = False
                trigger_stop = False

        if trigger_start and self.on_start_recording:
            self.on_start_recording()
        elif trigger_stop and self.on_stop_recording:
            self.on_stop_recording()

    def _on_release(self, key):
        canonical = get_canonical_key(key)

        with self._lock:
            self._currently_held.discard(canonical)
            was_recording = self._is_recording_active
            is_relevant_key = canonical in self._target_keys

        if self.test_callback:
            self.test_callback(False, False)

        if not self._is_running:
            return

        # In Hold-to-Talk mode, releasing ANY key of the shortcut stops recording
        if self.mode == "push_to_talk" and was_recording and is_relevant_key:
            with self._lock:
                self._is_recording_active = False
            if self.on_stop_recording:
                self.on_stop_recording()

    def notify_external_stop(self) -> None:
        """Informs the hotkey manager that recording was stopped externally (e.g. by GUI click)."""
        with self._lock:
            self._is_recording_active = False

    def start(self) -> None:
        """Starts global keyboard monitoring."""
        if self._listener is not None:
            return

        self._is_running = True
        self._is_recording_active = False
        self._currently_held.clear()

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        """Stops global keyboard monitoring."""
        self._is_running = False
        self._is_recording_active = False
        self._currently_held.clear()

        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

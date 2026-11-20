"""
Text injector for typing transcribed text into the currently active application.
Supports Windows SendInput (Unicode) and seamless Clipboard Paste fallback.
"""

import ctypes
from ctypes import wintypes
import time
from typing import Optional


# Windows SendInput structures
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

VK_CONTROL = 0x11
VK_V = 0x56


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]

    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]


user32 = ctypes.windll.user32


class TextInjector:
    """Inserts transcribed text into the active foreground window."""

    def __init__(self, mode: str = "sendinput", delay_ms: int = 2):
        self.mode = mode  # 'sendinput' or 'clipboard_paste'
        self.delay_ms = delay_ms
        self.last_injected_text = ""
        self._target_hwnd: Optional[int] = None

    def capture_foreground_window(self) -> int:
        """Remembers current active window handle before any popup takes focus."""
        try:
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                self._target_hwnd = hwnd
            return hwnd
        except Exception:
            return 0

    def restore_target_window(self) -> None:
        """Ensures the original target application has focus before typing."""
        if not self._target_hwnd:
            return
        try:
            current = user32.GetForegroundWindow()
            if current != self._target_hwnd:
                user32.SetForegroundWindow(self._target_hwnd)
                time.sleep(0.04)
        except Exception:
            pass

    def inject(self, text: str, mode: Optional[str] = None) -> bool:
        """Main entry point: injects text into active window."""
        if not text:
            return True

        self.last_injected_text = text
        active_mode = mode or self.mode

        self.restore_target_window()

        success = False
        if active_mode == "sendinput":
            success = self._inject_via_sendinput(text)
            if not success:
                # Automatic fallback to clipboard paste
                success = self._inject_via_clipboard(text)
        else:
            success = self._inject_via_clipboard(text)
            if not success:
                success = self._inject_via_sendinput(text)

        return success

    def _inject_via_sendinput(self, text: str) -> bool:
        """Simulates native keyboard Unicode inputs."""
        try:
            inputs = []
            for char in text:
                if char == "\n":
                    # Enter key
                    ki_down = KEYBDINPUT(wVk=0x0D, wScan=0, dwFlags=0, time=0, dwExtraInfo=None)
                    ki_up = KEYBDINPUT(wVk=0x0D, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)
                elif char == "\t":
                    # Tab key
                    ki_down = KEYBDINPUT(wVk=0x09, wScan=0, dwFlags=0, time=0, dwExtraInfo=None)
                    ki_up = KEYBDINPUT(wVk=0x09, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)
                else:
                    # Unicode character
                    code = ord(char)
                    ki_down = KEYBDINPUT(
                        wVk=0,
                        wScan=code,
                        dwFlags=KEYEVENTF_UNICODE,
                        time=0,
                        dwExtraInfo=None,
                    )
                    ki_up = KEYBDINPUT(
                        wVk=0,
                        wScan=code,
                        dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                        time=0,
                        dwExtraInfo=None,
                    )

                inp_down = INPUT(type=INPUT_KEYBOARD)
                inp_down.ki = ki_down
                inp_up = INPUT(type=INPUT_KEYBOARD)
                inp_up.ki = ki_up

                inputs.extend([inp_down, inp_up])

            if not inputs:
                return True

            n = len(inputs)
            arr = (INPUT * n)(*inputs)
            res = user32.SendInput(n, arr, ctypes.sizeof(INPUT))
            return res == n
        except Exception as e:
            print(f"[TextInjector] SendInput failed: {e}")
            return False

    def _inject_via_clipboard(self, text: str) -> bool:
        """Pastes text via Ctrl+V while preserving previous clipboard contents."""
        try:
            import pyperclip

            original_clipboard = None
            try:
                original_clipboard = pyperclip.paste()
            except Exception:
                pass

            pyperclip.copy(text)
            time.sleep(0.02)

            # Send Ctrl+V
            self._send_ctrl_v()
            time.sleep(0.05)

            # Restore original clipboard
            if original_clipboard is not None:
                try:
                    pyperclip.copy(original_clipboard)
                except Exception:
                    pass

            return True
        except Exception as e:
            print(f"[TextInjector] Clipboard paste failed: {e}")
            return False

    def _send_ctrl_v(self) -> None:
        """Sends native Ctrl+V key combination."""
        ctrl_down = INPUT(type=INPUT_KEYBOARD)
        ctrl_down.ki = KEYBDINPUT(wVk=VK_CONTROL, wScan=0, dwFlags=0, time=0, dwExtraInfo=None)

        v_down = INPUT(type=INPUT_KEYBOARD)
        v_down.ki = KEYBDINPUT(wVk=VK_V, wScan=0, dwFlags=0, time=0, dwExtraInfo=None)

        v_up = INPUT(type=INPUT_KEYBOARD)
        v_up.ki = KEYBDINPUT(wVk=VK_V, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)

        ctrl_up = INPUT(type=INPUT_KEYBOARD)
        ctrl_up.ki = KEYBDINPUT(wVk=VK_CONTROL, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)

        events = [ctrl_down, v_down, v_up, ctrl_up]
        arr = (INPUT * len(events))(*events)
        user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))

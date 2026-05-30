"""
core/global_hotkey.py — Глобальный хоткей (Windows).

Поддерживает одиночные клавиши (F12, CapsLock) и комбинации (Ctrl+Space).
Использует QAbstractNativeEventFilter для перехвата WM_HOTKEY.
"""

from __future__ import annotations

import sys
from PySide6.QtCore import QObject, Signal, QAbstractNativeEventFilter, QByteArray
from PySide6.QtWidgets import QApplication

WM_HOTKEY = 0x0312
_HOTKEY_ID = 9901

_VK_MAP: dict[str, int] = {
    "space": 0x20, "tab": 0x09,
    "escape": 0x1B, "esc": 0x1B,
    "insert": 0x2D, "ins": 0x2D,
    "delete": 0x2E, "del": 0x2E,
    "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pgup": 0x21,
    "pagedown": 0x22, "pgdn": 0x22,
    "backspace": 0x08, "back": 0x08,
    "return": 0x0D, "enter": 0x0D,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "`": 0xC0, "~": 0xC0,
    # Одиночные спец-клавиши
    "capslock": 0x14, "caps": 0x14,
    "numlock": 0x90, "scrolllock": 0x91,
    "printscreen": 0x2C, "prtsc": 0x2C,
    "pause": 0x13,
    # Win регистрируется через MOD_WIN + vk=0 → особый случай ниже
    "win": 0x5B,  # VK_LWIN
}


class _WinEventFilter(QAbstractNativeEventFilter):

    def __init__(self, callback):
        super().__init__()
        self._cb = callback

    def nativeEventFilter(self, event_type: QByteArray | bytes, message):
        if sys.platform != "win32":
            return False, 0
        if bytes(event_type) != b"windows_generic_MSG":
            return False, 0
        try:
            import ctypes
            from ctypes import wintypes
            msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
            if msg.message == WM_HOTKEY and msg.wParam == _HOTKEY_ID:
                self._cb()
                return True, 0
        except Exception:
            pass
        return False, 0


def _parse_combo(combo: str) -> tuple[int, int]:
    """Парсит 'Ctrl+Space', 'F12', 'CapsLock' → (mods, vk)."""
    MOD_ALT = 0x0001
    MOD_CTRL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008
    MOD_NOREPEAT = 0x4000

    parts = [p.strip().lower() for p in combo.replace("+", " ").split()]
    mods = MOD_NOREPEAT
    vk = 0

    for part in parts:
        if part in ("ctrl", "control"):
            mods |= MOD_CTRL
        elif part == "alt":
            mods |= MOD_ALT
        elif part == "shift":
            mods |= MOD_SHIFT
        elif part in ("win", "meta", "super", "lwin", "rwin"):
            # Win как модификатор если есть другие клавиши
            # или как одиночная клавиша
            if len(parts) == 1:
                vk = 0x5B  # VK_LWIN
            else:
                mods |= MOD_WIN
        elif part.startswith("f") and part[1:].isdigit():
            n = int(part[1:])
            if 1 <= n <= 24:
                vk = 0x6F + n
        elif part in _VK_MAP:
            vk = _VK_MAP[part]
        elif len(part) == 1 and part.isalnum():
            vk = ord(part.upper())
        elif len(part) == 1:
            vk = ord(part)

    return (mods, vk) if vk else (0, 0)


class GlobalHotkey(QObject):
    triggered = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._registered = False
        self._filter: _WinEventFilter | None = None

    def register(self, combo: str) -> bool:
        self.unregister()
        if not combo:
            return False
        if sys.platform == "win32":
            return self._register_win32(combo)
        return False

    def unregister(self):
        if self._filter:
            app = QApplication.instance()
            if app:
                app.removeNativeEventFilter(self._filter)
            self._filter = None
        if self._registered and sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.UnregisterHotKey(None, _HOTKEY_ID)
            except Exception:
                pass
        self._registered = False

    def _register_win32(self, combo: str) -> bool:
        try:
            import ctypes

            mods, vk = _parse_combo(combo)
            if not vk:
                print(f"[Hotkey] Cannot parse: {combo}")
                return False

            user32 = ctypes.windll.user32
            user32.UnregisterHotKey(None, _HOTKEY_ID)

            ok = user32.RegisterHotKey(None, _HOTKEY_ID, mods, vk)
            if not ok:
                err = ctypes.GetLastError()
                print(f"[Hotkey] RegisterHotKey failed: {combo} (err={err})")
                return False

            self._registered = True
            self._filter = _WinEventFilter(lambda: self.triggered.emit())
            app = QApplication.instance()
            if app:
                app.installNativeEventFilter(self._filter)

            print(f"[Hotkey] OK: {combo} (mods=0x{mods:X} vk=0x{vk:X})")
            return True
        except Exception as e:
            print(f"[Hotkey] Error: {e}")
            return False

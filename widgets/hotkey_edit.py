"""
widgets/hotkey_edit.py — Захват горячей клавиши нажатием.

Поддерживает одиночные клавиши (F12, CapsLock) и комбинации (Ctrl+Space).
"""

from __future__ import annotations

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence

from core.i18n import t

# Клавиши-модификаторы, которые НЕЛЬЗЯ назначить одиночно через Qt
# (Ctrl, Shift, Alt). Но CapsLock и Win — МОЖНО.
_PURE_MODS = {
    Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_AltGr,
}

# Специальные клавиши → читаемое имя для global_hotkey парсера
_SPECIAL_NAMES: dict[int, str] = {
    Qt.Key.Key_CapsLock: "CapsLock",
    Qt.Key.Key_Meta: "Win",          # Win / Super / Meta
    Qt.Key.Key_Super_L: "Win",
    Qt.Key.Key_Super_R: "Win",
    Qt.Key.Key_Space: "Space",
    Qt.Key.Key_Tab: "Tab",
    Qt.Key.Key_Escape: "Esc",
    Qt.Key.Key_Insert: "Insert",
    Qt.Key.Key_Delete: "Delete",
    Qt.Key.Key_Home: "Home",
    Qt.Key.Key_End: "End",
    Qt.Key.Key_PageUp: "PageUp",
    Qt.Key.Key_PageDown: "PageDown",
    Qt.Key.Key_Backspace: "Backspace",
    Qt.Key.Key_Return: "Enter",
    Qt.Key.Key_Enter: "Enter",
    Qt.Key.Key_Up: "Up",
    Qt.Key.Key_Down: "Down",
    Qt.Key.Key_Left: "Left",
    Qt.Key.Key_Right: "Right",
    Qt.Key.Key_QuoteLeft: "`",
}


class HotkeyEdit(QPushButton):
    """
    Клик → режим записи → нажми клавишу/комбинацию → готово.
    Escape — отмена. Поле пустое — отключено.
    """

    hotkey_changed = Signal(str)

    def __init__(self, current: str = "", parent=None):
        super().__init__(parent)
        self._combo = current
        self._recording = False
        self.setFixedHeight(34)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._update_text()
        self.clicked.connect(self._start)

    @property
    def combo(self) -> str:
        return self._combo

    def set_combo(self, val: str):
        self._combo = val
        self._update_text()

    def _update_text(self):
        if self._recording:
            self.setText(f"⏺  {t('hk_press')}")
            self.setStyleSheet(
                "QPushButton{background:rgba(59,130,246,12);color:#93c5fd;"
                "border:1px solid rgba(59,130,246,50);border-radius:7px;"
                "padding:5px 10px;font-size:12px;text-align:left;}")
        elif self._combo:
            self.setText(f"  {self._combo}")
            self.setStyleSheet(
                "QPushButton{background:rgba(255,255,255,6);color:white;"
                "border:1px solid rgba(255,255,255,12);border-radius:7px;"
                "padding:5px 10px;font-size:12px;text-align:left;}")
        else:
            self.setText(t("hk_empty"))
            self.setStyleSheet(
                "QPushButton{background:rgba(255,255,255,6);color:rgba(255,255,255,35);"
                "border:1px solid rgba(255,255,255,12);border-radius:7px;"
                "padding:5px 10px;font-size:12px;text-align:left;}")

    def _start(self):
        self._recording = True
        self._update_text()
        self.grabKeyboard()

    def keyPressEvent(self, event: QKeyEvent):
        if not self._recording:
            super().keyPressEvent(event)
            return

        key = event.key()

        # Escape — отмена
        if key == Qt.Key.Key_Escape:
            self._finish()
            return

        # Delete — очистить
        if key == Qt.Key.Key_Delete:
            self._combo = ""
            self._finish()
            self.hotkey_changed.emit("")
            return

        # Чистые модификаторы (Ctrl/Shift/Alt) — ждём основную клавишу
        if key in _PURE_MODS:
            return

        # Собираем модификаторы
        parts: list[str] = []
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            parts.append("Ctrl")
        if mods & Qt.KeyboardModifier.AltModifier:
            parts.append("Alt")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            parts.append("Shift")

        # Имя клавиши
        if key in _SPECIAL_NAMES:
            parts.append(_SPECIAL_NAMES[key])
        else:
            name = QKeySequence(key).toString()
            if name:
                parts.append(name)

        if parts:
            self._combo = "+".join(parts)
            self._finish()
            self.hotkey_changed.emit(self._combo)

    def _finish(self):
        self._recording = False
        self.releaseKeyboard()
        self._update_text()

    def focusOutEvent(self, event):
        if self._recording:
            self._finish()
        super().focusOutEvent(event)

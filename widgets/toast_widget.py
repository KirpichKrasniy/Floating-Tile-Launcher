"""
widgets/toast_widget.py — Toast-уведомления.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath


_COLORS = {
    "info":    QColor(59, 130, 246, 230),
    "success": QColor(34, 197, 94, 230),
    "error":   QColor(239, 68, 68, 230),
    "warning": QColor(245, 158, 11, 230),
}

_ICONS = {"info": "ℹ", "success": "✓", "error": "✕", "warning": "⚠"}


class ToastWidget(QWidget):

    def __init__(self, message: str, toast_type: str = "info",
                 duration: int = 3000, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedHeight(44)
        self.setMinimumWidth(200)

        self._bg_color = _COLORS.get(toast_type, _COLORS["info"])
        icon = _ICONS.get(toast_type, "ℹ")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        lbl = QLabel(f"  {icon}   {message}")
        lbl.setStyleSheet("color: white; font-size: 13px; font-weight: 500;")
        layout.addWidget(lbl)

        self.adjustSize()
        self.setFixedWidth(max(self.sizeHint().width() + 32, 220))

        self._opacity_fx = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_fx)

        self._fade_in = QPropertyAnimation(self._opacity_fx, b"opacity")
        self._fade_in.setDuration(200)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_out = QPropertyAnimation(self._opacity_fx, b"opacity")
        self._fade_out.setDuration(300)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self._on_done)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(duration)
        self._timer.timeout.connect(self._fade_out.start)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 12, 12)
        painter.fillPath(path, self._bg_color)
        painter.end()

    def show_toast(self, x: int, y: int):
        self.move(x, y)
        self.show()
        self._fade_in.start()
        self._timer.start()

    def _on_done(self):
        self.close()
        self.deleteLater()


class ToastManager:

    def __init__(self, parent: QWidget):
        self._parent = parent
        self._active: list[ToastWidget] = []

    def show(self, message: str, toast_type: str = "info", duration: int = 3000):
        toast = ToastWidget(message, toast_type, duration)
        toast.destroyed.connect(lambda: self._remove(toast))
        self._active.append(toast)
        self._reposition()
        pos = self._calc_pos(toast)
        toast.show_toast(pos.x(), pos.y())

    def _remove(self, toast: ToastWidget):
        if toast in self._active:
            self._active.remove(toast)
            self._reposition()

    def _calc_pos(self, toast: ToastWidget) -> QPoint:
        geo = self._parent.geometry()
        idx = self._active.index(toast) if toast in self._active else 0
        x = geo.right() - toast.width() - 20
        y = geo.bottom() - (idx + 1) * (toast.height() + 8) - 20
        return QPoint(x, y)

    def _reposition(self):
        for t in self._active:
            t.move(self._calc_pos(t))

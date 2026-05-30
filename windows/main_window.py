"""
windows/main_window.py — Главное окно.
"""

from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QGraphicsOpacityEffect, QApplication,
    QSystemTrayIcon, QMenu as QTrayMenu,
)
from PySide6.QtCore import (
    Qt, QPoint, QPropertyAnimation, QEasingCurve, QEvent, QRectF, QTimer,
)
from PySide6.QtGui import (
    QColor, QPainter, QPainterPath, QLinearGradient, QRadialGradient,
    QMouseEvent, QBrush, QIcon, QPixmap,
)

from core.config_manager import ConfigManager
from core.global_hotkey import GlobalHotkey
from core.i18n import t
from widgets.grid_manager import GridManager
from widgets.toast_widget import ToastManager
from windows.settings_window import SettingsWindow
from windows.add_tile_dialog import AddTileDialog

_PAD_H = 32
_PAD_V = 44


class MainWindow(QMainWindow):

    def __init__(self, config_mgr: ConfigManager):
        super().__init__()
        self.cfg = config_mgr

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Tile Launcher")

        self._drag_pos: QPoint | None = None
        self.toasts = ToastManager(self)

        self._build_ui()
        self._apply_lock_state()
        self._setup_tray()

        # Глобальный хоткей
        self._hotkey = GlobalHotkey(self)
        self._hotkey.triggered.connect(self._toggle_visibility)
        if self.cfg.config.hotkey:
            self._hotkey.register(self.cfg.config.hotkey)

        QTimer.singleShot(50, self._fit_and_position)

    # ── Фон ──

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 14, 14)

        bg = QLinearGradient(0, 0, self.width(), self.height())
        bg.setColorAt(0.0, QColor(13, 13, 26, 242))
        bg.setColorAt(0.5, QColor(18, 14, 32, 238))
        bg.setColorAt(1.0, QColor(13, 13, 26, 242))
        p.fillPath(path, QBrush(bg))
        p.end()

    # ── UI ──

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Верхняя зона
        top = QHBoxLayout()
        top.setContentsMargins(8, 3, 6, 0)
        top.addStretch()
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(22, 18)
        btn_close.setStyleSheet(
            "QPushButton{background:transparent;color:#4b5563;border:none;"
            "border-radius:4px;font-size:10px;}"
            "QPushButton:hover{background:rgba(239,68,68,50);color:white;}")
        btn_close.clicked.connect(self._toggle_visibility)
        top.addWidget(btn_close)
        root.addLayout(top)

        # Сетка
        self._grid = GridManager(self.cfg)
        self._grid.toast_requested.connect(self._on_toast)
        self._grid.grid_resized.connect(self._fit_and_position)

        gw = QWidget()
        gl = QHBoxLayout(gw)
        gl.setContentsMargins(10, 0, 10, 0)
        gl.addStretch()
        gl.addWidget(self._grid)
        gl.addStretch()
        root.addWidget(gw)

        # Кнопки
        bot = QWidget()
        bot.setFixedHeight(32)
        bl = QHBoxLayout(bot)
        bl.setContentsMargins(0, 0, 8, 5)
        bl.addStretch()

        self._controls = QWidget()
        cl = QHBoxLayout(self._controls)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(2)

        self._fab = (
            "QPushButton{background:rgba(255,255,255,8);"
            "color:rgba(255,255,255,90);border:none;"
            "border-radius:6px;font-size:12px;}"
            "QPushButton:hover{background:rgba(255,255,255,18);color:white;}")
        self._fab_on = (
            "QPushButton{background:rgba(59,130,246,25);"
            "color:rgba(59,130,246,180);border:none;"
            "border-radius:6px;font-size:12px;}"
            "QPushButton:hover{background:rgba(59,130,246,45);color:white;}")

        for icon, tip, slot in [
            ("＋", "Добавить", self._add_tile_dialog),
            ("📂", "Импорт", lambda: self._grid.import_from_folder()),
        ]:
            b = QPushButton(icon)
            b.setFixedSize(28, 28)
            b.setStyleSheet(self._fab)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            cl.addWidget(b)

        self._btn_lock = QPushButton("🔓")
        self._btn_lock.setFixedSize(28, 28)
        self._btn_lock.setStyleSheet(self._fab)
        self._btn_lock.clicked.connect(self._toggle_lock)
        cl.addWidget(self._btn_lock)

        b = QPushButton("⚙")
        b.setFixedSize(28, 28)
        b.setStyleSheet(self._fab)
        b.setToolTip("Настройки")
        b.clicked.connect(self._open_settings)
        cl.addWidget(b)

        self._ctrl_opacity = QGraphicsOpacityEffect(self._controls)
        self._ctrl_opacity.setOpacity(0.3)
        self._controls.setGraphicsEffect(self._ctrl_opacity)
        self._controls.installEventFilter(self)
        bl.addWidget(self._controls)
        root.addWidget(bot)

    # ── Трей ──

    def _setup_tray(self):
        pm = QPixmap(16, 16)
        pm.fill(QColor(59, 130, 246))
        self._tray = QSystemTrayIcon(QIcon(pm), self)
        menu = QTrayMenu()
        menu.addAction(t("show_hide")).triggered.connect(self._toggle_visibility)
        menu.addSeparator()
        menu.addAction(t("quit")).triggered.connect(self._quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(
            lambda r: self._toggle_visibility() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self._tray.show()

    # ── Добавление ──

    def _add_tile_dialog(self):
        dlg = AddTileDialog(os.path.dirname(self.cfg._path), parent=self)
        if dlg.exec() and dlg.result_tile:
            self._grid.add_tile_data(dlg.result_tile)

    # ── Замок ──

    def _toggle_lock(self):
        self.cfg.config.locked = not self.cfg.config.locked
        self.cfg.save()
        self._apply_lock_state()

    def _apply_lock_state(self):
        on = self.cfg.config.locked
        self._grid.set_locked(on)
        self._btn_lock.setText("🔒" if on else "🔓")
        self._btn_lock.setStyleSheet(self._fab_on if on else self._fab)

    # ── Fit + Position ──

    def _fit_and_position(self):
        w = self._grid.width() + _PAD_H
        h = self._grid.height() + _PAD_V
        scr = self.screen()
        if scr:
            a = scr.availableGeometry()
            w = min(w, a.width())
            h = min(h, a.height())
        self.resize(max(w, 120), max(h, 60))
        self._apply_position()

    def _apply_position(self):
        scr = self.screen()
        if not scr:
            return
        a = scr.availableGeometry()
        w, h, m = self.width(), self.height(), 6
        P = {
            "center":       QPoint(a.x()+(a.width()-w)//2, a.y()+(a.height()-h)//2),
            "bottom":       QPoint(a.x()+(a.width()-w)//2, a.bottom()-h-m),
            "top":          QPoint(a.x()+(a.width()-w)//2, a.y()+m),
            "left":         QPoint(a.x()+m, a.y()+(a.height()-h)//2),
            "right":        QPoint(a.right()-w-m, a.y()+(a.height()-h)//2),
            "bottom-left":  QPoint(a.x()+m, a.bottom()-h-m),
            "bottom-right": QPoint(a.right()-w-m, a.bottom()-h-m),
            "top-left":     QPoint(a.x()+m, a.y()+m),
            "top-right":    QPoint(a.right()-w-m, a.y()+m),
        }
        self.move(P.get(self.cfg.config.position, P["center"]))

    # ── Видимость ──

    def _toggle_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self._fade_out()
        else:
            self._fade_in()

    def _fade_in(self):
        self.setWindowOpacity(0.0)
        self._fit_and_position()
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._fade_step(0.0, 1.0, 8)

    def _fade_out(self):
        self._fade_step(1.0, 0.0, 6, on_done=self.hide)

    def _fade_step(self, start: float, end: float, steps: int, on_done=None):
        """Плавное изменение прозрачности окна за N шагов."""
        self._fade_i = 0
        self._fade_steps = steps
        self._fade_start = start
        self._fade_end = end
        self._fade_done = on_done
        self.setWindowOpacity(start)

        if hasattr(self, "_fade_timer") and self._fade_timer:
            self._fade_timer.stop()
        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(16)  # ~60fps
        self._fade_timer.timeout.connect(self._fade_tick)
        self._fade_timer.start()

    def _fade_tick(self):
        self._fade_i += 1
        progress = min(self._fade_i / self._fade_steps, 1.0)
        # Ease out cubic
        t_val = 1.0 - (1.0 - progress) ** 3
        opacity = self._fade_start + (self._fade_end - self._fade_start) * t_val
        self.setWindowOpacity(opacity)
        if self._fade_i >= self._fade_steps:
            self._fade_timer.stop()
            self.setWindowOpacity(self._fade_end)
            if self._fade_done:
                self._fade_done()

    # ── Events ──

    def eventFilter(self, obj, event):
        if obj is self._controls:
            if event.type() == QEvent.Type.Enter:
                self._anim_op(1.0)
            elif event.type() == QEvent.Type.Leave:
                self._anim_op(0.3)
        return super().eventFilter(obj, event)

    def _anim_op(self, t):
        a = QPropertyAnimation(self._ctrl_opacity, b"opacity", self)
        a.setDuration(180); a.setEndValue(t)
        a.setEasingCurve(QEasingCurve.Type.OutCubic)
        a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            p = e.globalPosition().toPoint() - self._drag_pos
            s = self.screen()
            if s:
                a = s.availableGeometry()
                p.setX(max(a.left(), min(p.x(), a.right()-self.width())))
                p.setY(max(a.top(), min(p.y(), a.bottom()-self.height())))
            self.move(p)

    def mouseReleaseEvent(self, _e):
        self._drag_pos = None

    def _open_settings(self):
        dlg = SettingsWindow(self.cfg, parent=self)
        dlg.settings_applied.connect(self._on_settings_ok)
        dlg.config_reset.connect(self._on_reset)
        dlg.exec()

    def _on_settings_ok(self):
        self._grid.apply_settings()
        self._apply_lock_state()
        self._hotkey.register(self.cfg.config.hotkey)
        self._fit_and_position()
        self.toasts.show(t("settings_applied"), "success")

    def _on_reset(self):
        self._grid.apply_settings()
        self._apply_lock_state()
        self._fit_and_position()
        self.toasts.show(t("reset_done"), "warning")

    def _on_toast(self, msg, typ):
        self.toasts.show(msg, typ)

    def _quit(self):
        self._hotkey.unregister()
        self._tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        self._hotkey.unregister()
        self._tray.hide()
        event.accept()

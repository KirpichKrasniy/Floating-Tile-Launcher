"""
widgets/tile_widget.py — Виджет одной плитки.
"""

from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtWidgets import (
    QWidget, QMenu, QGraphicsDropShadowEffect, QFileDialog, QInputDialog,
)
from PySide6.QtCore import (
    Qt, Signal, QRectF, QPoint,
    QPropertyAnimation, QEasingCurve, Property,
)
from PySide6.QtGui import (
    QColor, QPainter, QPainterPath, QPixmap, QPen, QBrush,
    QLinearGradient, QRadialGradient, QMouseEvent, QContextMenuEvent,
    QImage, QIcon,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray

from core.config_manager import TileData, BUILTIN_ICONS
from core.i18n import t

TILE_SIZES: list[tuple[str, list[int]]] = [
    ("1×1", [1, 1]),
    ("2×1", [2, 1]),
    ("1×2", [1, 2]),
    ("2×2", [2, 2]),
    ("2×3", [2, 3]),
    ("3×2", [3, 2]),
    ("4×2", [4, 2]),
]

TILE_COLORS: list[str] = [
    "#4285f4", "#3b82f6", "#6366f1", "#8b5cf6",
    "#a855f7", "#d946ef", "#ec4899", "#f43f5e",
    "#ef4444", "#f97316", "#f59e0b", "#eab308",
    "#84cc16", "#22c55e", "#10b981", "#14b8a6",
    "#06b6d4", "#0ea5e9", "#64748b", "#78716c",
]

_RENDER_SCALE = 2


class TileWidget(QWidget):

    delete_requested    = Signal(str)
    resize_requested    = Signal(str, list)
    image_changed       = Signal(str, str)
    color_changed       = Signal(str, str)
    app_path_changed    = Signal(str, str)
    label_changed       = Signal(str, str)       # tile_id, new_label
    fetch_grid_requested = Signal(str)
    drag_started        = Signal(str, QPoint)
    launch_failed       = Signal(str)

    def __init__(self, tile: TileData, cell_size: int, gap: int,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.tile = tile
        self.cell_size = cell_size
        self.gap = gap

        self._glow: float = 0.0
        self._hovered = False
        self._pressed = False
        self._dragging = False
        self._drag_start_pos = QPoint()
        self._drag_opacity: float = 1.0

        self._cover_pixmap: QPixmap | None = None
        self._has_cover = False

        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

        self._glow_anim = QPropertyAnimation(self, b"hover_glow")
        self._glow_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.update_geometry()
        self._load_icon()

    def _get_hover_glow(self) -> float:
        return self._glow

    def _set_hover_glow(self, val: float):
        self._glow = val
        self.update()

    hover_glow = Property(float, _get_hover_glow, _set_hover_glow)

    def pixel_width(self) -> int:
        return self.tile.grid_size[0] * self.cell_size + (self.tile.grid_size[0] - 1) * self.gap

    def pixel_height(self) -> int:
        return self.tile.grid_size[1] * self.cell_size + (self.tile.grid_size[1] - 1) * self.gap

    def grid_to_pixel(self) -> QPoint:
        return QPoint(
            self.tile.grid_position[0] * (self.cell_size + self.gap),
            self.tile.grid_position[1] * (self.cell_size + self.gap),
        )

    def update_geometry(self):
        pos = self.grid_to_pixel()
        self.setGeometry(pos.x(), pos.y(), self.pixel_width(), self.pixel_height())

    def _load_icon(self):
        path = self.tile.image_path
        pw, ph = self.pixel_width(), self.pixel_height()
        rw, rh = pw * _RENDER_SCALE, ph * _RENDER_SCALE

        if not path:
            self._cover_pixmap = None
            self._has_cover = False
            return

        if path.startswith("builtin:"):
            try:
                idx = int(path.split(":")[1])
                svg_bytes = QByteArray(BUILTIN_ICONS[idx].encode("utf-8"))
                renderer = QSvgRenderer(svg_bytes)
                if renderer.isValid():
                    svg_w = renderer.defaultSize().width() or 64
                    svg_h = renderer.defaultSize().height() or 64
                    scale = max(rw / svg_w, rh / svg_h)
                    draw_w, draw_h = int(svg_w * scale), int(svg_h * scale)
                    img = QImage(rw, rh, QImage.Format.Format_ARGB32_Premultiplied)
                    img.fill(Qt.GlobalColor.transparent)
                    p = QPainter(img)
                    p.setRenderHint(QPainter.RenderHint.Antialiasing)
                    renderer.render(p, QRectF((rw - draw_w) // 2, (rh - draw_h) // 2, draw_w, draw_h))
                    p.end()
                    pm = QPixmap.fromImage(img)
                    pm.setDevicePixelRatio(_RENDER_SCALE)
                    self._cover_pixmap = pm
                    self._has_cover = True
                    return
            except (IndexError, ValueError):
                pass
            self._cover_pixmap = None
            self._has_cover = False
            return

        if os.path.isfile(path):
            pm = QPixmap(path)
            if not pm.isNull():
                scaled = pm.scaled(rw, rh, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                   Qt.TransformationMode.SmoothTransformation)
                cx, cy = (scaled.width() - rw) // 2, (scaled.height() - rh) // 2
                cropped = scaled.copy(cx, cy, rw, rh)
                cropped.setDevicePixelRatio(_RENDER_SCALE)
                self._cover_pixmap = cropped
                self._has_cover = True
                return

        self._cover_pixmap = None
        self._has_cover = False

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        rect = QRectF(0, 0, w, h)

        if self._drag_opacity < 1.0:
            painter.setOpacity(self._drag_opacity)

        clip = QPainterPath()
        clip.addRoundedRect(rect, 16, 16)
        painter.setClipPath(clip)

        color = QColor(self.tile.color) if self.tile.color else QColor(255, 255, 255, 20)

        if self._has_cover and self._cover_pixmap:
            painter.drawPixmap(0, 0, self._cover_pixmap)
            painter.fillPath(clip, QBrush(QColor(0, 0, 0, 20)))
        else:
            bg = QLinearGradient(0, 0, w, h)
            bg.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 35))
            bg.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 18))
            painter.fillPath(clip, QBrush(bg))

        shine = QLinearGradient(0, 0, w, h)
        shine.setColorAt(0, QColor(255, 255, 255, 12))
        shine.setColorAt(0.4, QColor(255, 255, 255, 0))
        painter.fillPath(clip, QBrush(shine))

        if self._glow > 0.001:
            painter.fillPath(clip, QBrush(QColor(255, 255, 255, int(self._glow * 40))))
            painter.setClipping(False)
            painter.setPen(QPen(QColor(255, 255, 255, int(self._glow * 100)), 1.5))
            painter.drawRoundedRect(rect.adjusted(0.75, 0.75, -0.75, -0.75), 16, 16)
        else:
            painter.setClipping(False)
            painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
            painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 16, 16)

        painter.end()

    # ── Mouse ──

    def enterEvent(self, _event):
        self._hovered = True
        self._animate_glow(1.0, 200)
        fx = self.graphicsEffect()
        if isinstance(fx, QGraphicsDropShadowEffect):
            fx.setBlurRadius(36)
            fx.setOffset(0, 8)
            fx.setColor(QColor(0, 0, 0, 110))

    def leaveEvent(self, _event):
        self._hovered = False
        self._pressed = False
        self._animate_glow(0.0, 250)
        fx = self.graphicsEffect()
        if isinstance(fx, QGraphicsDropShadowEffect):
            fx.setBlurRadius(24)
            fx.setOffset(0, 6)
            fx.setColor(QColor(0, 0, 0, 80))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._animate_glow(0.4, 80)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self._drag_start_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            was_dragging = self._dragging
            self._pressed = False
            self._animate_glow(1.0 if self._hovered else 0.0, 200)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            if not was_dragging:
                self._launch_app()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._pressed and not self._dragging:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            if delta.manhattanLength() > 8:
                self._dragging = True
                self.drag_started.emit(self.tile.id, self._drag_start_pos)

    def _launch_app(self):
        target = self.tile.app_path.strip()
        if not target:
            return
        try:
            if target.startswith("http://") or target.startswith("https://"):
                import webbrowser
                webbrowser.open(target)
                return
            if sys.platform == "win32":
                os.startfile(target)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        except Exception as exc:
            self.launch_failed.emit(f"{t('launch_failed')}: {exc}")

    # ── Context menu (fully translated) ──

    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_stylesheet())

        if self.tile.app_path:
            app_label = os.path.basename(self.tile.app_path)
            menu.addAction("🚀  " + t("ctx_launch").format(app_label)).triggered.connect(self._launch_app)
            menu.addSeparator()

        menu.addAction("📎  " + t("ctx_bind_app")).triggered.connect(self._pick_app)
        menu.addAction("🌐  " + t("ctx_bind_url")).triggered.connect(self._pick_url)

        if self.tile.app_path:
            menu.addAction("✕  " + t("ctx_unbind")).triggered.connect(
                lambda: self.app_path_changed.emit(self.tile.id, ""))

        menu.addSeparator()

        # Переименовать
        menu.addAction("✏  " + t("ctx_rename")).triggered.connect(self._rename)

        menu.addAction("🖼  " + t("ctx_change_icon")).triggered.connect(self._pick_image)
        menu.addAction("🔍  " + t("ctx_find_cover")).triggered.connect(
            lambda: self.fetch_grid_requested.emit(self.tile.id))

        size_menu = menu.addMenu("↔  " + t("ctx_resize"))
        for label, size in TILE_SIZES:
            act = size_menu.addAction(label)
            if self.tile.grid_size == size:
                act.setText(f"✓ {label}")
                act.setEnabled(False)
            else:
                act.triggered.connect(
                    lambda _c=False, s=list(size): self.resize_requested.emit(self.tile.id, s))

        color_menu = menu.addMenu("🎨  " + t("ctx_change_color"))
        for c in TILE_COLORS:
            act = color_menu.addAction(f"● {c}")
            act.setIcon(self._make_color_icon(c))
            act.triggered.connect(
                lambda _c=False, clr=c: self.color_changed.emit(self.tile.id, clr))

        menu.addSeparator()
        menu.addAction("🗑  " + t("ctx_delete")).triggered.connect(
            lambda: self.delete_requested.emit(self.tile.id))

        menu.exec(event.globalPos())

    def _rename(self):
        text, ok = QInputDialog.getText(
            self, t("ctx_rename"),
            t("add_tile_name"),
            text=self.tile.label,
        )
        if ok:
            self.label_changed.emit(self.tile.id, text.strip())

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, t("dlg_choose_image"), "",
            "Images (*.png *.jpg *.jpeg *.svg *.ico *.bmp);;All (*)")
        if path:
            self.image_changed.emit(self.tile.id, path)

    def _pick_app(self):
        if sys.platform == "win32":
            filt = "Apps (*.exe *.lnk);;All (*)"
        else:
            filt = "All (*)"
        path, _ = QFileDialog.getOpenFileName(self, t("dlg_choose_app"), "", filt)
        if path:
            self.app_path_changed.emit(self.tile.id, path)

    def _pick_url(self):
        url, ok = QInputDialog.getText(
            self, t("dlg_bind_url_title"), t("dlg_bind_url_label"),
            text=self.tile.app_path if self.tile.app_path.startswith("http") else "https://")
        if ok and url.strip():
            self.app_path_changed.emit(self.tile.id, url.strip())

    def _animate_glow(self, target: float, duration: int):
        self._glow_anim.stop()
        self._glow_anim.setDuration(duration)
        self._glow_anim.setStartValue(self._glow)
        self._glow_anim.setEndValue(target)
        self._glow_anim.start()

    def set_dragging(self, val: bool):
        self._dragging = val
        self._drag_opacity = 0.4 if val else 1.0
        if not val:
            self._pressed = False
            self._hovered = False
            self._animate_glow(0.0, 150)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.update()

    def reload_icon(self):
        self._load_icon()
        self.update()

    @staticmethod
    def _make_color_icon(hex_color: str) -> QIcon:
        pm = QPixmap(16, 16)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(hex_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, 12, 12)
        p.end()
        return QIcon(pm)

    @staticmethod
    def _menu_stylesheet() -> str:
        return """
            QMenu {
                background: rgba(18, 18, 35, 248);
                border: 1px solid rgba(255,255,255,20);
                border-radius: 10px;
                padding: 4px;
                color: #e0e0e0;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 16px 6px 10px;
                border-radius: 6px;
            }
            QMenu::item:selected { background: rgba(255,255,255,20); }
            QMenu::item:disabled { color: #6b7280; }
            QMenu::separator { height: 1px; background: rgba(255,255,255,10); margin: 3px 6px; }
        """

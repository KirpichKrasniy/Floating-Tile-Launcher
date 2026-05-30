"""
windows/grid_picker.py — Диалог выбора обложки из SteamGridDB.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QFrame,
)
from PySide6.QtCore import Qt, QRectF, QByteArray
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap, QImage

from core.steamgriddb import GridImage
from core.i18n import t
from urllib import request as urllib_request

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0"


class _ThumbWidget(QWidget):

    def __init__(self, grid_img: GridImage, parent=None):
        super().__init__(parent)
        self.grid_img = grid_img
        self._pixmap: QPixmap | None = None
        self._selected = False
        self.setFixedSize(120, 170)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._load_thumb()

    def _load_thumb(self):
        url = self.grid_img.thumb or self.grid_img.url
        if not url:
            return
        try:
            req = urllib_request.Request(url, headers={"User-Agent": _UA})
            with urllib_request.urlopen(req, timeout=8) as resp:
                data = resp.read()
            img = QImage()
            img.loadFromData(QByteArray(data))
            if not img.isNull():
                self._pixmap = QPixmap.fromImage(img).scaled(
                    112, 162, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
        except Exception:
            pass
        self.update()

    def set_selected(self, val: bool):
        self._selected = val
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = QRectF(0, 0, self.width(), self.height())
        clip = QPainterPath()
        clip.addRoundedRect(rect, 8, 8)
        p.setClipPath(clip)

        if self._selected:
            p.fillPath(clip, QColor(59, 130, 246, 35))
        else:
            p.fillPath(clip, QColor(255, 255, 255, 6))

        if self._pixmap and not self._pixmap.isNull():
            x = (self.width() - self._pixmap.width()) // 2
            y = (self.height() - self._pixmap.height()) // 2
            p.drawPixmap(x, y, self._pixmap)
        else:
            p.setPen(QColor(255, 255, 255, 25))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "…")

        p.setClipping(False)
        border = QColor(59, 130, 246) if self._selected else QColor(255, 255, 255, 15)
        p.setPen(border)
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        p.end()


class GridPickerDialog(QDialog):

    def __init__(self, images: list[GridImage], parent=None):
        super().__init__(parent)
        self.images = images
        self.selected_image: GridImage | None = None
        self._thumbs: list[_ThumbWidget] = []

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(540, 420)
        self._build_ui()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 14, 14)
        p.fillPath(path, QColor(18, 18, 35, 248))
        p.end()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(0)

        hdr = QHBoxLayout()
        title_lbl = QLabel(f"{t('picker_title')}  ({len(self.images)})")
        title_lbl.setStyleSheet("color: white; font-size: 14px; font-weight: 600;")
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        bx = QPushButton("✕")
        bx.setFixedSize(26, 26)
        bx.setStyleSheet(
            "QPushButton{background:transparent;color:#6b7280;border:none;"
            "border-radius:6px;font-size:12px;}"
            "QPushButton:hover{background:rgba(255,255,255,15);color:white;}")
        bx.clicked.connect(self.reject)
        hdr.addWidget(bx)
        root.addLayout(hdr)
        root.addSpacing(8)

        # Вертикальный скролл, без горизонтального
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{width:4px;background:transparent;}"
            "QScrollBar::handle:vertical{background:rgba(255,255,255,20);"
            "border-radius:2px;}")

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        flow = QVBoxLayout(container)
        flow.setContentsMargins(0, 0, 0, 0)
        flow.setSpacing(6)

        # Раскладываем по 4 в ряд
        row: QHBoxLayout | None = None
        cols = 4
        for i, img in enumerate(self.images[:20]):
            if i % cols == 0:
                row = QHBoxLayout()
                row.setSpacing(6)
                flow.addLayout(row)
            tw = _ThumbWidget(img)
            tw.mousePressEvent = lambda _e, _tw=tw, _img=img: self._on_click(_tw, _img)
            self._thumbs.append(tw)
            row.addWidget(tw)
        # Заполняем остаток последнего ряда
        if row and len(self._thumbs) % cols:
            for _ in range(cols - len(self._thumbs) % cols):
                spacer = QWidget()
                spacer.setFixedSize(120, 170)
                row.addWidget(spacer)

        scroll.setWidget(container)
        root.addWidget(scroll)
        root.addSpacing(8)

        btns = QHBoxLayout()
        btns.addStretch()
        bc = QPushButton(t("picker_cancel"))
        bc.setStyleSheet(
            "QPushButton{background:transparent;color:#9ca3af;border:none;"
            "padding:6px 14px;border-radius:8px;font-size:12px;}"
            "QPushButton:hover{background:rgba(255,255,255,12);color:white;}")
        bc.clicked.connect(self.reject)
        btns.addWidget(bc)

        self._btn_ok = QPushButton(t("picker_ok"))
        self._btn_ok.setEnabled(False)
        self._btn_ok.setStyleSheet(
            "QPushButton{background:#3b82f6;color:white;border:none;"
            "padding:6px 16px;border-radius:8px;font-weight:600;font-size:12px;}"
            "QPushButton:hover{background:#60a5fa;}"
            "QPushButton:disabled{background:#1e293b;color:#475569;}")
        self._btn_ok.clicked.connect(self.accept)
        btns.addWidget(self._btn_ok)
        root.addLayout(btns)

    def _on_click(self, thumb: _ThumbWidget, img: GridImage):
        for tw in self._thumbs:
            tw.set_selected(False)
        thumb.set_selected(True)
        self.selected_image = img
        self._btn_ok.setEnabled(True)

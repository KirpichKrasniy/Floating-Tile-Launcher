"""
windows/add_tile_dialog.py — Диалог добавления новой плитки.

Позволяет выбрать приложение/ярлык, размер плитки и цвет.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFileDialog, QFrame,
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath

from core.config_manager import TileData, ACCENT_COLORS
from core.icon_extractor import extract_icon
from widgets.tile_widget import TILE_SIZES, TILE_COLORS


class AddTileDialog(QDialog):
    """
    Результат: self.result_tile — TileData или None.
    """

    def __init__(self, config_dir: str, parent=None):
        super().__init__(parent)
        self.config_dir = config_dir
        self.result_tile: TileData | None = None
        self._app_path = ""
        self._icon_path = ""
        self._color_idx = 0

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 380)
        self._build_ui()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 16, 16)
        p.fillPath(path, QColor(22, 22, 40, 250))
        p.setPen(QColor(255, 255, 255, 15))
        p.drawPath(path)
        p.end()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(0)

        # Заголовок
        hdr = QHBoxLayout()
        t = QLabel("＋  Новая плитка")
        t.setStyleSheet("color: white; font-size: 16px; font-weight: 600;")
        hdr.addWidget(t)
        hdr.addStretch()
        bx = QPushButton("✕")
        bx.setFixedSize(28, 28)
        bx.setStyleSheet(
            "QPushButton{background:transparent;color:#6b7280;border:none;"
            "border-radius:6px;font-size:13px;}"
            "QPushButton:hover{background:rgba(255,255,255,15);color:white;}")
        bx.clicked.connect(self.reject)
        hdr.addWidget(bx)
        root.addLayout(hdr)
        root.addSpacing(16)

        input_css = (
            "QLineEdit{background:rgba(255,255,255,8);color:white;"
            "border:1px solid rgba(255,255,255,15);border-radius:8px;"
            "padding:8px 10px;font-size:13px;}"
            "QLineEdit:focus{border:1px solid rgba(59,130,246,100);}")

        # Приложение
        lbl_app = QLabel("Приложение:")
        lbl_app.setStyleSheet("color: #9ca3af; font-size: 13px;")
        root.addWidget(lbl_app)
        root.addSpacing(4)

        app_row = QHBoxLayout()
        self._app_input = QLineEdit()
        self._app_input.setPlaceholderText("Путь к .exe / .lnk или URL")
        self._app_input.setStyleSheet(input_css)
        app_row.addWidget(self._app_input)

        btn_browse = QPushButton("📁")
        btn_browse.setFixedSize(36, 36)
        btn_browse.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,10);color:white;border:none;"
            "border-radius:8px;font-size:14px;}"
            "QPushButton:hover{background:rgba(255,255,255,20);}")
        btn_browse.clicked.connect(self._browse_app)
        app_row.addWidget(btn_browse)
        root.addLayout(app_row)
        root.addSpacing(12)

        # Название
        lbl_name = QLabel("Название:")
        lbl_name.setStyleSheet("color: #9ca3af; font-size: 13px;")
        root.addWidget(lbl_name)
        root.addSpacing(4)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Автоматически из имени файла")
        self._name_input.setStyleSheet(input_css)
        root.addWidget(self._name_input)
        root.addSpacing(12)

        # Размер + Цвет
        row2 = QHBoxLayout()

        # Размер
        size_col = QVBoxLayout()
        lbl_size = QLabel("Размер:")
        lbl_size.setStyleSheet("color: #9ca3af; font-size: 13px;")
        size_col.addWidget(lbl_size)
        size_col.addSpacing(4)
        self._size_combo = QComboBox()
        for label, _ in TILE_SIZES:
            self._size_combo.addItem(label)
        self._size_combo.setStyleSheet(
            "QComboBox{background:rgba(255,255,255,8);color:white;"
            "border:1px solid rgba(255,255,255,15);border-radius:8px;"
            "padding:6px 10px;font-size:13px;}"
            "QComboBox::drop-down{border:none;}"
            "QComboBox QAbstractItemView{background:rgb(30,30,50);color:white;"
            "border:1px solid rgba(255,255,255,15);selection-background-color:rgba(59,130,246,40);}")
        size_col.addWidget(self._size_combo)
        row2.addLayout(size_col)

        row2.addSpacing(12)

        # Цвет
        color_col = QVBoxLayout()
        lbl_clr = QLabel("Цвет:")
        lbl_clr.setStyleSheet("color: #9ca3af; font-size: 13px;")
        color_col.addWidget(lbl_clr)
        color_col.addSpacing(4)
        color_row = QHBoxLayout()
        color_row.setSpacing(4)
        self._color_buttons: list[QPushButton] = []
        for i, c in enumerate(TILE_COLORS[:10]):
            cb = QPushButton()
            cb.setFixedSize(22, 22)
            cb.setStyleSheet(
                f"QPushButton{{background:{c};border:none;border-radius:6px;}}"
                f"QPushButton:hover{{border:2px solid white;}}")
            cb.clicked.connect(lambda _=False, idx=i: self._select_color(idx))
            color_row.addWidget(cb)
            self._color_buttons.append(cb)
        color_col.addLayout(color_row)
        row2.addLayout(color_col)

        root.addLayout(row2)
        root.addSpacing(16)

        # Линия
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: rgba(255,255,255,10);")
        root.addWidget(line)
        root.addSpacing(12)

        # Кнопки
        btns = QHBoxLayout()
        btns.addStretch()
        bc = QPushButton("Отмена")
        bc.setStyleSheet(
            "QPushButton{background:transparent;color:#9ca3af;border:none;"
            "padding:8px 16px;border-radius:10px;font-size:13px;}"
            "QPushButton:hover{background:rgba(255,255,255,15);color:white;}")
        bc.clicked.connect(self.reject)
        btns.addWidget(bc)

        ba = QPushButton("Добавить")
        ba.setStyleSheet(
            "QPushButton{background:#3b82f6;color:white;border:none;"
            "padding:8px 20px;border-radius:10px;font-weight:600;font-size:13px;}"
            "QPushButton:hover{background:#60a5fa;}")
        ba.clicked.connect(self._on_add)
        btns.addWidget(ba)
        root.addLayout(btns)

    def _browse_app(self):
        if sys.platform == "win32":
            filt = "Приложения (*.exe *.lnk);;Все файлы (*)"
        else:
            filt = "Все файлы (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать приложение", "", filt)
        if path:
            self._app_input.setText(path)
            if not self._name_input.text():
                self._name_input.setText(os.path.splitext(os.path.basename(path))[0])

    def _select_color(self, idx: int):
        self._color_idx = idx
        for i, cb in enumerate(self._color_buttons):
            c = TILE_COLORS[i]
            if i == idx:
                cb.setStyleSheet(
                    f"QPushButton{{background:{c};border:2px solid white;border-radius:6px;}}")
            else:
                cb.setStyleSheet(
                    f"QPushButton{{background:{c};border:none;border-radius:6px;}}"
                    f"QPushButton:hover{{border:2px solid white;}}")

    def _on_add(self):
        app_path = self._app_input.text().strip()
        label = self._name_input.text().strip()
        if not label and app_path:
            label = os.path.splitext(os.path.basename(app_path))[0]

        size_idx = self._size_combo.currentIndex()
        _, size = TILE_SIZES[size_idx]

        color = TILE_COLORS[self._color_idx]

        icon_path = ""
        if app_path and os.path.isfile(app_path):
            icon_path = extract_icon(app_path, self.config_dir)

        self.result_tile = TileData(
            label=label,
            image_path=icon_path,
            app_path=app_path,
            grid_size=list(size),
            color=color,
        )
        self.accept()

"""
windows/settings_window.py — Окно настроек.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QFrame, QComboBox,
)
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath

from core.config_manager import ConfigManager
from core.i18n import t, available_languages
from widgets.hotkey_edit import HotkeyEdit


class SettingsWindow(QDialog):

    settings_applied = Signal()
    config_reset     = Signal()

    def __init__(self, config_mgr: ConfigManager, parent=None):
        super().__init__(parent)
        self.cfg = config_mgr
        self.setFixedSize(400, 700)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 14, 14)
        p.fillPath(path, QColor(18, 18, 35, 250))
        p.end()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 14)
        root.setSpacing(0)

        hdr = QHBoxLayout()
        title = QLabel(f"⚙  {t('settings_title')}")
        title.setStyleSheet("color: white; font-size: 15px; font-weight: 600;")
        hdr.addWidget(title)
        hdr.addStretch()
        bx = QPushButton("✕")
        bx.setFixedSize(28, 28)
        bx.setStyleSheet(
            "QPushButton{background:transparent;color:#6b7280;border:none;"
            "border-radius:6px;font-size:12px;}"
            "QPushButton:hover{background:rgba(255,255,255,15);color:white;}")
        bx.clicked.connect(self.reject)
        hdr.addWidget(bx)
        root.addLayout(hdr)
        root.addSpacing(14)

        self._sl_cols = self._slider(root, t("settings_columns"), 3, 12,
                                     self.cfg.config.grid_columns)
        root.addSpacing(10)
        self._sl_cell = self._slider(root, t("settings_cell"), 60, 160,
                                     self.cfg.config.cell_size, step=10)
        root.addSpacing(10)
        self._sl_gap = self._slider(root, t("settings_gap"), 2, 20,
                                    self.cfg.config.gap)
        root.addSpacing(12)

        # API key
        self._add_label(root, t("settings_api_key"))
        self._api_key = self._line_edit(root, self.cfg.config.steamgriddb_api_key,
                                        "steamgriddb.com/profile/preferences/api")
        self._add_hint(root, t("settings_api_hint"))
        root.addSpacing(10)

        # Hotkey
        self._add_label(root, t("settings_hotkey"))
        self._hotkey = HotkeyEdit(self.cfg.config.hotkey)
        root.addWidget(self._hotkey)
        self._add_hint(root, t("settings_hotkey_hint"))
        root.addSpacing(10)

        # Position
        self._add_label(root, t("settings_position"))
        self._pos = QComboBox()
        _POS = [
            (t("pos_center"), "center"), (t("pos_bottom"), "bottom"),
            (t("pos_top"), "top"), (t("pos_left"), "left"),
            (t("pos_right"), "right"), (t("pos_bottom_left"), "bottom-left"),
            (t("pos_bottom_right"), "bottom-right"),
            (t("pos_top_left"), "top-left"), (t("pos_top_right"), "top-right"),
        ]
        cur = self.cfg.config.position
        for i, (lbl, val) in enumerate(_POS):
            self._pos.addItem(lbl, val)
            if val == cur:
                self._pos.setCurrentIndex(i)
        self._pos.setStyleSheet(self._combo_css())
        root.addWidget(self._pos)
        root.addSpacing(10)

        # Language
        self._add_label(root, t("settings_language"))
        self._lang = QComboBox()
        cur_lang = self.cfg.config.language
        for i, (code, label) in enumerate(available_languages()):
            self._lang.addItem(label, code)
            if code == cur_lang:
                self._lang.setCurrentIndex(i)
        self._lang.setStyleSheet(self._combo_css())
        root.addWidget(self._lang)
        root.addSpacing(14)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: rgba(255,255,255,10);")
        root.addWidget(line)
        root.addSpacing(10)

        btns = QHBoxLayout()
        br = QPushButton(t("settings_reset"))
        br.setStyleSheet(
            "QPushButton{background:transparent;color:#f87171;border:none;"
            "padding:6px 14px;border-radius:8px;font-size:12px;}"
            "QPushButton:hover{background:rgba(239,68,68,20);}")
        br.clicked.connect(self._on_reset)
        btns.addWidget(br)
        btns.addStretch()

        bc = QPushButton(t("settings_cancel"))
        bc.setStyleSheet(
            "QPushButton{background:transparent;color:#9ca3af;border:none;"
            "padding:6px 14px;border-radius:8px;font-size:12px;}"
            "QPushButton:hover{background:rgba(255,255,255,12);color:white;}")
        bc.clicked.connect(self.reject)
        btns.addWidget(bc)

        ba = QPushButton(t("settings_apply"))
        ba.setStyleSheet(
            "QPushButton{background:#3b82f6;color:white;border:none;"
            "padding:6px 18px;border-radius:8px;font-weight:600;font-size:12px;}"
            "QPushButton:hover{background:#60a5fa;}")
        ba.clicked.connect(self._on_apply)
        btns.addWidget(ba)
        root.addLayout(btns)

    # ── helpers ──

    def _add_label(self, layout, text):
        l = QLabel(text)
        l.setStyleSheet("color: #9ca3af; font-size: 12px;")
        layout.addWidget(l)
        layout.addSpacing(3)

    def _add_hint(self, layout, text):
        l = QLabel(text)
        l.setStyleSheet("color: #4b5563; font-size: 10px;")
        layout.addWidget(l)

    def _line_edit(self, layout, text, placeholder):
        from PySide6.QtWidgets import QLineEdit
        le = QLineEdit()
        le.setText(text)
        le.setPlaceholderText(placeholder)
        le.setStyleSheet(
            "QLineEdit{background:rgba(255,255,255,6);color:white;"
            "border:1px solid rgba(255,255,255,12);border-radius:7px;"
            "padding:7px 9px;font-size:11px;font-family:monospace;}"
            "QLineEdit:focus{border:1px solid rgba(59,130,246,100);}"
            "QLineEdit::placeholder{color:rgba(255,255,255,20);}")
        layout.addWidget(le)
        return le

    def _slider(self, layout, label, mn, mx, val, step=1):
        lbl = QLabel(f"{label}: {val}")
        lbl.setStyleSheet("color: #9ca3af; font-size: 12px;")
        layout.addWidget(lbl)
        layout.addSpacing(2)
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(mn, mx); sl.setSingleStep(step); sl.setValue(val)
        sl.setStyleSheet(
            "QSlider::groove:horizontal{height:3px;background:rgba(255,255,255,20);border-radius:1px;}"
            "QSlider::handle:horizontal{width:14px;height:14px;margin:-5px 0;"
            "background:#3b82f6;border-radius:7px;}")
        sl.valueChanged.connect(lambda v, _l=lbl, _t=label: _l.setText(f"{_t}: {v}"))
        layout.addWidget(sl)
        return sl

    @staticmethod
    def _combo_css():
        return (
            "QComboBox{background:rgba(255,255,255,6);color:white;"
            "border:1px solid rgba(255,255,255,12);border-radius:7px;"
            "padding:6px 9px;font-size:12px;}"
            "QComboBox::drop-down{border:none;}"
            "QComboBox QAbstractItemView{background:rgb(25,25,45);color:white;"
            "border:1px solid rgba(255,255,255,12);"
            "selection-background-color:rgba(59,130,246,35);}")

    def _on_apply(self):
        self.cfg.config.grid_columns = self._sl_cols.value()
        self.cfg.config.cell_size = self._sl_cell.value()
        self.cfg.config.gap = self._sl_gap.value()
        self.cfg.config.steamgriddb_api_key = self._api_key.text().strip()
        self.cfg.config.hotkey = self._hotkey.combo
        self.cfg.config.position = self._pos.currentData() or "center"
        self.cfg.config.language = self._lang.currentData() or "ru"
        self.cfg.save()

        from core.i18n import set_language
        set_language(self.cfg.config.language)

        self.settings_applied.emit()
        self.accept()

    def _on_reset(self):
        self.cfg.reset()
        self.config_reset.emit()
        self.accept()

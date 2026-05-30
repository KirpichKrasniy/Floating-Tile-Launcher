"""
core/icon_extractor.py — Извлечение иконок из .exe / .lnk файлов.

Использует QFileIconProvider (кроссплатформенный) для получения
системной иконки приложения. На Windows также проверяет .ico файлы
рядом с приложением.

Иконка сохраняется как PNG-файл в папку icons/ рядом с config.json.
"""

from __future__ import annotations

import os
import hashlib

from PySide6.QtWidgets import QFileIconProvider
from PySide6.QtCore import QFileInfo, QSize, Qt
from PySide6.QtGui import QPixmap, QImage, QPainter


def _icons_dir(config_dir: str) -> str:
    """Папка для кэшированных иконок."""
    d = os.path.join(config_dir, "icons")
    os.makedirs(d, exist_ok=True)
    return d


def _hash_path(path: str) -> str:
    """Короткий хэш пути для имени файла иконки."""
    return hashlib.md5(path.encode("utf-8")).hexdigest()[:12]


def _find_ico_nearby(app_path: str) -> str | None:
    """
    Ищет .ico файл рядом с приложением:
    1. Файл с тем же именем но .ico расширением
    2. Любой .ico в той же папке
    3. Любой .ico в родительской папке
    """
    folder = os.path.dirname(app_path)
    base = os.path.splitext(os.path.basename(app_path))[0]

    # 1. Точное совпадение имени
    exact = os.path.join(folder, base + ".ico")
    if os.path.isfile(exact):
        return exact

    # 2. Любой .ico в папке приложения
    for f in _safe_listdir(folder):
        if f.lower().endswith(".ico"):
            return os.path.join(folder, f)

    # 3. Любой .ico в родительской папке
    parent = os.path.dirname(folder)
    if parent and parent != folder:
        for f in _safe_listdir(parent):
            if f.lower().endswith(".ico"):
                return os.path.join(parent, f)

    return None


def _find_png_nearby(app_path: str) -> str | None:
    """Ищет .png файл рядом с приложением (часто бывает у портативных программ)."""
    folder = os.path.dirname(app_path)
    base = os.path.splitext(os.path.basename(app_path))[0]

    exact = os.path.join(folder, base + ".png")
    if os.path.isfile(exact):
        return exact

    for f in _safe_listdir(folder):
        if f.lower().endswith(".png") and "icon" in f.lower():
            return os.path.join(folder, f)

    return None


def _safe_listdir(path: str) -> list[str]:
    try:
        return os.listdir(path)
    except OSError:
        return []


def extract_icon(app_path: str, config_dir: str, size: int = 256) -> str:
    """
    Извлекает иконку из приложения и сохраняет в icons/.

    Стратегия:
    1. Ищет .ico / .png файл рядом с приложением
    2. Использует QFileIconProvider для системной иконки
    3. Возвращает путь к сохранённому PNG

    Args:
        app_path:   путь к .exe / .lnk
        config_dir: папка с config.json (для хранения icons/)
        size:       размер иконки в пикселях

    Returns:
        Абсолютный путь к PNG-файлу иконки,
        или пустую строку если иконку не удалось извлечь.
    """
    icons = _icons_dir(config_dir)
    out_name = f"{_hash_path(app_path)}.png"
    out_path = os.path.join(icons, out_name)

    # Если уже извлекали — возвращаем кэш
    if os.path.isfile(out_path):
        return out_path

    pixmap: QPixmap | None = None

    # ── 1. Ищем .ico / .png рядом ──
    ico_path = _find_ico_nearby(app_path)
    if ico_path:
        pm = QPixmap(ico_path)
        if not pm.isNull():
            pixmap = pm

    if pixmap is None:
        png_path = _find_png_nearby(app_path)
        if png_path:
            pm = QPixmap(png_path)
            if not pm.isNull():
                pixmap = pm

    # ── 2. Системная иконка через QFileIconProvider ──
    if pixmap is None:
        provider = QFileIconProvider()
        info = QFileInfo(app_path)
        icon = provider.icon(info)
        if not icon.isNull():
            # Берём максимально доступный размер
            for try_size in [256, 128, 64, 48, 32]:
                pm = icon.pixmap(QSize(try_size, try_size))
                if not pm.isNull() and pm.width() >= 16:
                    pixmap = pm
                    break

    if pixmap is None or pixmap.isNull():
        return ""

    # Масштабируем до нужного размера
    if pixmap.width() != size or pixmap.height() != size:
        pixmap = pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    # Сохраняем
    pixmap.save(out_path, "PNG")
    return out_path


def resolve_lnk_target(lnk_path: str) -> str:
    """
    Разрешает .lnk ярлык в реальный путь (только Windows).
    На других ОС возвращает исходный путь.
    """
    import sys
    if sys.platform != "win32":
        return lnk_path

    try:
        import ctypes
        from ctypes import wintypes
        import comtypes
        from comtypes import GUID
        from comtypes.persist import IPersistFile
        from comtypes.shelllink import ShellLink  # type: ignore
    except ImportError:
        pass

    # Fallback: через powershell
    try:
        import subprocess
        cmd = (
            f'(New-Object -ComObject WScript.Shell)'
            f'.CreateShortcut("{lnk_path}").TargetPath'
        )
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True, text=True, timeout=5,
        )
        target = result.stdout.strip()
        if target and os.path.exists(target):
            return target
    except Exception:
        pass

    return lnk_path

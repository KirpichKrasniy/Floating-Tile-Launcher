"""
core/folder_scanner.py — Сканирование папки на .exe / .lnk.

Глубина: до 2 уровней подпапок.
Фильтрация:
 • Пропускает служебные файлы (uninstall, setup, vcredist, dotnet и т.д.)
 • Пропускает вторичные exe если главная игра из папки уже добавлена
 • Не дублирует приложения ни по пути, ни по нормализованному имени
"""

from __future__ import annotations

import os
import re
from typing import List

from core.config_manager import TileData, ACCENT_COLORS
from core.icon_extractor import extract_icon, resolve_lnk_target
from core.steamgriddb import search_and_download_grid

_APP_EXTENSIONS = {".exe", ".lnk"}

# ═══════════════════════════════════════════════════════════
#  Чёрные списки для фильтрации
# ═══════════════════════════════════════════════════════════

# Точные имена файлов (lowercase)
_SKIP_EXACT: set[str] = {
    # Деинсталляторы
    "uninstall.exe", "unins000.exe", "unins001.exe", "unins002.exe",
    "uninst.exe", "uninstaller.exe",
    # Инсталляторы / обновления
    "setup.exe", "install.exe", "installer.exe",
    "update.exe", "updater.exe", "autoupdate.exe", "selfupdate.exe",
    "patch.exe", "patcher.exe",
    # Краш-репортеры / диагностика
    "crashreporter.exe", "crash_reporter.exe", "bugreporter.exe",
    "crashhandler.exe", "crashpad_handler.exe",
    "reporter.exe", "sendrpt.exe", "errorreport.exe",
    # Visual C++ Redistributable / .NET
    "vcredist_x86.exe", "vcredist_x64.exe",
    "vc_redist.x86.exe", "vc_redist.x64.exe",
    "vc_redist.arm64.exe",
    "vcredist.exe",
    "dxsetup.exe", "dxwebsetup.exe",
    "dotnetfx35.exe", "ndp48-web.exe", "windowsdesktop-runtime.exe",
    # UE / Unity служебные
    "ue4prereqsetup_x64.exe", "ue4prereqsetup.exe",
    "unrealcefsubprocess.exe", "crashreportclient.exe",
    "unitycrashandler64.exe", "unitycrashandler32.exe",
    # Steam / лаунчеры
    "steam.exe", "steamservice.exe", "steamerrorreporter.exe",
    "steamerrorreporter64.exe",
    "gameoverlayui.exe", "gameoverlayrenderer.exe",
    "bootstrapper.exe",
    # Easy Anti-Cheat / BattlEye
    "easyanticheat_setup.exe", "easyanticheat.exe",
    "beservice.exe", "beclient.exe", "beclient_x64.exe",
    "eac_launcher.exe",
    # Прочее
    "7z.exe", "7za.exe", "7zs.exe",
    "python.exe", "pythonw.exe",
    "java.exe", "javaw.exe",
    "cmd.exe", "conhost.exe",
    "node.exe", "npm.exe",
}

# Подстроки в имени файла — если содержит, пропускаем
_SKIP_SUBSTRINGS: list[str] = [
    "vcredist", "vc_redist",
    "redist", "redistributable",
    "dxsetup", "directx",
    "dotnet", "netfx",
    "uninstall", "uninst",
    "crashreport", "crashhandl", "crashpad",
    "bugreport", "errorreport",
    "update", "patch",
    "setup", "install",
    "prereq",
    "easyanticheat", "battleye", "beclient",
    "anticheat",
    "launcher_helper", "subprocess",
    "vc_x86", "vc_x64",
    "_debug", "_test", "_benchmark",
]

# Подстроки в ПУТИ — если путь содержит такую папку, пропускаем файл
_SKIP_PATH_PARTS: list[str] = [
    "\\redist\\", "/redist/",
    "\\redistributable\\", "/redistributable/",
    "\\__installer\\", "/__installer/",
    "\\_commonredist\\", "/_commonredist/",
    "\\directx\\", "/directx/",
    "\\dotnet\\", "/dotnet/",
    "\\support\\", "/support/",
    "\\tools\\", "/tools/",
    "\\binaries\\", "/binaries/",
    "\\easyanticheat\\", "/easyanticheat/",
    "\\battleye\\", "/battleye/",
]

MAX_DEPTH = 2


def _normalize_label(name: str) -> str:
    """
    Нормализует имя для сравнения дубликатов.
    'Counter-Strike 2' и 'counter_strike_2' → 'counterstrike2'
    """
    s = name.lower()
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def _should_skip(filename: str, full_path: str) -> bool:
    """Проверяет, нужно ли пропустить файл."""
    low = filename.lower()

    # Точное совпадение имени
    if low in _SKIP_EXACT:
        return True

    # Подстроки в имени
    base = os.path.splitext(low)[0]
    for sub in _SKIP_SUBSTRINGS:
        if sub in base:
            return True

    # Подстроки в пути
    path_low = full_path.lower()
    for part in _SKIP_PATH_PARTS:
        if part in path_low:
            return True

    return False


def _listdir_safe(path: str) -> list[str]:
    try:
        return os.listdir(path)
    except OSError:
        return []


def _scan_dir(
    folder: str,
    depth: int,
    config_dir: str,
    existing_paths: set[str],
    existing_labels: set[str],
    added_labels: set[str],
    folder_primaries: dict[str, str],
    tiles: list[TileData],
    color_idx_ref: list[int],
    api_key: str,
) -> None:
    """
    Сканирует одну папку.

    folder_primaries: {нормализованная_папка → нормализованный_label первого exe}
        Если из одной папки уже добавлена игра, вторичные exe пропускаются.
    """
    entries = _listdir_safe(folder)
    folder_norm = os.path.normpath(folder).lower()

    # Собираем все exe в этой папке для определения «главного»
    exe_files = []
    for name in sorted(entries):
        full = os.path.join(folder, name)
        if not os.path.isfile(full):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext not in _APP_EXTENSIONS:
            continue
        if _should_skip(name, full):
            continue
        exe_files.append(name)

    for name in exe_files:
        full = os.path.normpath(os.path.join(folder, name))
        ext = os.path.splitext(name)[1].lower()

        if ext == ".lnk":
            target = resolve_lnk_target(full)
            app_path = full
            icon_source = target
        else:
            app_path = full
            icon_source = full

        # Дубликат по пути
        if app_path in existing_paths or icon_source in existing_paths:
            continue

        label = os.path.splitext(name)[0]
        label_norm = _normalize_label(label)

        # Дубликат по имени
        if label_norm in existing_labels or label_norm in added_labels:
            continue

        # В подпапках (depth > 0): одна игра на папку.
        # В корневой папке (depth == 0): добавляем все найденные exe.
        if depth > 0:
            if folder_norm in folder_primaries:
                primary = folder_primaries[folder_norm]
                if label_norm != primary:
                    continue
            else:
                folder_primaries[folder_norm] = label_norm

        # ── Обложка: SteamGridDB (приоритет), затем локальная иконка ──
        icon_path = ""
        if api_key:
            icon_path = search_and_download_grid(label, api_key, config_dir)
        if not icon_path:
            icon_path = extract_icon(icon_source, config_dir)

        color = ACCENT_COLORS[color_idx_ref[0] % len(ACCENT_COLORS)]
        color_idx_ref[0] += 1

        tiles.append(TileData(
            label=label,
            image_path=icon_path,
            app_path=app_path,
            grid_size=[1, 1],
            color=color,
        ))
        added_labels.add(label_norm)
        existing_paths.add(app_path)

    # Подпапки
    if depth >= MAX_DEPTH:
        return
    for name in sorted(entries):
        sub = os.path.join(folder, name)
        if os.path.isdir(sub):
            _scan_dir(
                sub, depth + 1, config_dir,
                existing_paths, existing_labels, added_labels,
                folder_primaries, tiles, color_idx_ref, api_key,
            )


def scan_folder(
    folder: str,
    config_dir: str,
    existing_app_paths: set[str] | None = None,
    api_key: str = "",
    existing_tiles: list[TileData] | None = None,
) -> List[TileData]:
    """
    Сканирует папку (до 2 уровней подпапок).
    Фильтрует служебные файлы, редистрибутивы, дубликаты.
    Из одной папки добавляет только один (главный) exe.
    """
    if existing_app_paths is None:
        existing_app_paths = set()

    # Собираем нормализованные имена уже существующих плиток
    existing_labels: set[str] = set()
    if existing_tiles:
        for t in existing_tiles:
            if t.label:
                existing_labels.add(_normalize_label(t.label))
            if t.app_path:
                bn = os.path.splitext(os.path.basename(t.app_path))[0]
                existing_labels.add(_normalize_label(bn))

    tiles: list[TileData] = []
    color_idx_ref = [0]
    added_labels: set[str] = set()
    folder_primaries: dict[str, str] = {}

    _scan_dir(
        folder, 0, config_dir,
        set(existing_app_paths), existing_labels, added_labels,
        folder_primaries, tiles, color_idx_ref, api_key,
    )
    return tiles

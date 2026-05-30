"""
core/config_manager.py — Чтение / запись JSON-конфигурации.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class TileData:
    id: str = ""
    label: str = ""
    image_path: str = ""
    app_path: str = ""
    grid_size: List[int] = field(default_factory=lambda: [1, 1])
    grid_position: List[int] = field(default_factory=lambda: [0, 0])
    color: str = "#4285f4"

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        # Гарантируем, что size/position — обычные list[int]
        self.grid_size = list(self.grid_size)
        self.grid_position = list(self.grid_position)


@dataclass
class AppConfig:
    grid_columns: int = 6
    cell_size: int = 100
    gap: int = 8
    steamgriddb_api_key: str = ""
    hotkey: str = ""
    locked: bool = False
    position: str = "center"
    language: str = "ru"
    tiles: List[TileData] = field(default_factory=list)


ACCENT_COLORS: list[str] = [
    "#4285f4", "#ea4335", "#fbbc04", "#34a853",
    "#e040fb", "#00bcd4", "#ff7043", "#7c4dff",
    "#26a69a", "#78909c", "#ff5252", "#448aff",
]

_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none">{}</svg>'

BUILTIN_ICONS: list[str] = [
    _SVG.format(
        '<circle cx="32" cy="32" r="24" stroke="#60a5fa" stroke-width="2.5"/>'
        '<ellipse cx="32" cy="32" rx="12" ry="24" stroke="#60a5fa" stroke-width="2"/>'
        '<line x1="8" y1="32" x2="56" y2="32" stroke="#60a5fa" stroke-width="2"/>'
        '<line x1="32" y1="8" x2="32" y2="56" stroke="#60a5fa" stroke-width="2"/>'
    ),
    _SVG.format(
        '<path d="M12 40V32C12 21 21 12 32 12C43 12 52 21 52 32V40"'
        ' stroke="#e879f9" stroke-width="3" stroke-linecap="round"/>'
        '<rect x="8" y="36" width="8" height="14" rx="4" fill="#e879f9"/>'
        '<rect x="48" y="36" width="8" height="14" rx="4" fill="#e879f9"/>'
    ),
    _SVG.format(
        '<rect x="8" y="12" width="48" height="40" rx="6" stroke="#22d3ee" stroke-width="2.5"/>'
        '<path d="M18 30L26 24L18 18" stroke="#22d3ee" stroke-width="2.5"'
        ' stroke-linecap="round" stroke-linejoin="round"/>'
        '<line x1="28" y1="34" x2="40" y2="34" stroke="#22d3ee" stroke-width="2.5"'
        ' stroke-linecap="round"/>'
    ),
    _SVG.format(
        '<rect x="8" y="14" width="48" height="36" rx="6" stroke="#fb923c" stroke-width="2.5"/>'
        '<circle cx="22" cy="28" r="5" fill="#fbbf24"/>'
        '<path d="M8 42L22 32L34 40L44 34L56 42" stroke="#34d399" stroke-width="2.5"'
        ' stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    _SVG.format(
        '<circle cx="32" cy="32" r="8" stroke="#94a3b8" stroke-width="2.5"/>'
        '<path d="M32 8V14M32 50V56M56 32H50M14 32H8M49 15L44.7 19.3'
        'M19.3 44.7L15 49M49 49L44.7 44.7M19.3 19.3L15 15"'
        ' stroke="#94a3b8" stroke-width="2.5" stroke-linecap="round"/>'
    ),
    _SVG.format(
        '<path d="M12 16C12 13.8 13.8 12 16 12H40C42.2 12 44 13.8 44 16V32'
        'C44 34.2 42.2 36 40 36H24L16 44V36C13.8 36 12 34.2 12 32V16Z"'
        ' fill="#2dd4bf" fill-opacity="0.3" stroke="#2dd4bf" stroke-width="2"/>'
        '<path d="M20 24C20 21.8 21.8 20 24 20H48C50.2 20 52 21.8 52 24V40'
        'C52 42.2 50.2 44 48 44H32L24 52V44C21.8 44 20 42.2 20 40V24Z"'
        ' stroke="#2dd4bf" stroke-width="2"/>'
    ),
    _SVG.format(
        '<path d="M16 24C16 19.6 19.6 16 24 16H40C44.4 16 48 19.6 48 24V36'
        'C48 42 44 48 38 48H26C20 48 16 42 16 36V24Z"'
        ' stroke="#a78bfa" stroke-width="2.5"/>'
        '<circle cx="24" cy="30" r="3" fill="#a78bfa"/>'
        '<circle cx="40" cy="26" r="2.5" fill="#f472b6"/>'
        '<circle cx="44" cy="30" r="2.5" fill="#60a5fa"/>'
        '<circle cx="40" cy="34" r="2.5" fill="#34d399"/>'
        '<circle cx="36" cy="30" r="2.5" fill="#fbbf24"/>'
    ),
    _SVG.format(
        '<rect x="8" y="16" width="48" height="32" rx="6" stroke="#f87171" stroke-width="2.5"/>'
        '<path d="M8 20L32 36L56 20" stroke="#f87171" stroke-width="2.5"'
        ' stroke-linecap="round" stroke-linejoin="round"/>'
        '<circle cx="48" cy="16" r="6" fill="#ef4444"/>'
    ),
    _SVG.format(
        '<rect x="10" y="14" width="44" height="38" rx="6" stroke="#fb923c" stroke-width="2.5"/>'
        '<line x1="10" y1="26" x2="54" y2="26" stroke="#fb923c" stroke-width="2"/>'
        '<line x1="22" y1="10" x2="22" y2="18" stroke="#fb923c" stroke-width="3"'
        ' stroke-linecap="round"/>'
        '<line x1="42" y1="10" x2="42" y2="18" stroke="#fb923c" stroke-width="3"'
        ' stroke-linecap="round"/>'
        '<rect x="18" y="32" width="6" height="6" rx="1.5" fill="#fb923c"/>'
        '<rect x="29" y="32" width="6" height="6" rx="1.5" fill="#fb923c"/>'
        '<rect x="40" y="32" width="6" height="6" rx="1.5" fill="#fb923c"/>'
    ),
    _SVG.format(
        '<path d="M16 12H38L48 22V48C48 50.2 46.2 52 44 52H16'
        'C13.8 52 12 50.2 12 48V16C12 13.8 13.8 12 16 12Z"'
        ' stroke="#a3e635" stroke-width="2.5"/>'
        '<path d="M38 12V22H48" stroke="#a3e635" stroke-width="2.5" stroke-linecap="round"/>'
        '<line x1="20" y1="32" x2="40" y2="32" stroke="#a3e635" stroke-width="2"'
        ' stroke-linecap="round"/>'
        '<line x1="20" y1="38" x2="36" y2="38" stroke="#a3e635" stroke-width="2"'
        ' stroke-linecap="round"/>'
    ),
]


def _create_demo_tiles() -> list[TileData]:
    demos = [
        ("Browser",  0, "#4285f4", [2, 2], [0, 0]),
        ("Music",    1, "#e040fb", [1, 1], [2, 0]),
        ("Code",     2, "#00bcd4", [2, 1], [3, 0]),
        ("Photos",   3, "#ff7043", [1, 2], [5, 0]),
        ("Chat",     5, "#26a69a", [1, 1], [2, 1]),
        ("Settings", 4, "#78909c", [1, 1], [3, 1]),
        ("Game",     6, "#7c4dff", [2, 2], [0, 2]),
        ("Mail",     7, "#ef5350", [2, 1], [4, 1]),
        ("Calendar", 8, "#fb923c", [1, 1], [2, 2]),
        ("Files",    9, "#a3e635", [1, 1], [2, 3]),
    ]
    return [
        TileData(label=l, image_path=f"builtin:{i}", color=c,
                 grid_size=list(s), grid_position=list(p))
        for l, i, c, s, p in demos
    ]


class ConfigManager:
    def __init__(self, path: str):
        self._path = path
        self.config: AppConfig = self._load()

    def save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(asdict(self.config), f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"[ConfigManager] save error: {e}")

    def reset(self) -> AppConfig:
        """Сброс — удаляет все плитки, сохраняет API-ключ."""
        api_key = self.config.steamgriddb_api_key
        self.config = AppConfig(steamgriddb_api_key=api_key, tiles=[])
        self.save()
        return self.config

    def _load(self) -> AppConfig:
        if not os.path.exists(self._path):
            cfg = AppConfig(tiles=_create_demo_tiles())
            self.config = cfg
            self.save()
            return cfg
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            tiles = [TileData(**t) for t in raw.get("tiles", [])]
            return AppConfig(
                grid_columns=int(raw.get("grid_columns", 6)),
                cell_size=int(raw.get("cell_size", 100)),
                gap=int(raw.get("gap", 8)),
                steamgriddb_api_key=str(raw.get("steamgriddb_api_key", "")),
                hotkey=str(raw.get("hotkey", "")),
                locked=bool(raw.get("locked", False)),
                position=str(raw.get("position", "center")),
                language=str(raw.get("language", "ru")),
                tiles=tiles,
            )
        except Exception as e:
            print(f"[ConfigManager] corrupted config, reset: {e}")
            return self.reset()

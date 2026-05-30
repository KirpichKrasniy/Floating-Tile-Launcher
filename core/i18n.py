"""
core/i18n.py — Локализация из JSON-файлов в папке lang/.

Каждый файл lang/{code}.json содержит пары "ключ": "перевод".
Поле "_name" задаёт отображаемое название языка.

Для добавления нового языка: создайте файл lang/{code}.json,
скопировав структуру из lang/en.json.
"""

from __future__ import annotations

import os
import json

_strings: dict[str, dict[str, str]] = {}
_current: str = "ru"
_lang_dir: str = ""


def init(lang_dir: str):
    """Загружает все JSON-файлы из папки lang/."""
    global _lang_dir
    _lang_dir = lang_dir
    _strings.clear()

    if not os.path.isdir(lang_dir):
        os.makedirs(lang_dir, exist_ok=True)
        return

    for fname in os.listdir(lang_dir):
        if not fname.endswith(".json"):
            continue
        code = fname[:-5]  # "ru.json" → "ru"
        path = os.path.join(lang_dir, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                _strings[code] = data
        except Exception as e:
            print(f"[i18n] Error loading {fname}: {e}")


def set_language(lang: str):
    global _current
    if lang in _strings:
        _current = lang
    elif _strings:
        _current = next(iter(_strings))


def t(key: str) -> str:
    """Возвращает перевод по ключу. Fallback: en → ключ."""
    val = _strings.get(_current, {}).get(key)
    if val is not None:
        return val
    val = _strings.get("en", {}).get(key)
    if val is not None:
        return val
    return key


def available_languages() -> list[tuple[str, str]]:
    """Возвращает [(code, display_name), ...], отсортированный."""
    result = []
    for code, data in sorted(_strings.items()):
        name = data.get("_name", code)
        result.append((code, name))
    return result

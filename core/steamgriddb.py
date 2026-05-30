"""
core/steamgriddb.py — Клиент SteamGridDB API v2.

search_grids()             → возвращает список обложек (для галереи)
download_grid()            → скачивает одну обложку по URL
search_and_download_grid() → автоматически: ищет + скачивает лучшую
"""

from __future__ import annotations

import os
import hashlib
import json
from urllib import request, error, parse
from dataclasses import dataclass

_BASE = "https://www.steamgriddb.com/api/v2"
_TIMEOUT = 10

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


@dataclass
class GridImage:
    """Одна обложка из SteamGridDB."""
    id: int
    url: str
    thumb: str
    width: int
    height: int
    score: int
    style: str
    author: str


def _grids_dir(config_dir: str) -> str:
    d = os.path.join(config_dir, "grids")
    os.makedirs(d, exist_ok=True)
    return d


def _hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


def _api_get(path: str, api_key: str) -> dict | None:
    url = f"{_BASE}/{path}"
    req = request.Request(url, headers={
        "Authorization": f"Bearer {api_key}",
        "User-Agent": _UA,
        "Accept": "application/json",
    })
    try:
        with request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        print(f"[SteamGridDB] HTTP {e.code}: {e.reason} | {body}")
        return None
    except (error.URLError, json.JSONDecodeError, OSError) as e:
        print(f"[SteamGridDB] error: {e}")
        return None


def _download_file(url: str, dest: str) -> bool:
    try:
        req = request.Request(url, headers={"User-Agent": _UA})
        with request.urlopen(req, timeout=_TIMEOUT * 3) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except (error.URLError, error.HTTPError, OSError) as e:
        print(f"[SteamGridDB] Download error: {e}")
        return False


def _aspect_score(img: GridImage, target_ratio: float) -> float:
    if img.width <= 0 or img.height <= 0:
        return 999.0
    return abs(img.width / img.height - target_ratio)


# ══════════════════════════════════════════════════════════
#  Публичный API
# ══════════════════════════════════════════════════════════

def search_grids(
    game_name: str,
    api_key: str,
    tile_size: list[int] | None = None,
) -> list[GridImage]:
    """
    Ищет обложки на SteamGridDB. Возвращает список GridImage,
    отсортированный по совпадению пропорций с tile_size, затем по score.
    """
    if not api_key or not game_name.strip():
        return []

    encoded = parse.quote(game_name.strip())
    data = _api_get(f"search/autocomplete/{encoded}", api_key)
    if not data or not data.get("success") or not data.get("data"):
        return []

    game_id = data["data"][0].get("id")
    if not game_id:
        return []

    grids_data = _api_get(
        f"grids/game/{game_id}?nsfw=false&humor=false", api_key
    )
    if not grids_data or not grids_data.get("success") or not grids_data.get("data"):
        return []

    images: list[GridImage] = []
    for raw in grids_data["data"]:
        images.append(GridImage(
            id=raw.get("id", 0),
            url=raw.get("url", ""),
            thumb=raw.get("thumb", raw.get("url", "")),
            width=raw.get("width", 0),
            height=raw.get("height", 0),
            score=raw.get("score", 0),
            style=raw.get("style", ""),
            author=raw.get("author", {}).get("name", ""),
        ))

    target_ratio = 1.0
    if tile_size and len(tile_size) == 2 and tile_size[1] > 0:
        target_ratio = tile_size[0] / tile_size[1]

    images.sort(key=lambda img: (
        _aspect_score(img, target_ratio),
        -img.score,
    ))

    return images


def download_grid(
    image_url: str,
    game_name: str,
    config_dir: str,
    suffix: str = "",
) -> str:
    """Скачивает одну обложку по URL. Возвращает путь или ''."""
    grids = _grids_dir(config_dir)
    cache_key = _hash(game_name.lower() + suffix)

    ext = ".png"
    url_low = image_url.lower()
    if ".jpg" in url_low or ".jpeg" in url_low:
        ext = ".jpg"
    elif ".webp" in url_low:
        ext = ".webp"

    out_path = os.path.join(grids, f"{cache_key}{ext}")
    if os.path.isfile(out_path):
        return out_path

    if _download_file(image_url, out_path):
        return out_path
    return ""


def search_and_download_grid(
    game_name: str,
    api_key: str,
    config_dir: str,
    tile_size: list[int] | None = None,
) -> str:
    """Автоматически ищет + скачивает лучшую обложку."""
    if not api_key or not game_name.strip():
        return ""

    size_tag = ""
    if tile_size:
        size_tag = f"_{tile_size[0]}x{tile_size[1]}"
    grids = _grids_dir(config_dir)
    cache_key = _hash(game_name.lower() + size_tag)
    for ext in (".png", ".jpg", ".webp"):
        cached = os.path.join(grids, f"{cache_key}{ext}")
        if os.path.isfile(cached):
            return cached

    images = search_grids(game_name, api_key, tile_size)
    if not images:
        return ""

    best = images[0]
    if not best.url:
        return ""

    return download_grid(best.url, game_name, config_dir, size_tag)


def is_api_key_valid(api_key: str) -> bool:
    if not api_key or len(api_key) < 10:
        return False
    data = _api_get("search/autocomplete/test", api_key)
    return data is not None and data.get("success", False)

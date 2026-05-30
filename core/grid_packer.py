"""
core/grid_packer.py — 2D Bin-Packing для плиточной сетки.

Плитки размещаются В ПОРЯДКЕ ДОБАВЛЕНИЯ (без сортировки по площади),
чтобы новые плитки всегда появлялись в конце.
Каждая плитка ставится в первую свободную позицию (top-left gravity).
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.config_manager import TileData

MAX_ROWS = 100


def _can_place(grid: list[list[bool]], col: int, row: int,
               w: int, h: int, columns: int) -> bool:
    if col + w > columns or row + h > MAX_ROWS:
        return False
    for r in range(row, row + h):
        for c in range(col, col + w):
            if grid[r][c]:
                return False
    return True


def _mark(grid: list[list[bool]], col: int, row: int, w: int, h: int) -> None:
    for r in range(row, row + h):
        for c in range(col, col + w):
            grid[r][c] = True


def _find_position(grid: list[list[bool]], w: int, h: int,
                   columns: int) -> tuple[int, int] | None:
    for row in range(MAX_ROWS):
        for col in range(columns - w + 1):
            if _can_place(grid, col, row, w, h, columns):
                return col, row
    return None


def pack_tiles(tiles: list["TileData"], columns: int) -> list["TileData"]:
    """
    Упаковка плиток БЕЗ сортировки — в порядке добавления.
    Новые плитки всегда оказываются в конце (внизу) сетки.
    Пустоты заполняются: каждая плитка ставится в первое
    свободное место сверху-вниз, слева-направо.
    """
    if not tiles:
        return []
    grid = [[False] * columns for _ in range(MAX_ROWS)]
    result: list["TileData"] = []
    for tile in tiles:
        w = min(tile.grid_size[0], columns)
        h = tile.grid_size[1]
        pos = _find_position(grid, w, h, columns)
        if pos:
            col, row = pos
            _mark(grid, col, row, w, h)
            tile.grid_position = [col, row]
        result.append(tile)
    return result


def pack_with_pinned(
    tiles: list["TileData"],
    columns: int,
    pinned_id: str,
    pinned_col: int,
    pinned_row: int,
) -> list["TileData"]:
    """
    Упаковка с одной «закреплённой» плиткой.
    Закреплённая плитка ставится первой в заданную позицию,
    все остальные упаковываются вокруг неё в порядке добавления.
    Возвращает новый список с обновлёнными grid_position (не мутирует входной).
    """
    if not tiles:
        return []

    grid = [[False] * columns for _ in range(MAX_ROWS)]
    result: list["TileData"] = []

    # Сначала ставим закреплённую плитку
    pinned = None
    others = []
    for t in tiles:
        if t.id == pinned_id:
            pinned = t
        else:
            others.append(t)

    if pinned:
        w = min(pinned.grid_size[0], columns)
        h = pinned.grid_size[1]
        pc = max(0, min(pinned_col, columns - w))
        pr = max(0, pinned_row)
        if _can_place(grid, pc, pr, w, h, columns):
            _mark(grid, pc, pr, w, h)
            # Создаём копию чтобы не мутировать оригинал
            import copy
            p_copy = copy.copy(pinned)
            p_copy.grid_position = [pc, pr]
            result.append(p_copy)
        else:
            # Если не помещается — ставим как обычно
            others.insert(0, pinned)

    # Остальные плитки упаковываем вокруг
    for tile in others:
        import copy
        t_copy = copy.copy(tile)
        w = min(t_copy.grid_size[0], columns)
        h = t_copy.grid_size[1]
        pos = _find_position(grid, w, h, columns)
        if pos:
            col, row = pos
            _mark(grid, col, row, w, h)
            t_copy.grid_position = [col, row]
        result.append(t_copy)

    return result


def is_position_available(tiles: list["TileData"], col: int, row: int,
                          w: int, h: int, columns: int,
                          exclude_id: str = "") -> bool:
    if col < 0 or row < 0 or col + w > columns:
        return False
    grid = [[False] * columns for _ in range(MAX_ROWS)]
    for t in tiles:
        if t.id == exclude_id:
            continue
        _mark(grid, t.grid_position[0], t.grid_position[1],
              t.grid_size[0], t.grid_size[1])
    return _can_place(grid, col, row, w, h, columns)


def get_grid_height(tiles: list["TileData"]) -> int:
    if not tiles:
        return 2
    h = 0
    for t in tiles:
        bottom = t.grid_position[1] + t.grid_size[1]
        if bottom > h:
            h = bottom
    return max(h, 2)

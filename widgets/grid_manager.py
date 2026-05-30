"""
widgets/grid_manager.py — Grid container for tiles / Контейнер сетки плиток.

RU: Управляет расположением плиток в сетке, обрабатывает drag-and-drop,
    контекстное меню, операции добавления/удаления/ресайза.
EN: Manages tile layout on the grid, handles drag-and-drop,
    context menu, add/delete/resize operations.

Drag-and-Drop logic / Логика перетаскивания:
- Swap: when dropped on another tile, they exchange positions in the list,
  then pack_tiles() repacks everything without overlaps.
  (при бросании на другую плитку — меняются индексами в списке,
  затем pack_tiles() переупаковывает без наложений.)
- Free move: when dropped on an empty area, the tile moves there directly,
  other tiles stay in place.
  (при бросании в пустое место — плитка просто переезжает туда,
  остальные не двигаются.)
"""

from __future__ import annotations

import os
import random

from PySide6.QtWidgets import QWidget, QMenu, QFileDialog
from PySide6.QtCore import (
    Qt, Signal, QPoint, QPropertyAnimation, QEasingCurve,
    QParallelAnimationGroup,
)
from PySide6.QtGui import (
    QColor, QPainter, QPen, QPainterPath, QMouseEvent,
    QContextMenuEvent, QBrush,
)

from core.config_manager import ConfigManager, TileData, ACCENT_COLORS, BUILTIN_ICONS
from core.grid_packer import pack_tiles, is_position_available, get_grid_height
from core.folder_scanner import scan_folder
from core.steamgriddb import search_and_download_grid, search_grids, download_grid
from core.i18n import t
from widgets.tile_widget import TileWidget, TILE_SIZES


class GridManager(QWidget):
    """
    RU: Виджет-контейнер, в котором живут все плитки.
        Отвечает за их расположение, drag-and-drop, контекстное меню.
    EN: Container widget that holds all tiles.
        Responsible for their layout, drag-and-drop, context menu.
    """

    # RU: Сигнал для показа toast-уведомлений (message, type)
    # EN: Signal to show toast notifications (message, type)
    toast_requested = Signal(str, str)

    # RU: Сигнал об изменении размера сетки (для auto-fit окна)
    # EN: Signal when grid size changes (for window auto-fit)
    grid_resized = Signal()

    @property
    def locked(self) -> bool:
        """RU: Заблокирована ли перестановка / EN: Is reordering locked."""
        return self._locked

    def set_locked(self, val: bool):
        self._locked = val

    def __init__(self, config_mgr: ConfigManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.cfg = config_mgr
        self.setMouseTracking(True)

        # RU: Флаг блокировки перестановки плиток
        # EN: Lock flag — prevents tile reordering when True
        self._locked = False

        # RU: Состояние перетаскивания
        # EN: Drag state
        self._dragging_id: str | None = None    # ID перетаскиваемой плитки / dragged tile ID
        self._drag_offset = QPoint()            # Смещение курсора внутри плитки / cursor offset inside tile
        self._drop_col = -1                     # Целевая колонка сетки / target grid column
        self._drop_row = -1                     # Целевая строка сетки / target grid row
        self._drop_valid = False                # Валидна ли целевая позиция / is target position valid

        # RU: Словарь виджетов плиток: tile.id → TileWidget
        # EN: Tile widget dictionary: tile.id → TileWidget
        self._tile_widgets: dict[str, TileWidget] = {}

        # RU: Группа анимаций для одновременного перемещения нескольких плиток
        # EN: Animation group for simultaneous tile movement
        self._anim_group: QParallelAnimationGroup | None = None

        # RU: Первичное построение сетки из конфига
        # EN: Initial grid build from config
        self._rebuild_all()

    # ── Shortcut properties / Свойства-шорткаты к конфигу ──

    @property
    def columns(self) -> int:
        return self.cfg.config.grid_columns

    @property
    def cell(self) -> int:
        return self.cfg.config.cell_size

    @property
    def gap_(self) -> int:
        return self.cfg.config.gap

    @property
    def tiles(self) -> list[TileData]:
        return self.cfg.config.tiles

    def _calc_size(self):
        """
        RU: Пересчитывает и устанавливает размер виджета сетки
            на основе текущих плиток.
        EN: Recalculates and sets the grid widget size
            based on current tiles.
        """
        h = get_grid_height(self.tiles)
        w = self.columns * (self.cell + self.gap_) - self.gap_
        total_h = h * (self.cell + self.gap_) - self.gap_
        self.setFixedSize(max(w, 50), max(total_h, 50))

    # ══════════════════════════════════════════════════════════
    #  Full rebuild / Полное пересоздание
    #  (при старте / смене настроек сетки)
    #  (on start / when grid settings change)
    # ══════════════════════════════════════════════════════════

    def _rebuild_all(self):
        """
        RU: Удаляет все виджеты и создаёт новые из текущего конфига.
        EN: Destroys all widgets and recreates them from current config.
        """
        for tw in self._tile_widgets.values():
            tw.setParent(None)
            tw.deleteLater()
        self._tile_widgets.clear()

        for tile in self.tiles:
            self._make_widget(tile)

        self._calc_size()
        self.update()
        self.grid_resized.emit()

    def _make_widget(self, tile: TileData) -> TileWidget:
        """
        RU: Создаёт TileWidget для одной плитки и подключает все сигналы.
        EN: Creates a TileWidget for one tile and connects all signals.
        """
        tw = TileWidget(tile, self.cell, self.gap_, parent=self)
        tw.delete_requested.connect(self._on_delete)
        tw.resize_requested.connect(self._on_resize)
        tw.image_changed.connect(self._on_image_changed)
        tw.color_changed.connect(self._on_color_changed)
        tw.app_path_changed.connect(self._on_app_path_changed)
        tw.label_changed.connect(self._on_label_changed)
        tw.fetch_grid_requested.connect(self._on_fetch_grid)
        tw.launch_failed.connect(lambda msg: self.toast_requested.emit(msg, "error"))
        tw.drag_started.connect(self._on_drag_started)
        tw.show()
        self._tile_widgets[tile.id] = tw
        return tw

    # ══════════════════════════════════════════════════════════
    #  Animated reflow / Анимированная перестройка
    #  (при добавлении, удалении, ресайзе плиток)
    #  (on add, delete, resize of tiles)
    # ══════════════════════════════════════════════════════════

    def _reflow_animated(self):
        """
        RU: Переупаковывает все плитки через pack_tiles(),
            удаляет лишние виджеты, создаёт недостающие,
            и плавно анимирует перемещение.
        EN: Repacks all tiles via pack_tiles(),
            removes stale widgets, creates missing ones,
            and smoothly animates movement.
        """
        # RU: Переупаковка позиций без наложений
        # EN: Repack positions without overlaps
        self.cfg.config.tiles = pack_tiles(self.tiles, self.columns)
        self.cfg.save()

        # RU: Удаляем виджеты для плиток, которых больше нет
        # EN: Remove widgets for tiles that no longer exist
        live_ids = {t.id for t in self.tiles}
        for tid in list(self._tile_widgets.keys()):
            if tid not in live_ids:
                self._tile_widgets[tid].setParent(None)
                self._tile_widgets[tid].deleteLater()
                del self._tile_widgets[tid]

        # RU: Создаём виджеты для новых плиток
        # EN: Create widgets for new tiles
        for tile in self.tiles:
            if tile.id not in self._tile_widgets:
                tw = self._make_widget(tile)
                tw.update_geometry()

        # RU: Запускаем параллельную анимацию перемещения всех плиток
        # EN: Start parallel animation moving all tiles to new positions
        if self._anim_group:
            self._anim_group.stop()
        self._anim_group = QParallelAnimationGroup(self)

        for tile in self.tiles:
            tw = self._tile_widgets.get(tile.id)
            if not tw:
                continue
            tw.tile = tile
            tw.cell_size = self.cell
            tw.gap = self.gap_

            target = tw.grid_to_pixel()
            target_w = tw.pixel_width()
            target_h = tw.pixel_height()

            # RU: Если размер плитки изменился — обновляем размер виджета и иконку
            # EN: If tile size changed — update widget size and reload icon
            if tw.width() != target_w or tw.height() != target_h:
                tw.setFixedSize(target_w, target_h)
                tw.resize(target_w, target_h)
                tw.reload_icon()

            current = tw.pos()
            if current != target:
                anim = QPropertyAnimation(tw, b"pos")
                anim.setDuration(280)
                anim.setStartValue(current)
                anim.setEndValue(target)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                self._anim_group.addAnimation(anim)

        self._anim_group.start()
        self._calc_size()
        self.update()
        self.grid_resized.emit()

    # ══════════════════════════════════════════════════════════
    #  Paint / Отрисовка
    # ══════════════════════════════════════════════════════════

    def paintEvent(self, _event):
        """
        RU: Рисует индикатор целевой позиции при перетаскивании.
            Зелёный = можно бросить, красный = нельзя.
        EN: Draws drop target indicator during drag.
            Green = valid, red = invalid.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._dragging_id and self._drop_col >= 0:
            tile = self._find_tile(self._dragging_id)
            if tile:
                x = self._drop_col * (self.cell + self.gap_)
                y = self._drop_row * (self.cell + self.gap_)
                tw = tile.grid_size[0] * self.cell + (tile.grid_size[0] - 1) * self.gap_
                th = tile.grid_size[1] * self.cell + (tile.grid_size[1] - 1) * self.gap_

                if self._drop_valid:
                    color = QColor(76, 175, 80, 60)
                    border = QColor(76, 175, 80)
                else:
                    color = QColor(244, 67, 54, 60)
                    border = QColor(244, 67, 54)

                path = QPainterPath()
                path.addRoundedRect(float(x), float(y), float(tw), float(th), 16, 16)
                painter.fillPath(path, QBrush(color))
                painter.setPen(QPen(border, 2, Qt.PenStyle.DashLine))
                painter.drawPath(path)

        painter.end()

    # ══════════════════════════════════════════════════════════
    #  Drag-and-Drop
    #
    #  RU: Перетаскивание плиток с обменом местами.
    #      При бросании на другую плитку — swap индексов + repack.
    #      При бросании в пустое место — прямое перемещение.
    #  EN: Tile dragging with position swap.
    #      On drop onto another tile — swap indices + repack.
    #      On drop onto empty space — direct move.
    # ══════════════════════════════════════════════════════════

    def _tile_at_cell(self, col: int, row: int, exclude_id: str = "") -> TileData | None:
        """
        RU: Ищет плитку, чья область покрывает ячейку (col, row).
        EN: Finds a tile whose area covers the cell (col, row).
        """
        for tile in self.tiles:
            if tile.id == exclude_id:
                continue
            tc, tr = tile.grid_position
            tw, th = tile.grid_size
            if tc <= col < tc + tw and tr <= row < tr + th:
                return tile
        return None

    def _on_drag_started(self, tile_id: str, global_pos: QPoint):
        """
        RU: Начало перетаскивания. Запоминаем смещение курсора,
            переводим плитку в drag-режим, захватываем мышь.
            Если заблокировано — сбрасываем drag-состояние плитки.
        EN: Drag start. Store cursor offset, set tile to drag mode,
            grab mouse.
            If locked — reset tile drag state immediately.
        """
        if self._locked:
            # RU: Сбрасываем drag-состояние, которое плитка уже выставила
            # EN: Reset drag state that the tile already set
            tw = self._tile_widgets.get(tile_id)
            if tw:
                tw.set_dragging(False)
            return
        self._dragging_id = tile_id
        tw = self._tile_widgets.get(tile_id)
        if not tw:
            self._dragging_id = None
            return

        # RU: Смещение курсора относительно верхнего левого угла плитки
        # EN: Cursor offset relative to the top-left corner of the tile
        local = self.mapFromGlobal(global_pos)
        tile_pos = tw.grid_to_pixel()
        self._drag_offset = local - tile_pos

        tw.set_dragging(True)
        tw.raise_()       # RU: Поднимаем поверх остальных / EN: Raise above others
        self.grabMouse()   # RU: Захватываем мышь на уровне GridManager / EN: Grab mouse at GridManager level

    def mouseMoveEvent(self, event: QMouseEvent):
        """
        RU: Обработка движения мыши во время drag.
            Двигает виджет за курсором и вычисляет целевую ячейку.
            Показывает live preview обмена.
        EN: Mouse move handler during drag.
            Moves the widget following cursor and calculates target cell.
            Shows live swap preview.
        """
        if not self._dragging_id:
            return
        tile = self._find_tile(self._dragging_id)
        if not tile:
            return

        pos = event.position().toPoint()
        step = self.cell + self.gap_

        # RU: Двигаем сам виджет за курсором (свободно, без привязки к сетке)
        # EN: Move the widget freely following cursor (no grid snap)
        drag_tw = self._tile_widgets.get(self._dragging_id)
        if drag_tw:
            drag_tw.move(pos.x() - self._drag_offset.x(),
                         pos.y() - self._drag_offset.y())

        # RU: Вычисляем целевую ячейку по центру перетаскиваемой плитки
        # EN: Calculate target cell by the center of the dragged tile
        cx = pos.x() - self._drag_offset.x() + drag_tw.width() // 2 if drag_tw else pos.x()
        cy = pos.y() - self._drag_offset.y() + drag_tw.height() // 2 if drag_tw else pos.y()
        col = max(0, min(int(cx / step), self.columns - 1))
        row = max(0, int(cy / step))

        # RU: Не обновляем, если целевая ячейка не изменилась
        # EN: Skip update if target cell hasn't changed
        if col == self._drop_col and row == self._drop_row:
            return

        self._drop_col = col
        self._drop_row = row
        self._drop_valid = True

        # RU: Live preview: если под курсором есть плитка — показываем
        #     анимированный обмен (целевая плитка едет на место перетаскиваемой).
        # EN: Live preview: if there's a tile under cursor — show animated swap
        #     (target tile moves to the position of the dragged one).
        target = self._tile_at_cell(col, row, self._dragging_id)
        if target:
            target_tw = self._tile_widgets.get(target.id)
            if target_tw:
                src_pos = QPoint(
                    tile.grid_position[0] * step,
                    tile.grid_position[1] * step,
                )
                if target_tw.pos() != src_pos:
                    anim = QPropertyAnimation(target_tw, b"pos")
                    anim.setDuration(180)
                    anim.setEndValue(src_pos)
                    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        self.update()

    def mouseReleaseEvent(self, _event: QMouseEvent):
        """
        RU: Завершение drag. Два сценария:
            1) Если бросили на другую плитку — swap индексов + repack.
            2) Если бросили в пустое место — прямое перемещение
               (только если вся область свободна).
        EN: Drag end. Two scenarios:
            1) Dropped on another tile — swap indices + repack.
            2) Dropped on empty space — direct move
               (only if entire area is free).
        """
        if not self._dragging_id:
            return
        self.releaseMouse()

        tile = self._find_tile(self._dragging_id)
        if tile and self._drop_col >= 0:
            target = self._tile_at_cell(self._drop_col, self._drop_row, self._dragging_id)
            if target:
                # RU: Обмен: меняем индексы в списке, затем repack через pack_tiles.
                #     pack_tiles() гарантирует отсутствие наложений после обмена.
                # EN: Swap: exchange indices in list, then repack via pack_tiles.
                #     pack_tiles() guarantees no overlaps after swap.
                tiles = self.cfg.config.tiles
                idx_drag = next(i for i, x in enumerate(tiles) if x.id == tile.id)
                idx_tgt = next(i for i, x in enumerate(tiles) if x.id == target.id)
                tiles[idx_drag], tiles[idx_tgt] = tiles[idx_tgt], tiles[idx_drag]
                self.cfg.config.tiles = pack_tiles(self.cfg.config.tiles, self.columns)
            else:
                # RU: Пустое место — ставим плитку туда напрямую,
                #     если вся её область свободна. Остальные не двигаются.
                # EN: Empty space — place tile there directly,
                #     only if entire tile area is free. Others stay in place.
                if is_position_available(
                    self.tiles, self._drop_col, self._drop_row,
                    tile.grid_size[0], tile.grid_size[1],
                    self.columns, self._dragging_id,
                ):
                    tile.grid_position = [self._drop_col, self._drop_row]
                # RU: Если не помещается — плитка остаётся на месте
                # EN: If doesn't fit — tile stays in its original position

            self.cfg.save()

        # RU: Сброс drag-состояния у виджета плитки
        # EN: Reset drag state on the tile widget
        tw = self._tile_widgets.get(self._dragging_id)
        if tw:
            tw.set_dragging(False)

        # RU: Синхронизируем геометрию всех виджетов с данными
        # EN: Sync all widget geometries with tile data
        for tile_data in self.tiles:
            w = self._tile_widgets.get(tile_data.id)
            if w:
                w.tile = tile_data
                w.update_geometry()

        self._dragging_id = None
        self._drop_col = -1
        self._drop_row = -1
        self._drop_valid = False

        self._calc_size()
        self.update()

    # ══════════════════════════════════════════════════════════
    #  Context menu / Контекстное меню (ПКМ на пустом месте)
    # ══════════════════════════════════════════════════════════

    def contextMenuEvent(self, event: QContextMenuEvent):
        """
        RU: Показывает меню с вариантами добавления плитки.
            Срабатывает только на пустом месте сетки.
        EN: Shows menu with tile-adding options.
            Fires only on empty grid space.
        """
        # RU: Если клик попал на плитку — её собственное меню, не наше
        # EN: If clicked on a tile — its own menu handles it, not ours
        for tw in self._tile_widgets.values():
            if tw.geometry().contains(event.pos()):
                return

        menu = QMenu(self)
        menu.setStyleSheet(TileWidget._menu_stylesheet())

        header = menu.addAction("Добавить плитку")
        header.setEnabled(False)
        menu.addSeparator()

        for label, size in TILE_SIZES:
            act = menu.addAction(f"＋  {label}")
            act.triggered.connect(
                lambda _checked=False, s=list(size): self.add_tile(s))

        menu.addSeparator()
        act_folder = menu.addAction("📂  Импорт из папки…")
        act_folder.triggered.connect(self.import_from_folder)

        menu.exec(event.globalPos())

    # ══════════════════════════════════════════════════════════
    #  CRUD operations / CRUD-операции
    # ══════════════════════════════════════════════════════════

    def add_tile(self, size: list[int] | None = None):
        """RU: Добавляет пустую плитку с рандомной иконкой / EN: Adds empty tile with random icon."""
        if size is None:
            size = [1, 1]
        idx = random.randint(0, len(BUILTIN_ICONS) - 1)
        tile = TileData(
            image_path=f"builtin:{idx}",
            grid_size=list(size),
            color=random.choice(ACCENT_COLORS),
        )
        self.cfg.config.tiles.append(tile)
        self._reflow_animated()
        self.toast_requested.emit("Добавлено", "success")

    def add_tile_data(self, tile: TileData):
        """RU: Добавляет готовый TileData (из диалога) / EN: Adds a ready TileData (from dialog)."""
        self.cfg.config.tiles.append(tile)
        self._reflow_animated()
        self.toast_requested.emit("Добавлено", "success")

    def import_from_folder(self):
        """
        RU: Открывает диалог выбора папки, сканирует .exe/.lnk,
            извлекает иконки, добавляет плитки.
        EN: Opens folder picker, scans for .exe/.lnk,
            extracts icons, adds tiles.
        """
        folder = QFileDialog.getExistingDirectory(
            self, "Выбрать папку с приложениями", "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if not folder:
            return

        existing = {t.app_path for t in self.tiles if t.app_path}
        config_dir = os.path.dirname(self.cfg._path)
        api_key = self.cfg.config.steamgriddb_api_key
        new_tiles = scan_folder(
            folder, config_dir, existing, api_key,
            existing_tiles=list(self.tiles),
        )

        if not new_tiles:
            self.toast_requested.emit("Приложений не найдено", "warning")
            return

        self.cfg.config.tiles.extend(new_tiles)
        self._reflow_animated()
        self.toast_requested.emit(
            f"Добавлено {len(new_tiles)} приложений", "success")

    def _on_delete(self, tile_id: str):
        """RU: Удаление плитки / EN: Delete a tile."""
        self.cfg.config.tiles = [t for t in self.tiles if t.id != tile_id]
        self._reflow_animated()
        self.toast_requested.emit("Удалено", "info")

    def _on_resize(self, tile_id: str, new_size: list[int]):
        """RU: Изменение размера плитки / EN: Resize a tile."""
        tile = self._find_tile(tile_id)
        if tile:
            tile.grid_size = list(new_size)
            self._reflow_animated()
            self.toast_requested.emit(f"Размер → {new_size[0]}×{new_size[1]}", "info")

    def _on_image_changed(self, tile_id: str, path: str):
        """RU: Смена иконки / EN: Change icon."""
        tile = self._find_tile(tile_id)
        if tile:
            tile.image_path = path
            self.cfg.save()
            tw = self._tile_widgets.get(tile_id)
            if tw:
                tw.tile = tile
                tw.reload_icon()
            self.toast_requested.emit("Иконка изменена", "success")

    def _on_label_changed(self, tile_id: str, new_label: str):
        """RU: Переименование плитки / EN: Rename a tile."""
        tile = self._find_tile(tile_id)
        if tile:
            tile.label = new_label
            self.cfg.save()
            self.toast_requested.emit(t("added"), "success")

    def _on_color_changed(self, tile_id: str, color: str):
        """RU: Смена цвета / EN: Change color."""
        tile = self._find_tile(tile_id)
        if tile:
            tile.color = color
            self.cfg.save()
            tw = self._tile_widgets.get(tile_id)
            if tw:
                tw.tile = tile
                tw.update()
            self.toast_requested.emit("Цвет изменён", "success")

    def _on_fetch_grid(self, tile_id: str):
        """
        RU: Поиск обложки на SteamGridDB. Показывает галерею с выбором.
        EN: Search cover on SteamGridDB. Shows gallery picker.
        """
        tile = self._find_tile(tile_id)
        if not tile:
            return

        api_key = self.cfg.config.steamgriddb_api_key
        if not api_key:
            self.toast_requested.emit(
                "Введите API-ключ SteamGridDB в настройках", "warning")
            return

        search_name = tile.label or os.path.splitext(
            os.path.basename(tile.app_path))[0]
        if not search_name:
            self.toast_requested.emit("Нет имени для поиска", "warning")
            return

        self.toast_requested.emit(f"Поиск: {search_name}…", "info")

        images = search_grids(search_name, api_key, tile.grid_size)
        if not images:
            self.toast_requested.emit(
                f"Обложки не найдены: {search_name}", "warning")
            return

        # RU: Открываем диалог с галереей миниатюр
        # EN: Open gallery dialog with thumbnails
        from windows.grid_picker import GridPickerDialog
        dlg = GridPickerDialog(images, parent=self)
        if dlg.exec() and dlg.selected_image:
            config_dir = os.path.dirname(self.cfg._path)
            grid_path = download_grid(
                dlg.selected_image.url, search_name, config_dir,
                suffix=f"_sel{dlg.selected_image.id}",
            )
            if grid_path:
                tile.image_path = grid_path
                self.cfg.save()
                tw = self._tile_widgets.get(tile_id)
                if tw:
                    tw.tile = tile
                    tw.reload_icon()
                self.toast_requested.emit("Обложка установлена", "success")
            else:
                self.toast_requested.emit("Ошибка скачивания", "error")

    def _on_app_path_changed(self, tile_id: str, app_path: str):
        """RU: Привязка/отвязка приложения / EN: Bind/unbind application."""
        tile = self._find_tile(tile_id)
        if tile:
            tile.app_path = app_path
            self.cfg.save()
            tw = self._tile_widgets.get(tile_id)
            if tw:
                tw.tile = tile
                tw.update()
            if app_path:
                self.toast_requested.emit(
                    f"Привязано: {os.path.basename(app_path)}", "success")
            else:
                self.toast_requested.emit("Отвязано", "info")

    def _find_tile(self, tile_id: str) -> TileData | None:
        """RU: Поиск плитки по ID / EN: Find tile by ID."""
        for t in self.tiles:
            if t.id == tile_id:
                return t
        return None

    def apply_settings(self):
        """
        RU: Применяет новые настройки сетки — полная перестройка.
        EN: Applies new grid settings — full rebuild.
        """
        self.cfg.config.tiles = pack_tiles(self.tiles, self.columns)
        self.cfg.save()
        self._rebuild_all()

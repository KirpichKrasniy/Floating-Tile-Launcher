<p align="center">
  <h1 align="center">🎮 Tile Launcher</h1>
  <p align="center">
    A modern tile-based application launcher inspired by Windows 8.<br>
    Drag-and-drop grid, SteamGridDB covers, global hotkey, full localization.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/PySide6-6.6+-green?logo=qt&logoColor=white" alt="PySide6">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="MIT">
  <img src="https://img.shields.io/badge/platform-Windows-lightgrey1" alt="Platform">
</p>

---

<p align="center">
  <img src="https://raw.githubusercontent.com/KirpichKrasniy/Floating-Tile-Launcher/a77bcf35639d5de8f66d18298856a71b33e4dce9/nomacs_pDyKZBI9cc.jpg" alt="Python">
</p>

## ⚡ Quick Start

```bash
pip install PySide6
python main.py
```




# 📖 Documentation (English)

## Features

- **Adaptive tile grid** — variable-size tiles (1×1 to 4×2) packed without gaps
- **Drag-and-drop** — swap tiles by dragging, live preview animation
- **SteamGridDB integration** — automatic game cover downloads with gallery picker
- **Folder import** — scan folders for `.exe` / `.lnk`, auto-extract icons
- **Global hotkey** — show/hide with any key combo (Win32 `RegisterHotKey`)
- **System tray** — app stays alive in tray when window is hidden
- **Fade animation** — smooth window show/hide transitions
- **Lock mode** — prevent accidental tile reordering
- **Full localization** — JSON-based, add your own language in seconds
- **Frameless window** — dark acrylic-style design, auto-fit to grid

## Tile Management

| Action | How |
|---|---|
| Add tile | **＋** button → pick app, size, color |
| Import from folder | **📂** button → select folder |
| Launch app | Click on tile |
| Move tile | Drag & drop (swap with target) |
| Resize | Right-click → Resize |
| Rename | Right-click → Rename |
| Change icon | Right-click → Change icon |
| Find cover | Right-click → Find cover (SteamGridDB) |
| Change color | Right-click → Change color |
| Bind app / URL | Right-click → Bind application / URL |
| Delete | Right-click → Delete |
| Lock layout | **🔓** button |

## Drag-and-Drop Behavior

| Scenario | Result |
|---|---|
| Drop onto another tile | Tiles swap positions, grid repacks without overlaps |
| Drop onto empty space | Tile moves there, others stay in place |
| Drop outside valid area | Tile returns to original position |
| Locked mode | Drag is blocked, click still launches app |

## Settings

| Parameter | Description |
|---|---|
| Columns | Grid columns (3–12) |
| Cell size | Cell size in pixels (60–160) |
| Gap | Spacing between tiles (2–20 px) |
| SteamGridDB API key | For automatic cover downloads ([get key](https://www.steamgriddb.com/profile/preferences/api)) |
| Hotkey | Show/hide window (click field, press keys) |
| Position | Where window appears: center, bottom, corners, etc. |
| Language | UI language from `lang/` folder |
| Reset | Removes all tiles, keeps settings |

## Folder Import

The scanner:
- Scans selected folder + up to 2 subfolder levels
- Skips system files (uninstall, vcredist, setup, crashreporter, etc.)
- Adds only the main executable from each subfolder
- Skips duplicates by path and normalized name
- Downloads covers from SteamGridDB if API key is set

## Tile Sizes

`1×1` · `2×1` · `1×2` · `2×2` · `2×3` · `3×2` · `4×2`

## Adding a Language

1. Copy `lang/en.json` → `lang/xx.json`
2. Translate values (keep keys unchanged):

```json
{
  "_name": "Deutsch",
  "show_hide": "Anzeigen/Ausblenden",
  "quit": "Beenden",
  "add": "Hinzufügen"
}
```

3. `_name` — display name in settings
4. Restart app → new language appears in ⚙ → Language
5. Missing keys fall back to English

## Architecture

```
tile_launcher/
├── main.py                    # Entry point
├── config.json                # Auto-generated config
├── lang/                      # Translation JSON files
│   ├── ru.json
│   └── en.json
├── icons/                     # Cached icons from .exe files
├── grids/                     # SteamGridDB cover cache
├── core/
│   ├── config_manager.py      # Data models + JSON persistence
│   ├── grid_packer.py         # 2D bin-packing algorithm
│   ├── icon_extractor.py      # Icon extraction (.exe/.lnk/.ico)
│   ├── folder_scanner.py      # Recursive folder scanner with filters
│   ├── steamgriddb.py         # SteamGridDB API v2 client
│   ├── global_hotkey.py       # Win32 global hotkey via native event filter
│   └── i18n.py                # JSON-based localization loader
├── widgets/
│   ├── tile_widget.py         # Individual tile (glow, drag, context menu)
│   ├── grid_manager.py        # Grid container (layout, DnD, CRUD)
│   ├── toast_widget.py        # Toast notifications
│   └── hotkey_edit.py         # Hotkey capture widget
└── windows/
    ├── main_window.py         # Main frameless window (tray, fade, hotkey)
    ├── settings_window.py     # Settings dialog
    ├── add_tile_dialog.py     # Add tile dialog
    └── grid_picker.py         # SteamGridDB cover gallery
```

### Key Algorithms

**2D Bin-Packing** (`grid_packer.py`):
Tiles are placed sequentially (in insertion order) into the first available position using top-left gravity. No sorting by area — new tiles always appear at the end.

**Global Hotkey** (`global_hotkey.py`):
Uses Win32 `RegisterHotKey()` + `QAbstractNativeEventFilter` to intercept `WM_HOTKEY` inside Qt's event loop. Works even when the window is hidden because `QSystemTrayIcon` keeps the application alive.

**Drag-and-Drop** (`grid_manager.py`):
Tile widget detects drag start (8px threshold), emits signal. GridManager captures mouse, moves widget freely, calculates grid snap position. On release: swap indices if dropped on tile, or direct move if dropped on empty space. `pack_tiles()` repacks after swap to prevent overlaps.

---

## 📝 License

MIT

---

---

# 📖 Документация (Русский)

## Возможности

- **Адаптивная сетка плиток** — размеры от 1×1 до 4×2, упаковка без пустот
- **Drag-and-drop** — обмен плиток местами перетаскиванием, live preview
- **Интеграция SteamGridDB** — автоматическая загрузка обложек игр с галереей выбора
- **Импорт из папки** — сканирование папок на `.exe` / `.lnk`, автоизвлечение иконок
- **Глобальный хоткей** — показ/скрытие любой клавишей (Win32 `RegisterHotKey`)
- **Системный трей** — приложение живёт в трее когда окно скрыто
- **Плавная анимация** — fade при показе/скрытии окна
- **Режим блокировки** — запрет перестановки плиток
- **Полная локализация** — JSON-файлы, добавьте свой язык за минуту
- **Frameless-окно** — тёмный acrylic-дизайн, авто-подгонка под сетку

## Управление плитками

| Действие | Как |
|---|---|
| Добавить плитку | Кнопка **＋** → выбрать приложение, размер, цвет |
| Импорт из папки | Кнопка **📂** → выбрать папку |
| Запустить | Клик по плитке |
| Переместить | Зажать и перетащить (обмен с целевой) |
| Изменить размер | ПКМ → Изменить размер |
| Переименовать | ПКМ → Переименовать |
| Изменить иконку | ПКМ → Изменить иконку |
| Найти обложку | ПКМ → Найти обложку (SteamGridDB) |
| Изменить цвет | ПКМ → Изменить цвет |
| Привязать приложение/URL | ПКМ → Привязать приложение / URL |
| Удалить | ПКМ → Удалить |
| Заблокировать | Кнопка **🔓** |

## Поведение Drag-and-Drop

| Сценарий | Результат |
|---|---|
| Бросить на другую плитку | Плитки меняются местами, сетка переупаковывается без наложений |
| Бросить в пустое место | Плитка перемещается туда, остальные не двигаются |
| Бросить за пределы сетки | Плитка возвращается на место |
| Режим блокировки | Перетаскивание заблокировано, клик по-прежнему запускает приложение |

## Настройки (⚙)

| Параметр | Описание |
|---|---|
| Колонки | Количество колонок сетки (3–12) |
| Ячейка | Размер одной ячейки в пикселях (60–160) |
| Отступ | Расстояние между плитками (2–20 px) |
| SteamGridDB API ключ | Для загрузки обложек ([получить ключ](https://www.steamgriddb.com/profile/preferences/api)) |
| Горячая клавиша | Показ/скрытие окна (нажмите поле, затем клавиши) |
| Позиция окна | Где появляется окно: центр, снизу, углы и т.д. |
| Язык | Выбор из файлов в папке `lang/` |
| Сбросить | Удаляет все плитки, сохраняет настройки |

## Импорт из папки

Сканер при выборе папки:
- Обходит папку и до 2 уровней подпапок
- Пропускает служебные файлы (uninstall, vcredist, setup, crashreporter и т.д.)
- Из каждой подпапки добавляет только основное приложение
- Не дублирует по пути и нормализованному имени
- Если задан API-ключ — скачивает обложки с SteamGridDB

## Размеры плиток

`1×1` · `2×1` · `1×2` · `2×2` · `2×3` · `3×2` · `4×2`

## Добавление языка

1. Скопируйте `lang/en.json` → `lang/xx.json`
2. Переведите значения (ключи не меняйте!):

```json
{
  "_name": "Deutsch",
  "show_hide": "Anzeigen/Ausblenden",
  "quit": "Beenden",
  "add": "Hinzufügen"
}
```

3. `_name` — название языка в настройках
4. Перезапустите приложение → новый язык появится в ⚙ → Язык
5. Отсутствующие ключи берутся из английского

## Структура проекта

```
tile_launcher/
├── main.py                    # Точка входа
├── config.json                # Конфигурация (создаётся автоматически)
├── lang/                      # JSON-файлы переводов
│   ├── ru.json                # Русский
│   └── en.json                # English
├── icons/                     # Кэш иконок из .exe
├── grids/                     # Обложки SteamGridDB
├── core/
│   ├── config_manager.py      # Модели данных + JSON
│   ├── grid_packer.py         # 2D bin-packing алгоритм
│   ├── icon_extractor.py      # Извлечение иконок (.exe/.lnk/.ico)
│   ├── folder_scanner.py      # Рекурсивный сканер с фильтрами
│   ├── steamgriddb.py         # Клиент SteamGridDB API v2
│   ├── global_hotkey.py       # Глобальный хоткей через Win32
│   └── i18n.py                # Загрузчик переводов из JSON
├── widgets/
│   ├── tile_widget.py         # Плитка (подсветка, drag, контекстное меню)
│   ├── grid_manager.py        # Контейнер сетки (раскладка, DnD, CRUD)
│   ├── toast_widget.py        # Toast-уведомления
│   └── hotkey_edit.py         # Виджет захвата горячей клавиши
└── windows/
    ├── main_window.py         # Главное окно (трей, fade, хоткей)
    ├── settings_window.py     # Окно настроек
    ├── add_tile_dialog.py     # Диалог добавления плитки
    └── grid_picker.py         # Галерея обложек SteamGridDB
```

### Ключевые алгоритмы

**2D Bin-Packing** (`grid_packer.py`):
Плитки размещаются последовательно (в порядке добавления) в первую свободную позицию (top-left gravity). Без сортировки по площади — новые плитки всегда в конце.

**Глобальный хоткей** (`global_hotkey.py`):
Win32 `RegisterHotKey()` + `QAbstractNativeEventFilter` для перехвата `WM_HOTKEY` внутри Qt event loop. Работает даже когда окно скрыто — `QSystemTrayIcon` держит приложение живым.

**Drag-and-Drop** (`grid_manager.py`):
TileWidget определяет начало drag (порог 8px), отправляет сигнал. GridManager захватывает мышь, двигает виджет, вычисляет snap-позицию. При отпускании: swap индексов если на другой плитке, или прямое перемещение если в пустое место. `pack_tiles()` переупаковывает после swap для предотвращения наложений.

---

## 📝 Лицензия

MIT

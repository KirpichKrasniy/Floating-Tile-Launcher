# ============================================================
# Tile Launcher — плиточный лаунчер приложений / tile app launcher
#
# Установка / Install:
#   pip install PySide6
#
# Запуск / Run:
#   python main.py
#
# Компиляция / Build:
#   pip install pyinstaller
#   pyinstaller --noconfirm --onedir --windowed \
#     --name TileLauncher --add-data "lang;lang" \
#     --hidden-import PySide6.QtSvg main.py
# ============================================================

"""
main.py — Entry point / Точка входа.

RU: Инициализирует QApplication, загружает конфиг и локализацию,
    запускает главное окно.
EN: Initializes QApplication, loads config and localization,
    launches the main window.
"""

import sys
import os
import traceback

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


def _app_dir() -> str:
    """
    RU: Возвращает рабочую директорию приложения.
        При обычном запуске — папка, где лежит main.py.
        При запуске из PyInstaller .exe — папка, где лежит .exe.
    EN: Returns the application working directory.
        Normal run — folder containing main.py.
        PyInstaller .exe — folder containing the .exe.
    """
    if getattr(sys, "frozen", False):
        # RU: Запущено из скомпилированного .exe (PyInstaller)
        # EN: Running from compiled .exe (PyInstaller)
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _bundle_dir() -> str:
    """
    RU: Возвращает директорию с встроенными ресурсами (lang/ и т.д.).
        PyInstaller --onefile распаковывает их во временную папку (_MEIPASS).
        PyInstaller --onedir или обычный запуск — та же папка, что и _app_dir().
    EN: Returns the directory with bundled resources (lang/, etc.).
        PyInstaller --onefile extracts them to a temp folder (_MEIPASS).
        PyInstaller --onedir or normal run — same as _app_dir().
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def main():
    # RU: Включаем поддержку High-DPI мониторов
    # EN: Enable High-DPI display support
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # RU: Устанавливаем шрифт по умолчанию
    # EN: Set default application font
    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(font)

    # RU: config.json, icons/, grids/ — в рабочей директории (рядом с .exe)
    # EN: config.json, icons/, grids/ — in working directory (next to .exe)
    app_dir = _app_dir()
    config_path = os.path.join(app_dir, "config.json")

    from core.config_manager import ConfigManager
    config_manager = ConfigManager(config_path)

    # RU: lang/ — в директории ресурсов (может быть во временной папке PyInstaller)
    # EN: lang/ — in bundle directory (may be in PyInstaller temp folder)
    bundle_dir = _bundle_dir()
    lang_dir = os.path.join(bundle_dir, "lang")

    from core.i18n import init as i18n_init, set_language
    i18n_init(lang_dir)
    set_language(config_manager.config.language)

    # RU: Создаём и показываем главное окно
    # EN: Create and show the main window
    from windows.main_window import MainWindow
    window = MainWindow(config_manager)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        input("Press Enter to exit / Нажмите Enter для выхода...")

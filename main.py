# ============================================================
# Tile Launcher — плиточный лаунчер приложений / tile app launcher
#
# Установка / Install:
#   pip install PySide6
#
# Запуск / Run:
#   python main.py
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

    # RU: Путь к config.json — в той же папке, что и main.py
    # EN: Path to config.json — same directory as main.py
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

    from core.config_manager import ConfigManager
    config_manager = ConfigManager(config_path)

    # RU: Загружаем переводы из папки lang/ и ставим язык из конфига
    # EN: Load translations from lang/ folder and set language from config
    from core.i18n import init as i18n_init, set_language
    lang_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lang")
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

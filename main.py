"""
main.py
-------
Punto di ingresso dell'applicazione. Avvia Qt e mostra la finestra
principale.

Esecuzione in sviluppo:
    python main.py

Per generare l'eseguibile .exe di Windows, vedi build_exe.bat / README.md.
"""

import sys

from PySide6.QtWidgets import QApplication

from core import database
from gui.main_window import MainWindow
from gui.theme import DARK_PURPLE_THEME
from services import youtube_service


def main() -> None:
    database.init_db()

    # Le anteprime da 30s sono usa-e-getta: si svuota la cache ad ogni
    # avvio, così non si accumulano nel tempo file di ascolti passati.
    youtube_service.clear_preview_cache()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # base pulita su cui applicare il tema personalizzato
    app.setStyleSheet(DARK_PURPLE_THEME)  # tema scuro nero/viola

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

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


def main() -> None:
    database.init_db()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # base pulita su cui applicare il tema personalizzato
    app.setStyleSheet(DARK_PURPLE_THEME)  # tema scuro nero/viola

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

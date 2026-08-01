"""
theme.py
--------
Stylesheet Qt (QSS) per un tema scuro con accenti viola, applicato a
tutta l'applicazione da main.py tramite `app.setStyleSheet(DARK_PURPLE_THEME)`.

Palette:
  - sfondo principale:  #121016 (quasi nero)
  - sfondo pannelli:    #1c1a24
  - bordo/separatori:   #2e2a3a
  - accento viola:      #9d4edd
  - accento viola scuro:#6a2fb0
  - testo principale:   #f1eef7
  - testo secondario:   #b8b0c9
"""

DARK_PURPLE_THEME = """
QWidget {
    background-color: #121016;
    color: #f1eef7;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #121016;
}

/* --- Pulsanti --- */
QPushButton {
    background-color: #2a2333;
    color: #f1eef7;
    border: 1px solid #3d3550;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton:hover {
    background-color: #43305f;
    border: 1px solid #9d4edd;
}
QPushButton:pressed {
    background-color: #6a2fb0;
}
QPushButton:disabled {
    background-color: #201c28;
    color: #6b6478;
    border: 1px solid #2a2533;
}

/* --- Liste (cartelle, brani, consigli) --- */
QListWidget {
    background-color: #1c1a24;
    border: 1px solid #2e2a3a;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}
QListWidget::item {
    padding: 6px 8px;
    border-radius: 4px;
}
QListWidget::item:hover {
    background-color: #2a2333;
}
QListWidget::item:selected {
    background-color: #6a2fb0;
    color: #ffffff;
}

/* --- Albero cartelle (collassabile) --- */
QTreeWidget {
    background-color: #1c1a24;
    border: 1px solid #2e2a3a;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}
QTreeWidget::item {
    padding: 5px 4px;
    border-radius: 4px;
}
QTreeWidget::item:hover {
    background-color: #2a2333;
}
QTreeWidget::item:selected {
    background-color: #6a2fb0;
    color: #ffffff;
}
QTreeView::branch {
    background: transparent;
    border-image: none;
}

/* Freccina chiusa (collassata) - Senza virgolette e con border-image a none */
QTreeView::branch:has-children:closed {
    border-image: none;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNCIgaGVpZ2h0PSIxNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNiOGIwYzkiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSI5IDE4IDE1IDEyIDkgNiIvPjwvc3ZnPg==);
}

/* Freccina aperta (espansa) */
QTreeView::branch:has-children:open {
    border-image: none;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNCIgaGVpZ2h0PSIxNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNiOGIwYzkiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSI2IDkgMTIgMTUgMTggOSIvPjwvc3ZnPg==);
}

/* Effetto hover (viola) */
QTreeView::branch:has-children:closed:hover {
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNCIgaGVpZ2h0PSIxNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM5ZDRlZGQiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSI5IDE4IDE1IDEyIDkgNiIvPjwvc3ZnPg==);
}
QTreeView::branch:has-children:open:hover {
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNCIgaGVpZ2h0PSIxNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM5ZDRlZGQiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSI2IDkgMTIgMTUgMTggOSIvPjwvc3ZnPg==);
}
/* --- Etichette --- */
QLabel {
    color: #d8d2e6;
}

/* --- ComboBox (selettore velocità) --- */
QComboBox {
    background-color: #2a2333;
    border: 1px solid #3d3550;
    border-radius: 6px;
    padding: 4px 8px;
}
QComboBox:hover {
    border: 1px solid #9d4edd;
}
QComboBox QAbstractItemView {
    background-color: #1c1a24;
    border: 1px solid #9d4edd;
    selection-background-color: #6a2fb0;
    outline: none;
}

/* --- Slider (barra di avanzamento e volume) --- */
QSlider::groove:horizontal {
    height: 6px;
    background: #2e2a3a;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #9d4edd;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #d9b6ff;
    border: 1px solid #9d4edd;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #ffffff;
}

/* --- Splitter --- */
QSplitter::handle {
    background-color: #2e2a3a;
    width: 2px;
}

/* --- ScrollBar --- */
QScrollBar:vertical {
    background: #1c1a24;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #43305f;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #9d4edd;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* --- ProgressDialog (scansione libreria) --- */
QProgressBar {
    background-color: #1c1a24;
    border: 1px solid #2e2a3a;
    border-radius: 6px;
    text-align: center;
    color: #f1eef7;
}
QProgressBar::chunk {
    background-color: #9d4edd;
    border-radius: 6px;
}

/* --- MessageBox / Dialog --- */
QDialog {
    background-color: #1c1a24;
}
QSpinBox {
    background-color: #2a2333;
    border: 1px solid #3d3550;
    border-radius: 6px;
    padding: 3px 6px;
}

/* --- Tooltip --- */
QToolTip {
    background-color: #1c1a24;
    color: #f1eef7;
    border: 1px solid #9d4edd;
    padding: 4px;
}


/* --- Menu a tendina (QMenu) --- */
QMenu {
    background-color: #1c1a24;
    color: #f1eef7;
    border: 1px solid #3d3550;
    border-radius: 4px;
    padding: 4px 0px;
}
QMenu::item {
    padding: 6px 24px 6px 12px;
    background-color: transparent;
}
QMenu::item:selected {
    background-color: #6a2fb0;
}
QMenu::item:disabled {
    color: #6b6478;
}
QMenu::separator {
    height: 1px;
    background-color: #2e2a3a;
    margin: 4px 0px;
}

"""

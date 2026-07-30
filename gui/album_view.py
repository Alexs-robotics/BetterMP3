"""
album_view.py
-------------
Vista a due colonne:
  - a sinistra la lista delle CARTELLE musicali trovate nella libreria
    (raggruppamento per cartella fisica, non per tag ID3 "album" — vedi
    nota in core/database.py)
  - a destra i brani della cartella selezionata, ordinati per numero di
    traccia, con possibilità di doppio click per suonare l'intera
    cartella a partire da quel brano, e un pulsante per modificarne il
    numero d'ordine.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core import database
from gui.track_editor_dialog import TrackEditorDialog

FOLDER_PATH_ROLE = Qt.UserRole + 1


class AlbumView(QWidget):
    # Emesso quando l'utente vuole riprodurre una cartella a partire da un indice.
    play_album_requested = Signal(list, int)  # (lista path, indice iniziale)
    # Emesso quando l'utente seleziona un brano (per mostrare i consigli).
    track_selected = Signal(str, str)  # (titolo, artista)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._folders: dict = {}  # {percorso_cartella_completo: [righe]}
        self._current_folder_tracks: list = []

        self.album_list = QListWidget()
        self.album_list.currentItemChanged.connect(self._on_folder_selected)

        self.track_list = QListWidget()
        self.track_list.itemDoubleClicked.connect(self._on_track_double_clicked)
        self.track_list.currentRowChanged.connect(self._on_track_row_changed)

        self.edit_track_number_button = QPushButton("Modifica numero traccia")
        self.edit_track_number_button.clicked.connect(self._on_edit_track_number)

        left_column = QVBoxLayout()
        left_column.addWidget(QLabel("Cartelle musicali"))
        left_column.addWidget(self.album_list)

        right_column = QVBoxLayout()
        right_column.addWidget(QLabel("Brani (doppio click per suonare da qui)"))
        right_column.addWidget(self.track_list)
        right_column.addWidget(self.edit_track_number_button)

        main_layout = QHBoxLayout(self)
        main_layout.addLayout(left_column, 1)
        main_layout.addLayout(right_column, 2)

    def set_albums(self, albums_grouped: dict) -> None:
        """`albums_grouped`: dict {percorso_cartella: [righe sqlite3.Row]}."""
        self._folders = albums_grouped
        self.album_list.clear()
        for folder_path in sorted(albums_grouped.keys(), key=database.folder_display_name):
            item = QListWidgetItem(database.folder_display_name(folder_path))
            item.setData(FOLDER_PATH_ROLE, folder_path)
            item.setToolTip(folder_path)
            self.album_list.addItem(item)

    def _on_folder_selected(self, current: QListWidgetItem, _previous: QListWidgetItem) -> None:
        if current is None:
            self.track_list.clear()
            self._current_folder_tracks = []
            return
        folder_path = current.data(FOLDER_PATH_ROLE)
        self._current_folder_tracks = self._folders.get(folder_path, [])
        self.track_list.clear()
        for row in self._current_folder_tracks:
            label = f"{row['track_number']:02d}. {row['title']} — {row['artist']}"
            self.track_list.addItem(QListWidgetItem(label))

    def _on_track_double_clicked(self, _item: QListWidgetItem) -> None:
        index = self.track_list.currentRow()
        if index < 0:
            return
        paths = [row["path"] for row in self._current_folder_tracks]
        self.play_album_requested.emit(paths, index)

    def _on_track_row_changed(self, index: int) -> None:
        if 0 <= index < len(self._current_folder_tracks):
            row = self._current_folder_tracks[index]
            self.track_selected.emit(row["title"], row["artist"])

    def _on_edit_track_number(self) -> None:
        index = self.track_list.currentRow()
        if index < 0 or index >= len(self._current_folder_tracks):
            return
        row = self._current_folder_tracks[index]
        dialog = TrackEditorDialog(current_number=row["track_number"], parent=self)
        if dialog.exec():
            new_number = dialog.selected_number()
            from core import metadata
            metadata.set_track_number(row["path"], new_number)
            database.update_track_number(row["path"], new_number)
            # Aggiorna la vista corrente senza dover ri-scansionare tutta la libreria.
            current_item = self.album_list.currentItem()
            folder_path = current_item.data(FOLDER_PATH_ROLE)
            self._folders = database.albums_grouped()
            self._current_folder_tracks = self._folders.get(folder_path, [])
            self.track_list.clear()
            for r in self._current_folder_tracks:
                label = f"{r['track_number']:02d}. {r['title']} — {r['artist']}"
                self.track_list.addItem(QListWidgetItem(label))

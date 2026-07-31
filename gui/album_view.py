"""
album_view.py
-------------
Vista a due colonne:
  - a sinistra un ALBERO di cartelle (QTreeWidget) che rispecchia la
    struttura reale delle sottocartelle dentro la cartella musicale
    (es. "Jesto" -> "Jesto - SAMSARA" -> ...), collassabile a ogni
    livello. Solo le cartelle "foglia" che contengono davvero dei file
    audio sono selezionabili per la riproduzione; le cartelle
    intermedie servono solo a organizzare l'albero.
  - a destra i brani della cartella foglia selezionata, ordinati per
    numero di traccia, con possibilità di doppio click per suonare
    l'intera cartella a partire da quel brano, e un pulsante per
    modificarne il numero d'ordine.
"""

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
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

        self.album_tree = QTreeWidget()
        self.album_tree.setHeaderHidden(True)
        self.album_tree.currentItemChanged.connect(self._on_folder_selected)

        self.track_list = QListWidget()
        self.track_list.itemDoubleClicked.connect(self._on_track_double_clicked)
        self.track_list.currentRowChanged.connect(self._on_track_row_changed)

        self.edit_track_number_button = QPushButton("Edit track number")
        self.edit_track_number_button.clicked.connect(self._on_edit_track_number)

        left_column = QVBoxLayout()
        left_column.addWidget(QLabel("Music folders"))
        left_column.addWidget(self.album_tree)

        right_column = QVBoxLayout()
        right_column.addWidget(QLabel("Tracks (double-click to play from here)"))
        right_column.addWidget(self.track_list)
        right_column.addWidget(self.edit_track_number_button)

        main_layout = QHBoxLayout(self)
        main_layout.addLayout(left_column, 1)
        main_layout.addLayout(right_column, 2)

    def set_albums(self, root_folder: str, albums_grouped: dict) -> None:
        """
        `root_folder`: la cartella musicale scansionata (serve per calcolare
        i percorsi relativi e costruire l'albero).
        `albums_grouped`: dict {percorso_cartella_completo: [righe sqlite3.Row]},
        una voce per ogni cartella FOGLIA che contiene almeno un brano.
        """
        self._folders = albums_grouped
        self.album_tree.clear()

        # Cache dei nodi già creati, chiave = tupla dei componenti del
        # percorso relativo (es. ("Jesto", "Jesto - SAMSARA")), così le
        # cartelle intermedie condivise da più album vengono create una
        # sola volta e riusate.
        node_cache: dict = {}

        for folder_path in sorted(albums_grouped.keys(), key=lambda p: os.path.relpath(p, root_folder)):
            rel_path = os.path.relpath(folder_path, root_folder)
            components = [] if rel_path == "." else rel_path.split(os.sep)
            if not components:
                # Brano direttamente nella cartella radice: usa il nome
                # della cartella radice come unico nodo.
                components = [database.folder_display_name(folder_path)]

            parent_item = None
            path_key = ()
            leaf_item = None
            for component in components:
                path_key = path_key + (component,)
                item = node_cache.get(path_key)
                if item is None:
                    item = QTreeWidgetItem([component])
                    node_cache[path_key] = item
                    if parent_item is None:
                        self.album_tree.addTopLevelItem(item)
                    else:
                        parent_item.addChild(item)
                parent_item = item
                leaf_item = item

            # L'ultimo nodo del percorso è la cartella foglia reale: le
            # attacchiamo il percorso completo, così diventa selezionabile
            # per la riproduzione. I nodi intermedi restano senza questo
            # dato e servono solo a organizzare/collassare l'albero.
            leaf_item.setData(0, FOLDER_PATH_ROLE, folder_path)
            leaf_item.setToolTip(0, folder_path)

        self.album_tree.expandToDepth(0)

    def _on_folder_selected(self, current: "QTreeWidgetItem", _previous: "QTreeWidgetItem") -> None:
        if current is None:
            self.track_list.clear()
            self._current_folder_tracks = []
            return

        folder_path = current.data(0, FOLDER_PATH_ROLE)
        if not folder_path:
            # Nodo intermedio (es. "Jesto"): non contiene brani propri,
            # serve solo a organizzare l'albero. Svuota la lista brani.
            self.track_list.clear()
            self._current_folder_tracks = []
            return

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
            current_item = self.album_tree.currentItem()
            folder_path = current_item.data(0, FOLDER_PATH_ROLE)
            self._folders = database.albums_grouped()
            self._current_folder_tracks = self._folders.get(folder_path, [])
            self.track_list.clear()
            for r in self._current_folder_tracks:
                label = f"{r['track_number']:02d}. {r['title']} — {r['artist']}"
                self.track_list.addItem(QListWidgetItem(label))

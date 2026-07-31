"""
main_window.py
----------------
Main window. Ties together:
  - library scanning (Windows Music folder)
  - the album/track view (album_view.py)
  - playback controls (player_controls.py)
  - the recommendations panel (recommendations_panel.py)
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core import database, library
from core.config import WINDOWS_MUSIC_FOLDER
from core.player import PlaybackEngine
from gui.album_view import AlbumView
from gui.player_controls import PlayerControls
from gui.recommendations_panel import RecommendationsPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MP3 Player")
        self.resize(1200, 720)

        self.engine = PlaybackEngine()
        self._current_playlist: list[str] = []

        self.album_view = AlbumView()
        self.player_controls = PlayerControls(self.engine)
        self.recommendations_panel = RecommendationsPanel(
            preview_engine=PlaybackEngine(), main_engine=self.engine
        )

        self.rescan_button = QPushButton("Rescan Music folder")
        self.rescan_button.clicked.connect(self._rescan_library)

        self.force_rescan_button = QPushButton("Full re-read (ignore cache)")
        self.force_rescan_button.setToolTip(
            "Re-reads the tags of ALL files from scratch, even unmodified ones.\n"
            "Use this if you updated the app and some titles/track numbers still look wrong."
        )
        self.force_rescan_button.clicked.connect(self._force_full_rescan)

        self.choose_folder_button = QPushButton("Choose a different music folder...")
        self.choose_folder_button.clicked.connect(self._choose_folder)

        # -- Signal connections --
        self.album_view.play_album_requested.connect(self._play_album)
        self.album_view.track_selected.connect(self.recommendations_panel.refresh_for_track)
        self.player_controls.play_pause_clicked.connect(self._toggle_play_pause)
        self.player_controls.next_clicked.connect(self.engine.next)
        self.player_controls.previous_clicked.connect(self.engine.previous)
        self.engine.track_changed.connect(self._on_track_changed)

        # -- Layout --
        central = QWidget()
        main_layout = QVBoxLayout(central)

        top_buttons = QVBoxLayout()
        top_buttons.addWidget(self.rescan_button)
        top_buttons.addWidget(self.force_rescan_button)
        top_buttons.addWidget(self.choose_folder_button)
        main_layout.addLayout(top_buttons)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.album_view)
        splitter.addWidget(self.recommendations_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter, stretch=1)

        main_layout.addWidget(self.player_controls)

        self.setCentralWidget(central)

        self._music_folder = WINDOWS_MUSIC_FOLDER
        self._rescan_library()

    # -- Library -------------------------------------------------
    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose the music folder", self._music_folder)
        if folder:
            self._music_folder = folder
            self._rescan_library()

    def _force_full_rescan(self) -> None:
        """Clears the cache and re-reads the tags of all files from scratch,
        even unmodified ones (useful after updating the app)."""
        database.clear_all_tracks()
        self._rescan_library()

    def _rescan_library(self) -> None:
        if not os.path.isdir(self._music_folder):
            QMessageBox.information(
                self, "Folder not found",
                f"The folder '{self._music_folder}' does not exist. Please choose another one."
            )
            return

        progress = QProgressDialog("Scanning music library...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        def on_progress(done: int, total: int) -> None:
            if total > 0:
                progress.setMaximum(total)
                progress.setValue(done)

        library.scan_library(self._music_folder, progress_callback=on_progress)
        progress.close()

        albums = database.albums_grouped()
        self.album_view.set_albums(self._music_folder, albums)

    # -- Playback -------------------------------------------------
    def _play_album(self, paths: list[str], start_index: int) -> None:
        self._current_playlist = paths
        self.engine.load_playlist(paths, start_index)
        self.player_controls.set_now_playing_text(os.path.basename(paths[start_index]))

    def _toggle_play_pause(self) -> None:
        if self.engine.is_playing():
            self.engine.pause()
        else:
            if self._current_playlist:
                self.engine.pause()  # resumes if it was paused
            else:
                self.engine.play()

    def _on_track_changed(self, index: int) -> None:
        if 0 <= index < len(self._current_playlist):
            name = os.path.splitext(os.path.basename(self._current_playlist[index]))[0]
            self.player_controls.set_now_playing_text(name)

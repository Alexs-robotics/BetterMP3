"""
search_panel.py
----------------
Nuova pagina "Search & Download": a differenza del pannello dei
consigli (che parte sempre da un brano già in libreria), qui l'utente
può cercare liberamente qualsiasi brano o album per nome e:

  1. cercare BRANI (ricerca diretta su YouTube) oppure ALBUM (ricerca
     su Last.fm, che fornisce la tracklist ufficiale) tramite un
     selettore di modalità;
  2. ascoltare un'ANTEPRIMA di ~30 secondi di qualunque risultato,
     senza scaricare nulla in libreria;
  3. scaricare il singolo brano oppure l'intero album (tutti i brani
     della tracklist, uno dopo l'altro) dentro la cartella musicale
     scansionata dall'app, cosicché compaiano in libreria alla
     prossima scansione.

È una finestra separata (non modale) così l'utente può continuare ad
ascoltare la libreria mentre cerca/scarica. Eredita automaticamente il
tema scuro viola perché lo stylesheet è applicato a livello di
QApplication in main.py.
"""

import os

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core import metadata
from core.config import WINDOWS_MUSIC_FOLDER
from core.net_errors import is_no_internet_error
from core.player import PlaybackEngine
from services import lastfm_service, youtube_service

MODE_SONGS = "Songs"
MODE_ALBUMS = "Albums"


# ---------------------------------------------------------------------
# Thread di ricerca
# ---------------------------------------------------------------------

class _SearchSongsThread(QThread):
    finished_ok = Signal(list)  # List[YoutubeSearchResult]
    finished_error = Signal(str)

    def __init__(self, query: str) -> None:
        super().__init__()
        self.query = query

    def run(self) -> None:
        try:
            results = youtube_service.search_tracks(self.query, limit=15)
            self.finished_ok.emit(results)
        except Exception as exc:
            self.finished_error.emit("No Internet" if is_no_internet_error(exc) else str(exc))


class _SearchAlbumsThread(QThread):
    finished_ok = Signal(list)  # List[AlbumResult]
    finished_error = Signal(str)

    def __init__(self, query: str) -> None:
        super().__init__()
        self.query = query

    def run(self) -> None:
        try:
            results = lastfm_service.search_albums(self.query, limit=15)
            self.finished_ok.emit(results)
        except Exception as exc:
            self.finished_error.emit("No Internet" if is_no_internet_error(exc) else str(exc))


class _FetchAlbumTracksThread(QThread):
    finished_ok = Signal(str, str, list)  # (artist, album, List[AlbumTrackInfo])
    finished_error = Signal(str)

    def __init__(self, artist: str, album: str) -> None:
        super().__init__()
        self.artist = artist
        self.album = album

    def run(self) -> None:
        try:
            tracks = lastfm_service.get_album_tracks(self.artist, self.album)
            self.finished_ok.emit(self.artist, self.album, tracks)
        except Exception as exc:
            self.finished_error.emit("No Internet" if is_no_internet_error(exc) else str(exc))


# ---------------------------------------------------------------------
# Thread di anteprima (nessun file finisce in libreria)
# ---------------------------------------------------------------------

class _PreviewThread(QThread):
    finished_ok = Signal(str)  # preview_path
    finished_error = Signal(str)

    def __init__(self, title: str, artist: str) -> None:
        super().__init__()
        self.title = title
        self.artist = artist

    def run(self) -> None:
        try:
            result = youtube_service.search_track(f"{self.artist} {self.title} audio")
            if result is None:
                self.finished_error.emit("No results found on YouTube.")
                return
            safe_name = f"preview_{result.video_id}"
            preview_path = youtube_service.download_preview(result.url, safe_name)
            self.finished_ok.emit(preview_path)
        except Exception as exc:
            self.finished_error.emit("No Internet" if is_no_internet_error(exc) else str(exc))


# ---------------------------------------------------------------------
# Thread di download
# ---------------------------------------------------------------------

class _DownloadSongThread(QThread):
    finished_ok = Signal(str)  # downloaded file path
    finished_error = Signal(str)

    def __init__(self, video_url: str, artist: str, title: str) -> None:
        super().__init__()
        self.video_url = video_url
        self.artist = artist
        self.title = title

    def run(self) -> None:
        try:
            path = youtube_service.download_full_track(
                self.video_url, self.artist, self.title, None, WINDOWS_MUSIC_FOLDER
            )
            metadata.write_full_tags(path, self.title, self.artist, "Singles", 1)
            self.finished_ok.emit(path)
        except Exception as exc:
            self.finished_error.emit("No Internet" if is_no_internet_error(exc) else str(exc))


class _DownloadAlbumThread(QThread):
    progress = Signal(int, int)  # (fatti, totale)
    finished_ok = Signal(str, int, int)  # (cartella album, scaricati, totale)
    finished_error = Signal(str)

    def __init__(self, artist: str, album: str, tracks: list) -> None:
        super().__init__()
        self.artist = artist
        self.album = album
        self.tracks = tracks

    def run(self) -> None:
        try:
            album_folder = ""
            downloaded = 0
            total = len(self.tracks)
            for i, track in enumerate(self.tracks, start=1):
                result = youtube_service.search_track(f"{self.artist} {track.title} audio")
                if result is not None:
                    path = youtube_service.download_full_track(
                        result.url, self.artist, track.title, self.album, WINDOWS_MUSIC_FOLDER
                    )
                    metadata.write_full_tags(path, track.title, self.artist, self.album, track.track_number)
                    album_folder = os.path.dirname(path)
                    downloaded += 1
                self.progress.emit(i, total)
            self.finished_ok.emit(album_folder, downloaded, total)
        except Exception as exc:
            self.finished_error.emit("No Internet" if is_no_internet_error(exc) else str(exc))


# ---------------------------------------------------------------------
# Finestra "Search & Download"
# ---------------------------------------------------------------------

class SearchWindow(QDialog):
    # Emesso dopo ogni download andato a buon fine, così main_window può
    # riscansionare la libreria e far comparire subito il nuovo brano/album.
    library_changed = Signal()

    def __init__(self, main_engine: PlaybackEngine, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Search & Download")
        self.setWindowFlag(Qt.Window)  # finestra indipendente, non modale
        self.resize(560, 640)

        # Motore di anteprima separato da quello della libreria, per lo
        # stesso motivo del pannello dei consigli: si mette in pausa la
        # libreria principale mentre parte una preview, non si sovrappongono.
        self.preview_engine = PlaybackEngine()
        self.main_engine = main_engine

        self._selected_song = None  # (video_url, title, artist)
        self._selected_album = None  # (artist, album_title)
        self._album_tracks: list = []
        self._active_threads: list[QThread] = []

        # -- Barra di ricerca --------------------------------------------------
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([MODE_SONGS, MODE_ALBUMS])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for a song or an album...")
        self.search_input.returnPressed.connect(self._on_search_clicked)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self._on_search_clicked)

        search_row = QHBoxLayout()
        search_row.addWidget(self.mode_combo)
        search_row.addWidget(self.search_input, stretch=1)
        search_row.addWidget(self.search_button)

        # -- Risultati -----------------------------------------------------
        self.results_list = QListWidget()
        self.results_list.currentItemChanged.connect(self._on_result_selected)

        # -- Tracklist album (visibile solo in modalità Albums, dopo aver
        # selezionato un album) --------------------------------------------
        self.album_tracks_label = QLabel("Tracklist:")
        self.album_tracks_list = QListWidget()
        self.album_tracks_list.currentItemChanged.connect(self._on_album_track_selected)

        # -- Controlli anteprima/download ------------------------------------
        self.preview_button = QPushButton("▶ Play preview (30s)")
        self.preview_button.setEnabled(False)
        self.preview_button.clicked.connect(self._on_preview_clicked)

        self.stop_preview_button = QPushButton("⏹ Stop preview")
        self.stop_preview_button.setEnabled(False)
        self.stop_preview_button.clicked.connect(self._on_stop_preview_clicked)

        self.download_song_button = QPushButton("⬇ Download this song")
        self.download_song_button.setEnabled(False)
        self.download_song_button.clicked.connect(self._on_download_song_clicked)

        self.download_album_button = QPushButton("⬇ Download entire album")
        self.download_album_button.setEnabled(False)
        self.download_album_button.clicked.connect(self._on_download_album_clicked)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        preview_row = QHBoxLayout()
        preview_row.addWidget(self.preview_button)
        preview_row.addWidget(self.stop_preview_button)

        # -- Layout ---------------------------------------------------------
        layout = QVBoxLayout(self)
        layout.addLayout(search_row)
        layout.addWidget(QLabel("Results:"))
        layout.addWidget(self.results_list, stretch=2)
        layout.addWidget(self.album_tracks_label)
        layout.addWidget(self.album_tracks_list, stretch=2)
        layout.addLayout(preview_row)
        layout.addWidget(self.download_song_button)
        layout.addWidget(self.download_album_button)
        layout.addWidget(self.status_label)

        self._on_mode_changed(self.mode_combo.currentText())

    # -- Gestione thread (li teniamo "vivi" finché non finiscono, altrimenti
    # il garbage collector di Python può distruggerli mentre girano ancora
    # e PySide6 va in crash) -------------------------------------------------
    def _launch_thread(self, thread: QThread) -> None:
        self._active_threads.append(thread)
        thread.finished.connect(lambda: self._cleanup_thread(thread))
        thread.start()

    def _cleanup_thread(self, thread: QThread) -> None:
        if thread in self._active_threads:
            self._active_threads.remove(thread)
        thread.deleteLater()

    # -- Cambio modalità (Songs / Albums) -------------------------------------
    def _on_mode_changed(self, mode: str) -> None:
        self.results_list.clear()
        self.album_tracks_list.clear()
        self._selected_song = None
        self._selected_album = None
        self._album_tracks = []

        is_albums = mode == MODE_ALBUMS
        self.album_tracks_label.setVisible(is_albums)
        self.album_tracks_list.setVisible(is_albums)
        self.download_album_button.setVisible(is_albums)
        self.download_song_button.setVisible(not is_albums)

        self.preview_button.setEnabled(False)
        self.download_song_button.setEnabled(False)
        self.download_album_button.setEnabled(False)
        self.status_label.setText("")

    # -- Ricerca ------------------------------------------------------------
    def _on_search_clicked(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            return

        self.results_list.clear()
        self.album_tracks_list.clear()
        self._selected_song = None
        self._selected_album = None
        self.preview_button.setEnabled(False)
        self.download_song_button.setEnabled(False)
        self.download_album_button.setEnabled(False)
        self.search_button.setEnabled(False)
        self.status_label.setText("Searching...")

        if self.mode_combo.currentText() == MODE_SONGS:
            thread = _SearchSongsThread(query)
            thread.finished_ok.connect(self._on_songs_found)
            thread.finished_error.connect(self._on_error)
        else:
            thread = _SearchAlbumsThread(query)
            thread.finished_ok.connect(self._on_albums_found)
            thread.finished_error.connect(self._on_error)

        self._launch_thread(thread)

    def _on_songs_found(self, results) -> None:
        self.search_button.setEnabled(True)
        if not results:
            self.status_label.setText("No songs found.")
            return
        self.status_label.setText(f"{len(results)} songs found.")
        for r in results:
            item = QListWidgetItem(f"{r.title} — {r.channel}")
            item.setData(1000, (r.url, r.title, r.channel))
            self.results_list.addItem(item)

    def _on_albums_found(self, results) -> None:
        self.search_button.setEnabled(True)
        if not results:
            self.status_label.setText("No albums found.")
            return
        self.status_label.setText(f"{len(results)} albums found.")
        for a in results:
            item = QListWidgetItem(f"{a.title} — {a.artist}")
            item.setData(1000, (a.artist, a.title))
            self.results_list.addItem(item)

    def _on_result_selected(self, current: QListWidgetItem, _previous: QListWidgetItem) -> None:
        if current is None:
            return
        self._stop_preview_playback()

        if self.mode_combo.currentText() == MODE_SONGS:
            video_url, title, channel = current.data(1000)
            self._selected_song = (video_url, title, channel)
            self.preview_button.setEnabled(True)
            self.download_song_button.setEnabled(True)
            self.status_label.setText("Ready for preview.")
        else:
            artist, album_title = current.data(1000)
            self._selected_album = (artist, album_title)
            self.album_tracks_list.clear()
            self.download_album_button.setEnabled(False)
            self.preview_button.setEnabled(False)
            self.status_label.setText("Loading tracklist...")

            thread = _FetchAlbumTracksThread(artist, album_title)
            thread.finished_ok.connect(self._on_album_tracks_ready)
            thread.finished_error.connect(self._on_error)
            self._launch_thread(thread)

    def _on_album_tracks_ready(self, artist: str, album: str, tracks: list) -> None:
        # Se nel frattempo l'utente ha selezionato un altro album, questi
        # risultati sono superati: li scartiamo.
        if self._selected_album != (artist, album):
            return
        self._album_tracks = tracks
        self.album_tracks_list.clear()
        for t in tracks:
            self.album_tracks_list.addItem(QListWidgetItem(f"{t.track_number:02d}. {t.title}"))
        if tracks:
            self.status_label.setText(f"{len(tracks)} tracks in this album.")
            self.download_album_button.setEnabled(True)
        else:
            self.status_label.setText("No tracklist available for this album.")

    def _on_album_track_selected(self, current: QListWidgetItem, _previous: QListWidgetItem) -> None:
        if current is None or self._selected_album is None:
            return
        self._stop_preview_playback()
        self.preview_button.setEnabled(True)
        self.status_label.setText("Ready for preview.")

    # -- Anteprima ------------------------------------------------------------
    def _current_preview_target(self):
        """Ritorna (title, artist) del brano attualmente selezionato,
        sia in modalità Songs (risultato diretto) sia in modalità Albums
        (brano scelto dentro la tracklist)."""
        if self.mode_combo.currentText() == MODE_SONGS:
            if self._selected_song is None:
                return None
            _url, title, channel = self._selected_song
            return title, channel
        else:
            index = self.album_tracks_list.currentRow()
            if self._selected_album is None or not (0 <= index < len(self._album_tracks)):
                return None
            track = self._album_tracks[index]
            return track.title, track.artist

    def _on_preview_clicked(self) -> None:
        target = self._current_preview_target()
        if target is None:
            return
        title, artist = target

        self._stop_preview_playback()
        if self.main_engine is not None and self.main_engine.is_playing():
            self.main_engine.pause()

        self.status_label.setText("Downloading preview...")
        self.preview_button.setEnabled(False)

        thread = _PreviewThread(title, artist)
        thread.finished_ok.connect(self._on_preview_ready)
        thread.finished_error.connect(self._on_error)
        self._launch_thread(thread)

    def _on_preview_ready(self, preview_path: str) -> None:
        self.preview_engine.load_playlist([preview_path], start_index=0)
        self.status_label.setText("Preview playing.")
        self.preview_button.setEnabled(True)
        self.stop_preview_button.setEnabled(True)

    def _on_stop_preview_clicked(self) -> None:
        self._stop_preview_playback()
        self.status_label.setText("Preview stopped.")

    def _stop_preview_playback(self) -> None:
        self.preview_engine.stop()
        self.stop_preview_button.setEnabled(False)

    # -- Download singolo brano -------------------------------------------
    def _on_download_song_clicked(self) -> None:
        if self._selected_song is None:
            return
        video_url, title, channel = self._selected_song
        self.status_label.setText("Downloading song...")
        self.download_song_button.setEnabled(False)

        thread = _DownloadSongThread(video_url, channel, title)
        thread.finished_ok.connect(self._on_song_downloaded)
        thread.finished_error.connect(self._on_error)
        self._launch_thread(thread)

    def _on_song_downloaded(self, path: str) -> None:
        self.status_label.setText(f"Downloaded: {os.path.basename(path)}")
        self.download_song_button.setEnabled(True)
        self.library_changed.emit()

    # -- Download intero album ---------------------------------------------
    def _on_download_album_clicked(self) -> None:
        if self._selected_album is None or not self._album_tracks:
            return
        artist, album_title = self._selected_album
        self.status_label.setText(f"Downloading album (0/{len(self._album_tracks)})...")
        self.download_album_button.setEnabled(False)

        thread = _DownloadAlbumThread(artist, album_title, self._album_tracks)
        thread.progress.connect(self._on_album_download_progress)
        thread.finished_ok.connect(self._on_album_downloaded)
        thread.finished_error.connect(self._on_error)
        self._launch_thread(thread)

    def _on_album_download_progress(self, done: int, total: int) -> None:
        self.status_label.setText(f"Downloading album ({done}/{total})...")

    def _on_album_downloaded(self, _album_folder: str, downloaded: int, total: int) -> None:
        self.status_label.setText(f"Album downloaded: {downloaded}/{total} tracks.")
        self.download_album_button.setEnabled(True)
        if downloaded > 0:
            self.library_changed.emit()

    # -- Errori ---------------------------------------------------------------
    def _on_error(self, message: str) -> None:
        self.status_label.setText(f"Error: {message}")
        self.search_button.setEnabled(True)
        if self._selected_song is not None:
            self.download_song_button.setEnabled(True)
        if self._album_tracks:
            self.download_album_button.setEnabled(True)
        # Come nel pannello dei consigli: "No Internet" è già chiaro nella
        # status label, il popup extra sarebbe solo rumore.
        if message != "No Internet":
            QMessageBox.warning(self, "Error", message)

    def closeEvent(self, event) -> None:
        # Ferma qualunque anteprima in corso quando la finestra si chiude.
        self.preview_engine.stop()
        super().closeEvent(event)

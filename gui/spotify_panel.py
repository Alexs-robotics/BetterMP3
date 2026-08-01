"""
spotify_panel.py
------------------
Pagina "Sync Spotify Liked Songs": legge (in sola lettura) l'elenco dei
brani che piacciono all'utente su Spotify e permette di scaricarli
tutti in un colpo solo, cercandoli su YouTube esattamente come fa la
pagina di ricerca manuale (search_panel.py). Spotify fornisce solo i
METADATI (titolo/artista/album): l'audio arriva sempre da YouTube.

Prima di poter sincronizzare serve configurare le credenziali Spotify
in core/config.py (vedi i commenti lì e in services/spotify_service.py).

Come per search_panel.py, è una finestra separata non modale, ed
eredita automaticamente il tema scuro viola perché lo stylesheet è
applicato a livello di QApplication in main.py.
"""

import os

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
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
from services import spotify_service, youtube_service


# ---------------------------------------------------------------------
# Thread: recupero della lista Liked Songs (può aprire il browser per
# il login Spotify se non c'è ancora un token valido in cache)
# ---------------------------------------------------------------------

class _FetchLikedSongsThread(QThread):
    finished_ok = Signal(list)  # List[LikedTrack]
    finished_error = Signal(str)

    def run(self) -> None:
        try:
            tracks = spotify_service.get_liked_songs()
            self.finished_ok.emit(tracks)
        except Exception as exc:
            self.finished_error.emit("No Internet" if is_no_internet_error(exc) else str(exc))


# ---------------------------------------------------------------------
# Thread: anteprima di un singolo Liked Song (nessun file finisce in libreria)
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
# Thread: download di tutti i Liked Songs (salta quelli già scaricati)
# ---------------------------------------------------------------------

class _DownloadAllLikedThread(QThread):
    progress = Signal(int, int, str)  # (fatti, totale, brano corrente)
    finished_ok = Signal(int, int, int)  # (scaricati, saltati, falliti)
    finished_error = Signal(str)

    def __init__(self, tracks: list) -> None:
        super().__init__()
        self.tracks = tracks
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        downloaded = 0
        skipped = 0
        failed = 0
        total = len(self.tracks)

        try:
            for i, track in enumerate(self.tracks, start=1):
                if self._cancel_requested:
                    break

                self.progress.emit(i, total, f"{track.title} — {track.artist}")

                expected_path = youtube_service.expected_track_path(
                    track.artist, track.title, track.album, WINDOWS_MUSIC_FOLDER
                )
                if os.path.exists(expected_path):
                    # Già scaricato in una sincronizzazione precedente: non
                    # ha senso riscaricarlo, così una risincronizzazione
                    # periodica prende solo i brani nuovi.
                    skipped += 1
                    continue

                try:
                    result = youtube_service.search_track(f"{track.artist} {track.title} audio")
                    if result is None:
                        failed += 1
                        continue
                    path = youtube_service.download_full_track(
                        result.url, track.artist, track.title, track.album or None, WINDOWS_MUSIC_FOLDER
                    )
                    metadata.write_full_tags(path, track.title, track.artist, track.album or "Singles", 1)
                    downloaded += 1
                except Exception as track_exc:
                    # Un brano fallito (non trovato, tag illeggibili, ecc.)
                    # non deve interrompere la sincronizzazione di tutti
                    # gli altri: lo contiamo come fallito e si continua.
                    if is_no_internet_error(track_exc):
                        raise
                    failed += 1

            self.finished_ok.emit(downloaded, skipped, failed)
        except Exception as exc:
            self.finished_error.emit("No Internet" if is_no_internet_error(exc) else str(exc))


# ---------------------------------------------------------------------
# Finestra "Sync Spotify Liked Songs"
# ---------------------------------------------------------------------

class SpotifySyncWindow(QDialog):
    # Emesso dopo ogni sincronizzazione che ha scaricato almeno un
    # brano, così main_window può riscansionare la libreria.
    library_changed = Signal()

    def __init__(self, main_engine: PlaybackEngine, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sync Spotify Liked Songs")
        self.setWindowFlag(Qt.Window)
        self.resize(560, 640)

        self.preview_engine = PlaybackEngine()
        self.main_engine = main_engine

        self._liked_tracks: list = []
        self._selected_track = None
        self._active_threads: list[QThread] = []
        self._download_thread: _DownloadAllLikedThread | None = None

        self.info_label = QLabel(
            "Reads your Spotify Liked Songs (read-only) and lets you download "
            "them all via YouTube, just like the rest of this app."
        )
        self.info_label.setWordWrap(True)

        self.sync_button = QPushButton("🔄 Sync Liked Songs from Spotify")
        self.sync_button.clicked.connect(self._on_sync_clicked)

        self.results_list = QListWidget()
        self.results_list.currentItemChanged.connect(self._on_track_selected)

        self.preview_button = QPushButton("▶ Play preview (30s)")
        self.preview_button.setEnabled(False)
        self.preview_button.clicked.connect(self._on_preview_clicked)

        self.stop_preview_button = QPushButton("⏹ Stop preview")
        self.stop_preview_button.setEnabled(False)
        self.stop_preview_button.clicked.connect(self._on_stop_preview_clicked)

        self.download_all_button = QPushButton("⬇ Download all Liked Songs")
        self.download_all_button.setEnabled(False)
        self.download_all_button.clicked.connect(self._on_download_all_clicked)

        self.cancel_button = QPushButton("Cancel download")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        preview_row = QHBoxLayout()
        preview_row.addWidget(self.preview_button)
        preview_row.addWidget(self.stop_preview_button)

        download_row = QHBoxLayout()
        download_row.addWidget(self.download_all_button)
        download_row.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.info_label)
        layout.addWidget(self.sync_button)
        layout.addWidget(QLabel("Liked Songs:"))
        layout.addWidget(self.results_list, stretch=1)
        layout.addLayout(preview_row)
        layout.addLayout(download_row)
        layout.addWidget(self.status_label)

    # -- Gestione thread (tenuti "vivi" finché non finiscono, altrimenti
    # il garbage collector di Python può distruggerli mentre girano
    # ancora e PySide6 va in crash) -----------------------------------
    def _launch_thread(self, thread: QThread) -> None:
        self._active_threads.append(thread)
        thread.finished.connect(lambda: self._cleanup_thread(thread))
        thread.start()

    def _cleanup_thread(self, thread: QThread) -> None:
        if thread in self._active_threads:
            self._active_threads.remove(thread)
        thread.deleteLater()

    # -- Sincronizzazione -----------------------------------------------------
    def _on_sync_clicked(self) -> None:
        self.results_list.clear()
        self._liked_tracks = []
        self._selected_track = None
        self.preview_button.setEnabled(False)
        self.download_all_button.setEnabled(False)
        self.sync_button.setEnabled(False)
        self.status_label.setText(
            "Syncing... a browser window may open for you to log in and "
            "authorize access to your Liked Songs."
        )

        thread = _FetchLikedSongsThread()
        thread.finished_ok.connect(self._on_liked_songs_ready)
        thread.finished_error.connect(self._on_error)
        self._launch_thread(thread)

    def _on_liked_songs_ready(self, tracks: list) -> None:
        self.sync_button.setEnabled(True)
        self._liked_tracks = tracks
        self.results_list.clear()
        for t in tracks:
            label = f"{t.title} — {t.artist}"
            if t.album:
                label += f"  ({t.album})"
            self.results_list.addItem(QListWidgetItem(label))

        if tracks:
            self.status_label.setText(f"{len(tracks)} Liked Songs found.")
            self.download_all_button.setEnabled(True)
        else:
            self.status_label.setText("No Liked Songs found on this account.")

    # -- Anteprima ------------------------------------------------------------
    def _on_track_selected(self, current: QListWidgetItem, _previous: QListWidgetItem) -> None:
        if current is None:
            return
        self._stop_preview_playback()
        index = self.results_list.currentRow()
        if 0 <= index < len(self._liked_tracks):
            self._selected_track = self._liked_tracks[index]
            self.preview_button.setEnabled(True)
            self.status_label.setText("Ready for preview.")

    def _on_preview_clicked(self) -> None:
        if self._selected_track is None:
            return

        self._stop_preview_playback()
        if self.main_engine is not None and self.main_engine.is_playing():
            self.main_engine.pause()

        self.status_label.setText("Downloading preview...")
        self.preview_button.setEnabled(False)

        thread = _PreviewThread(self._selected_track.title, self._selected_track.artist)
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

    # -- Download di tutti i Liked Songs --------------------------------------
    def _on_download_all_clicked(self) -> None:
        if not self._liked_tracks:
            return
        self.status_label.setText(f"Downloading (0/{len(self._liked_tracks)})...")
        self.download_all_button.setEnabled(False)
        self.sync_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

        self._download_thread = _DownloadAllLikedThread(self._liked_tracks)
        self._download_thread.progress.connect(self._on_download_progress)
        self._download_thread.finished_ok.connect(self._on_download_all_finished)
        self._download_thread.finished_error.connect(self._on_error)
        self._launch_thread(self._download_thread)

    def _on_cancel_clicked(self) -> None:
        if self._download_thread is not None:
            self._download_thread.request_cancel()
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Cancelling after the current track...")

    def _on_download_progress(self, done: int, total: int, current_title: str) -> None:
        self.status_label.setText(f"Downloading ({done}/{total}): {current_title}")

    def _on_download_all_finished(self, downloaded: int, skipped: int, failed: int) -> None:
        self.download_all_button.setEnabled(True)
        self.sync_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_label.setText(
            f"Done. Downloaded: {downloaded}, already had: {skipped}, failed: {failed}."
        )
        if downloaded > 0:
            self.library_changed.emit()

    # -- Errori ---------------------------------------------------------------
    def _on_error(self, message: str) -> None:
        self.sync_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if self._liked_tracks:
            self.download_all_button.setEnabled(True)
        if self._selected_track is not None:
            self.preview_button.setEnabled(True)
        self.status_label.setText(f"Error: {message}")
        # Come nelle altre pagine: "No Internet" è già chiaro nella status
        # label, il popup extra sarebbe solo rumore.
        if message != "No Internet":
            QMessageBox.warning(self, "Error", message)

    def closeEvent(self, event) -> None:
        self.preview_engine.stop()
        if self._download_thread is not None:
            self._download_thread.request_cancel()
        super().closeEvent(event)

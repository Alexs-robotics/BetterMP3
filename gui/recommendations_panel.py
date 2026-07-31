"""
recommendations_panel.py
--------------------------
Pannello laterale che, per il brano attualmente selezionato/in
riproduzione, mostra una lista di brani simili (via Last.fm) e per
ognuno permette di:
  1. ascoltare una ANTEPRIMA di ~30 secondi cercata su YouTube
  2. fermarla in qualsiasi momento
  3. se piace, scaricare il brano completo nella cartella corretta
     (album o singoli)

La preview usa un motore di riproduzione SEPARATO da quello della
libreria principale (per poter scaricare/ascoltare un consiglio senza
perdere il punto in cui era il brano che stavi ascoltando). Per evitare
che le due riproduzioni si sovrappongano, quando parte una preview la
riproduzione della libreria viene messa in automatico in pausa.

Le chiamate di rete girano su QThread separati per non bloccare la GUI.
"""

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.player import PlaybackEngine
from services import lastfm_service, youtube_service
from core.config import WINDOWS_MUSIC_FOLDER

class _FetchSimilarThread(QThread):
    finished_ok = Signal(list)
    finished_error = Signal(str)

    def __init__(self, title: str, artist: str) -> None:
        super().__init__()
        self.title = title
        self.artist = artist

    def run(self) -> None:
        try:
            results = lastfm_service.get_similar_tracks(self.title, self.artist)
            self.finished_ok.emit(results)
        except Exception as exc:
            self.finished_error.emit(str(exc))


class _PreviewThread(QThread):
    finished_ok = Signal(str, str)  # (preview_path, video_url)
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
            self.finished_ok.emit(preview_path, result.url)
        except Exception as exc:
            self.finished_error.emit(str(exc))


class _DownloadThread(QThread):
    finished_ok = Signal(str)
    finished_error = Signal(str)

    def __init__(self, video_url: str, title: str, artist: str, album_name: str | None) -> None:
        super().__init__()
        self.video_url = video_url
        self.title = title
        self.artist = artist
        self.album_name = album_name

    def run(self) -> None:
        try:
            # Pass all 5 arguments exactly as expected by the function signature
            path = youtube_service.download_full_track(
                self.video_url,
                self.artist,
                self.title,
                self.album_name,
                WINDOWS_MUSIC_FOLDER
            )
            self.finished_ok.emit(path)
        except Exception as exc:
            self.finished_error.emit(str(exc))


class RecommendationsPanel(QWidget):
    def __init__(self, preview_engine: PlaybackEngine, main_engine: PlaybackEngine | None = None, parent=None) -> None:
        super().__init__(parent)
        self.preview_engine = preview_engine
        # Riferimento al motore della libreria principale: serve solo per
        # metterlo in pausa quando parte una preview, così le due
        # riproduzioni non si sovrappongono.
        self.main_engine = main_engine
        self._current_video_url: str | None = None
        self._current_result_title = ""
        self._current_result_artist = ""

        self.title_label = QLabel("Recommended for you")
        self.title_label.setStyleSheet("font-weight: 600;")

        self.similar_list = QListWidget()
        self.similar_list.itemClicked.connect(self._on_similar_selected)

        self.preview_button = QPushButton("▶ Play preview (30s)")
        self.preview_button.setEnabled(False)
        self.preview_button.clicked.connect(self._on_preview_clicked)

        self.stop_preview_button = QPushButton("⏹ Stop preview")
        self.stop_preview_button.setEnabled(False)
        self.stop_preview_button.clicked.connect(self._on_stop_preview_clicked)

        self.download_button = QPushButton("⬇ Download full track")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self._on_download_clicked)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.similar_list)
        buttons_row = QHBoxLayout()
        buttons_row.addWidget(self.preview_button)
        buttons_row.addWidget(self.stop_preview_button)
        layout.addLayout(buttons_row)
        layout.addWidget(self.download_button)
        layout.addWidget(self.status_label)

        self._fetch_thread: _FetchSimilarThread | None = None
        self._preview_thread: _PreviewThread | None = None
        self._download_thread: _DownloadThread | None = None

        # Riferimenti "tenuti in vita" per ogni thread in esecuzione. Senza
        # questa lista, se l'utente cambia brano rapidamente il thread
        # precedente (a cui non punta più nessuna variabile) può essere
        # distrutto dal garbage collector di Python MENTRE gira ancora,
        # il che in PySide6 causa un crash dell'intera applicazione. Il
        # thread viene rimosso dalla lista solo a lavoro concluso.
        self._active_threads: list[QThread] = []

    def _launch_thread(self, thread: QThread) -> None:
        self._active_threads.append(thread)
        thread.finished.connect(lambda: self._cleanup_thread(thread))
        thread.start()

    def _cleanup_thread(self, thread: QThread) -> None:
        if thread in self._active_threads:
            self._active_threads.remove(thread)
        thread.deleteLater()

    def refresh_for_track(self, title: str, artist: str) -> None:
        self.status_label.setText("Searching for similar tracks...")
        self.similar_list.clear()
        self.preview_button.setEnabled(False)
        self.download_button.setEnabled(False)

        self._fetch_thread = _FetchSimilarThread(title, artist)
        self._fetch_thread.finished_ok.connect(self._on_similar_ready)
        self._fetch_thread.finished_error.connect(self._on_error)
        self._launch_thread(self._fetch_thread)

    def _on_similar_ready(self, results) -> None:
        # Se nel frattempo l'utente ha selezionato un altro brano, questo
        # risultato è ormai superato: lo scartiamo invece di sovrascrivere
        # la lista con dati non più pertinenti.
        if self.sender() is not self._fetch_thread:
            return
        self.status_label.setText(f"{len(results)} similar tracks found.")
        for r in results:
            item = QListWidgetItem(f"{r.title} — {r.artist}  ({int(r.match_score * 100)}% match)")
            item.setData(1000, (r.title, r.artist))
            self.similar_list.addItem(item)

    def _on_similar_selected(self, item: QListWidgetItem) -> None:
        # Cambiare brano selezionato interrompe subito qualunque anteprima
        # in corso, per evitare ambiguità su quale sia "quella attiva".
        self._stop_preview_playback()

        title, artist = item.data(1000)
        self._current_result_title = title
        self._current_result_artist = artist
        self._current_video_url = None
        self.preview_button.setEnabled(True)
        self.download_button.setEnabled(False)
        self.status_label.setText("Ready for preview.")

    def _on_preview_clicked(self) -> None:
        # Ferma un'eventuale preview già in riproduzione prima di scaricarne
        # un'altra, e mette in pausa la riproduzione della libreria
        # principale così le due non suonano insieme.
        self._stop_preview_playback()
        if self.main_engine is not None and self.main_engine.is_playing():
            self.main_engine.pause()

        self.status_label.setText("Downloading preview...")
        self.preview_button.setEnabled(False)

        self._preview_thread = _PreviewThread(self._current_result_title, self._current_result_artist)
        self._preview_thread.finished_ok.connect(self._on_preview_ready)
        self._preview_thread.finished_error.connect(self._on_error)
        self._launch_thread(self._preview_thread)

    def _on_preview_ready(self, preview_path: str, video_url: str) -> None:
        self._current_video_url = video_url
        self.preview_engine.load_playlist([preview_path], start_index=0)
        self.status_label.setText("Preview playing. Do you like it?")
        self.preview_button.setEnabled(True)
        self.stop_preview_button.setEnabled(True)
        self.download_button.setEnabled(True)

    def _on_stop_preview_clicked(self) -> None:
        self._stop_preview_playback()
        self.status_label.setText("Preview stopped.")

    def _stop_preview_playback(self) -> None:
        self.preview_engine.stop()
        self.stop_preview_button.setEnabled(False)

    def _on_download_clicked(self) -> None:
        if not self._current_video_url:
            return
        self.status_label.setText("Downloading full track...")
        self.download_button.setEnabled(False)

        # Se il brano correntemente in libreria appartiene a un album, viene chiesto
        # implicitamente tramite album_name=None: il chiamante (main_window) può
        # comunque passare un nome album, qui va di default nei singoli.
        self._download_thread = _DownloadThread(
            self._current_video_url, self._current_result_title, self._current_result_artist, None
        )
        self._download_thread.finished_ok.connect(self._on_download_ready)
        self._download_thread.finished_error.connect(self._on_error)
        self._launch_thread(self._download_thread)

    def _on_download_ready(self, path: str) -> None:
        self.status_label.setText(f"Downloaded to: {path}")
        self.download_button.setEnabled(True)

    def _on_error(self, message: str) -> None:
        self.status_label.setText(f"Error: {message}")
        self.preview_button.setEnabled(True)
        self.download_button.setEnabled(bool(self._current_video_url))
        QMessageBox.warning(self, "Error", message)

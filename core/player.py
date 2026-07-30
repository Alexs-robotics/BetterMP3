"""
player.py
---------
Motore di riproduzione audio. Usa `python-vlc` (bindings di libVLC), che
a differenza di pygame supporta nativamente:
  - cambio di velocità di riproduzione (2x, 1.5x, ecc.) senza alterare il pitch in modo strano
  - seek preciso a un punto qualsiasi del brano
  - pausa/ripresa
  - callback di fine-brano per passare automaticamente al successivo

Richiede che VLC (o le sue DLL) sia disponibile: vedi requirements.txt e
README per le istruzioni di packaging.
"""

from typing import Callable, List, Optional

import vlc

import threading

class PlaybackEngine:
    def __init__(self) -> None:
        self._instance = vlc.Instance("--quiet")
        self._player: vlc.MediaPlayer = self._instance.media_player_new()
        self._playlist: List[str] = []
        self._current_index: int = -1
        self._rate: float = 1.0

        self._on_track_changed: Optional[Callable[[int], None]] = None
        self._on_playback_ended: Optional[Callable[[], None]] = None

        events = self._player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self._handle_end_reached)

    # -- Callback registration -------------------------------------------------
    def set_on_track_changed(self, callback: Callable[[int], None]) -> None:
        self._on_track_changed = callback

    def set_on_playback_ended(self, callback: Callable[[], None]) -> None:
        self._on_playback_ended = callback

    def _handle_end_reached(self, _event) -> None:
        # Eseguito su un thread di VLC: passa al brano successivo se c'è.
        if self._current_index + 1 < len(self._playlist):
            threading.Timer(0.1, self.next).start()
        elif self._on_playback_ended:
            threading.Timer(0.1, self._on_playback_ended).start()

    # -- Gestione playlist -------------------------------------------------
    def load_playlist(self, paths: List[str], start_index: int = 0) -> None:
        """Carica un album o una lista di brani e inizia la riproduzione da start_index."""
        self._playlist = list(paths)
        self._current_index = -1
        if self._playlist:
            self._play_index(start_index)

    def _play_index(self, index: int) -> None:
        if not (0 <= index < len(self._playlist)):
            return
        self._current_index = index
        media = self._instance.media_new(self._playlist[index])
        self._player.set_media(media)
        self._player.play()
        self._player.set_rate(self._rate)
        if self._on_track_changed:
            self._on_track_changed(index)

    # -- Controlli di riproduzione -------------------------------------------------
    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()  # toggle play/pausa in libVLC

    def stop(self) -> None:
        self._player.stop()

    def next(self) -> None:
        self._play_index(self._current_index + 1)

    def previous(self) -> None:
        self._play_index(self._current_index - 1)

    def set_speed(self, rate: float) -> None:
        """rate: 1.0 = normale, 2.0 = doppia velocità, 0.5 = metà velocità, ecc."""
        self._rate = rate
        self._player.set_rate(rate)

    def get_speed(self) -> float:
        return self._rate

    def seek_to_seconds(self, seconds: float) -> None:
        self._player.set_time(int(seconds * 1000))

    def seek_to_fraction(self, fraction: float) -> None:
        """fraction: 0.0 - 1.0, utile per una barra di avanzamento trascinabile."""
        self._player.set_position(max(0.0, min(1.0, fraction)))

    def get_position_seconds(self) -> float:
        return max(0, self._player.get_time()) / 1000.0

    def get_duration_seconds(self) -> float:
        length = self._player.get_length()
        return max(0, length) / 1000.0

    def is_playing(self) -> bool:
        return bool(self._player.is_playing())

    def current_index(self) -> int:
        return self._current_index

    def set_volume(self, volume_0_100: int) -> None:
        self._player.audio_set_volume(max(0, min(100, volume_0_100)))

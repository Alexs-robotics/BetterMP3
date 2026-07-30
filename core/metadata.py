"""
metadata.py
-----------
Wrapper attorno a `mutagen` per leggere e MODIFICARE i tag ID3 dei file
audio. In particolare gestisce il campo "numero traccia" (TRCK), che è
quello richiesto per riordinare le canzoni dentro un album.
"""

from dataclasses import dataclass
from typing import Optional

from mutagen import File as MutagenFile
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TRCK
from mutagen.mp3 import MP3


@dataclass
class TrackMetadata:
    path: str
    title: str
    artist: str
    album: str
    track_number: int
    duration_seconds: float


def read_metadata(path: str) -> TrackMetadata:
    """Legge i tag di un file audio. Se un tag manca, usa dei fallback sensati."""
    audio = MutagenFile(path, easy=True)
    duration = 0.0
    try:
        raw = MutagenFile(path)
        if raw is not None and raw.info is not None:
            duration = float(raw.info.length)
    except Exception:
        pass

    if audio is None:
        # File non supportato per i tag (es. wav senza tag): usa il nome file.
        import os
        name = os.path.splitext(os.path.basename(path))[0]
        return TrackMetadata(path, name, "Sconosciuto", "Sconosciuto", 0, duration)

    def _first(tag_name, default):
        val = audio.get(tag_name)
        # Alcuni file hanno il tag presente ma vuoto ("" o solo spazi):
        # in quel caso va trattato come mancante, non come stringa valida.
        if val and str(val[0]).strip():
            return val[0]
        return default

    import os
    filename_without_ext = os.path.splitext(os.path.basename(path))[0]

    # Se il tag titolo manca, usa il nome del file (senza estensione)
    # invece di un generico "Senza titolo": è molto più utile per
    # riconoscere il brano nella lista.
    title = _first("title", filename_without_ext)
    artist = _first("artist", "Artista sconosciuto")
    album = _first("album", "Album sconosciuto")

    track_raw = _first("tracknumber", "0")
    # Il tag può essere "3" oppure "3/12" (traccia 3 di 12).
    track_number = 0
    try:
        track_number = int(str(track_raw).split("/")[0])
    except (ValueError, IndexError):
        track_number = 0

    return TrackMetadata(path, title, artist, album, track_number, duration)


def set_track_number(path: str, new_number: int) -> None:
    """
    Modifica il numero della traccia (il numero "#" dentro l'album)
    scrivendo direttamente il frame TRCK dell'ID3, e lo salva su disco.
    Funziona per gli MP3. Per altri formati usa il tag "easy" generico.
    """
    if path.lower().endswith(".mp3"):
        try:
            audio = ID3(path)
        except Exception:
            # Nessun header ID3 esistente: lo creiamo.
            audio = ID3()
        audio.setall("TRCK", [TRCK(encoding=3, text=str(new_number))])
        audio.save(path)
    else:
        audio = MutagenFile(path, easy=True)
        if audio is None:
            raise ValueError(f"Formato non supportato per la modifica dei tag: {path}")
        audio["tracknumber"] = str(new_number)
        audio.save()

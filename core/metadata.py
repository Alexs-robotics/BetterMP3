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
        # File format not supported for tags (e.g. wav without tags): use the filename.
        import os
        name = os.path.splitext(os.path.basename(path))[0]
        return TrackMetadata(path, name, "Unknown Artist", "Unknown Album", 0, duration)

    def _first(tag_name, default):
        val = audio.get(tag_name)
        # Some files have the tag present but empty ("" or just whitespace):
        # treat that as missing, not as a valid string.
        if val and str(val[0]).strip():
            return val[0]
        return default

    import os
    filename_without_ext = os.path.splitext(os.path.basename(path))[0]

    # If the title tag is missing, use the filename (without extension)
    # instead of a generic "Untitled" — much more useful for recognizing
    # the track in the list.
    title = _first("title", filename_without_ext)
    artist = _first("artist", "Unknown Artist")
    album = _first("album", "Unknown Album")

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
            raise ValueError(f"Unsupported format for tag editing: {path}")
        audio["tracknumber"] = str(new_number)
        audio.save()


def write_full_tags(path: str, title: str, artist: str, album: str, track_number: int = 1) -> None:
    """
    Scrive titolo, artista, album e numero di traccia su un file mp3,
    creando l'header ID3 se non esiste ancora (es. subito dopo un
    download da YouTube via yt-dlp, che spesso lascia tag assenti o
    incompleti). Usata dal flusso di download dei brani consigliati,
    così la libreria mostra subito le informazioni corrette invece di
    "Unknown Artist"/"Unknown Album".
    """
    try:
        audio = EasyID3(path)
    except Exception:
        # Nessun header ID3 presente: lo creiamo da zero.
        raw = MutagenFile(path)
        if raw is None:
            raise ValueError(f"Unsupported format for tag writing: {path}")
        raw.add_tags()
        raw.save()
        audio = EasyID3(path)

    audio["title"] = title
    audio["artist"] = artist
    audio["album"] = album
    audio["tracknumber"] = str(track_number)
    audio.save()
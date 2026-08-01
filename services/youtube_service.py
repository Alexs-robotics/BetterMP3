"""
youtube_service.py
-------------------
Usa `yt-dlp` per:
  1. cercare su YouTube un brano consigliato (titolo + artista), o una
     lista di risultati per la ricerca manuale
  2. scaricarne solo una ANTEPRIMA di ~30 secondi (usa la funzione
     "download_ranges" di yt-dlp, che taglia durante il download senza
     dover scaricare l'intero file)
  3. se all'utente piace, scaricare il brano completo in mp3 dentro la
     cartella corretta (album o singoli, a seconda della scelta utente)

Nota legale: scaricare musica da YouTube può violare i Termini di
Servizio di YouTube e, a seconda del brano e della giurisdizione, il
diritto d'autore. Questa funzionalità va usata solo per contenuti che
si ha il diritto di scaricare (es. materiale royalty-free, propri
caricamenti, o dove la legge locale lo consente).
"""

import os
import shutil
from dataclasses import dataclass
from typing import List, Optional

import yt_dlp

from core.config import (
    DOWNLOADS_ALBUMS_DIR,
    DOWNLOADS_SINGLES_DIR,
    PREVIEW_CACHE_DIR,
    PREVIEW_DURATION_SECONDS,
)


@dataclass
class YoutubeSearchResult:
    video_id: str
    title: str
    channel: str
    url: str


def search_track(query: str) -> Optional[YoutubeSearchResult]:
    """Cerca `query` su YouTube e ritorna il primo risultato utile."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch1",
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        entries = info.get("entries") or []
        if not entries:
            return None
        top = entries[0]
        return YoutubeSearchResult(
            video_id=top["id"],
            title=top.get("title", query),
            channel=top.get("uploader", "Unknown"),
            url=top.get("webpage_url", f"https://www.youtube.com/watch?v={top['id']}"),
        )


def search_tracks(query: str, limit: int = 15) -> List[YoutubeSearchResult]:
    """
    Come `search_track`, ma ritorna fino a `limit` risultati invece di
    uno solo. Usata dalla pagina di ricerca manuale in modalità
    "Songs", dove l'utente sceglie tra più brani trovati.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "default_search": f"ytsearch{max(1, limit)}",
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        entries = info.get("entries") or []
        results: List[YoutubeSearchResult] = []
        for entry in entries:
            if not entry:
                continue
            results.append(
                YoutubeSearchResult(
                    video_id=entry["id"],
                    title=entry.get("title", query),
                    channel=entry.get("uploader", "Unknown"),
                    url=entry.get("webpage_url", f"https://www.youtube.com/watch?v={entry['id']}"),
                )
            )
        return results


def clear_preview_cache() -> None:
    """
    Svuota completamente la cartella delle anteprime (i file mp3 di
    ~30s scaricati per l'ascolto rapido di un brano prima di
    scaricarlo per intero). Le anteprime sono usa-e-getta: non ha
    senso tenerle tra un riavvio e l'altro dell'app, e altrimenti col
    tempo si accumulerebbero senza motivo occupando spazio su disco.

    Va chiamata una volta sola, all'avvio del programma (vedi main.py).
    Non solleva eccezioni se un file è bloccato o già rimosso: la
    pulizia della cache non deve mai impedire l'avvio dell'app.
    """
    if not os.path.isdir(PREVIEW_CACHE_DIR):
        return
    for name in os.listdir(PREVIEW_CACHE_DIR):
        entry_path = os.path.join(PREVIEW_CACHE_DIR, name)
        try:
            if os.path.isfile(entry_path) or os.path.islink(entry_path):
                os.remove(entry_path)
            elif os.path.isdir(entry_path):
                shutil.rmtree(entry_path)
        except Exception as exc:
            print(f"[youtube_service] Could not remove preview cache file {entry_path}: {exc}")


def download_preview(video_url: str, safe_filename: str) -> str:
    """
    Scarica solo i primi PREVIEW_DURATION_SECONDS secondi come mp3,
    dentro la cartella cache delle anteprime. Ritorna il path del file.
    """
    output_template = os.path.join(PREVIEW_CACHE_DIR, f"{safe_filename}.%(ext)s")

    def _ranges(_info_dict, _ydl):
        return [{"start_time": 0, "end_time": PREVIEW_DURATION_SECONDS}]

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "download_ranges": _ranges,
        "force_keyframes_at_cuts": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    return os.path.join(PREVIEW_CACHE_DIR, f"{safe_filename}.mp3")


def expected_track_path(
    artist_name: str,
    track_title: str,
    album_name: Optional[str],
    music_root_folder: str,
) -> str:
    """
    Calcola il percorso in cui `download_full_track` salverebbe questo
    brano, SENZA scaricare nulla. Usato per capire se un brano è già
    presente in libreria (es. durante la sincronizzazione dei Liked
    Songs di Spotify) ed evitare di riscaricarlo inutilmente.
    """
    artist_folder = _sanitize_folder_name(artist_name)
    album_folder = _sanitize_folder_name(album_name or "Singles")
    safe_filename = _sanitize_folder_name(track_title)
    return os.path.join(music_root_folder, artist_folder, album_folder, f"{safe_filename}.mp3")


def download_full_track(
    video_url: str,
    artist_name: str,
    track_title: str,
    album_name: Optional[str],
    music_root_folder: str,
) -> str:
    """
    Scarica il brano completo come mp3 DENTRO la cartella musicale
    scansionata dall'app (non in una cartella separata dell'app), così
    la libreria lo rileva automaticamente alla prossima scansione.

    Struttura creata: <music_root_folder>/<Artista>/<Album>/<Titolo>.mp3
    (se `album_name` non è noto, viene usata la sottocartella "Singles").
    """
    artist_folder = _sanitize_folder_name(artist_name)
    album_folder = _sanitize_folder_name(album_name or "Singles")
    target_dir = os.path.join(music_root_folder, artist_folder, album_folder)
    os.makedirs(target_dir, exist_ok=True)

    safe_filename = _sanitize_folder_name(track_title)
    output_template = os.path.join(target_dir, f"{safe_filename}.%(ext)s")
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    return os.path.join(target_dir, f"{safe_filename}.mp3")


def _sanitize_folder_name(name: str) -> str:
    invalid = '<>:"/\\|?*'
    for ch in invalid:
        name = name.replace(ch, "_")
    return name.strip() or "Unknown"

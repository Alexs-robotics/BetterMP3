"""
lastfm_service.py
------------------
Usa l'API pubblica e gratuita di Last.fm per trovare brani "simili" a
uno già presente in libreria.

NOTA IMPORTANTE: originariamente il progetto avrebbe dovuto usare
l'endpoint "Recommendations" di Spotify. Spotify lo ha però disattivato
per tutte le nuove app dal 27 novembre 2024 (insieme ad Audio Features
e Related Artists), e non esiste un percorso per farselo riattivare.
Last.fm offre lo stesso tipo di funzionalità (track.getSimilar /
artist.getSimilar) tramite una API key gratuita ottenibile su:
https://www.last.fm/api/account/create

Per usare questo modulo, imposta LASTFM_API_KEY in core/config.py
oppure come variabile d'ambiente.
"""

from dataclasses import dataclass
from typing import List

import requests

from core.config import LASTFM_API_KEY

API_ROOT = "https://ws.audioscrobbler.com/2.0/"


@dataclass
class SimilarTrack:
    title: str
    artist: str
    match_score: float  # 0.0 - 1.0, how "similar" according to Last.fm


def get_similar_tracks(title: str, artist: str, limit: int = 10) -> List[SimilarTrack]:
    """
    Interroga track.getSimilar. Se Last.fm non trova il brano esatto
    (succede spesso con artisti di nicchia/poco noti su Last.fm), fa un
    fallback su artist.getSimilar + artist.getTopTracks per restituire
    comunque titoli di brani reali (non solo nomi di artisti).
    """
    if LASTFM_API_KEY == "INSERISCI_QUI_LA_TUA_API_KEY":
        raise RuntimeError(
            "You must set LASTFM_API_KEY in core/config.py (free key from last.fm/api)"
        )

    params = {
        "method": "track.getsimilar",
        "artist": artist,
        "track": title,
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "limit": limit,
    }
    response = requests.get(API_ROOT, params=params, timeout=10)
    data = response.json()

    similar_tracks_node = data.get("similartracks", {}).get("track", [])
    if similar_tracks_node:
        return [
            SimilarTrack(
                title=t["name"],
                artist=t["artist"]["name"],
                match_score=float(t.get("match", 0.0)),
            )
            for t in similar_tracks_node
        ]

    # Fallback: no direct track match, try via similar artists instead.
    return _similar_by_artist(artist, limit)


def _get_top_track_for_artist(artist_name: str) -> str | None:
    """
    Ritorna il titolo del brano più popolare di un artista secondo
    Last.fm (artist.getTopTracks), oppure None se non trovato.
    Usato per dare un titolo REALE ai suggerimenti quando si è dovuto
    ripiegare sugli "artisti simili" invece che sui "brani simili".
    """
    params = {
        "method": "artist.gettoptracks",
        "artist": artist_name,
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "limit": 1,
    }
    try:
        response = requests.get(API_ROOT, params=params, timeout=10)
        data = response.json()
        tracks = data.get("toptracks", {}).get("track", [])
        if tracks:
            top = tracks[0] if isinstance(tracks, list) else tracks
            return top.get("name")
    except Exception:
        pass
    return None


def _similar_by_artist(seed_artist: str, limit: int) -> List[SimilarTrack]:
    params = {
        "method": "artist.getsimilar",
        "artist": seed_artist,
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "limit": limit,
    }
    response = requests.get(API_ROOT, params=params, timeout=10)
    data = response.json()
    artists_node = data.get("similarartists", {}).get("artist", [])

    results: List[SimilarTrack] = []
    for a in artists_node:
        similar_artist_name = a["name"]

        # Last.fm a volte include l'artista di partenza stesso nei
        # risultati quando non ha abbastanza dati: lo escludiamo, non è
        # un vero suggerimento.
        if similar_artist_name.strip().lower() == seed_artist.strip().lower():
            continue

        # Recupera il brano più popolare di quell'artista, così il
        # suggerimento ha un titolo di canzone reale invece di un
        # placeholder generico.
        top_track_title = _get_top_track_for_artist(similar_artist_name)
        if not top_track_title:
            continue

        results.append(
            SimilarTrack(
                title=top_track_title,
                artist=similar_artist_name,
                match_score=float(a.get("match", 0.0)),
            )
        )
        if len(results) >= limit:
            break

    return results

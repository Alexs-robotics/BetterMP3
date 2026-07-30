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
    match_score: float  # 0.0 - 1.0, quanto è "simile" secondo Last.fm


def get_similar_tracks(title: str, artist: str, limit: int = 10) -> List[SimilarTrack]:
    """
    Interroga track.getSimilar. Se Last.fm non trova il brano esatto
    (succede con brani poco noti/locali), fa un fallback su
    artist.getSimilar per restare comunque utile.
    """
    if LASTFM_API_KEY == "INSERISCI_QUI_LA_TUA_API_KEY":
        raise RuntimeError(
            "Devi impostare LASTFM_API_KEY in core/config.py (chiave gratuita su last.fm/api)"
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

    # Fallback: nessun match diretto sul brano, proviamo con l'artista.
    return _similar_by_artist(artist, limit)


def _similar_by_artist(artist: str, limit: int) -> List[SimilarTrack]:
    params = {
        "method": "artist.getsimilar",
        "artist": artist,
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "limit": limit,
    }
    response = requests.get(API_ROOT, params=params, timeout=10)
    data = response.json()
    artists_node = data.get("similarartists", {}).get("artist", [])

    results = []
    for a in artists_node:
        # Non abbiamo un titolo di brano specifico: suggeriamo l'artista
        # simile stesso, la ricerca YouTube farà il resto.
        results.append(
            SimilarTrack(title=f"Brani di {a['name']}", artist=a["name"], match_score=float(a.get("match", 0.0)))
        )
    return results

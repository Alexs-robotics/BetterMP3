"""
spotify_service.py
--------------------
Sincronizza i brani "Liked Songs" (Brani che ti piacciono) dell'utente
da Spotify, usando l'API ufficiale di Spotify (Web API) tramite la
libreria `spotipy`.

IMPORTANTE — cosa serve prima di usare questo modulo (vedi anche i
commenti in core/config.py):
  1. Crea una app gratuita sulla Spotify Developer Dashboard:
     https://developer.spotify.com/dashboard
  2. Nelle impostazioni della app, aggiungi come Redirect URI
     ESATTAMENTE il valore di SPOTIFY_REDIRECT_URI in core/config.py
     (di default: http://127.0.0.1:8888/callback).
  3. Copia il Client ID e il Client Secret e impostali in
     core/config.py (o come variabili d'ambiente SPOTIFY_CLIENT_ID /
     SPOTIFY_CLIENT_SECRET).

Alla prima sincronizzazione si apre una pagina del browser dove
Spotify chiede di autorizzare l'app a leggere la libreria dell'utente
(scope "user-library-read", SOLA LETTURA: l'app non può modificare i
Liked Songs). Il token ottenuto viene salvato in cache su disco
(SPOTIFY_TOKEN_CACHE_PATH), così le sincronizzazioni successive non
richiedono un nuovo login.

NOTA: questo modulo legge solo i METADATI (titolo/artista/album) dei
brani che piacciono all'utente. Il download audio vero e proprio
avviene sempre tramite YouTube (youtube_service.py), esattamente come
per la ricerca manuale: Spotify non fornisce né permette di scaricare
l'audio dei brani, questo modulo serve solo a sapere QUALI brani
cercare.

Richiede il pacchetto `spotipy` (pip install spotipy).
"""

from dataclasses import dataclass
from typing import List

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from core.config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_TOKEN_CACHE_PATH,
)

# Sola lettura della libreria: l'app non può modificare/aggiungere/
# rimuovere Liked Songs con questo scope.
_SCOPE = "user-library-read"


@dataclass
class LikedTrack:
    title: str
    artist: str
    album: str  # può essere stringa vuota se Spotify non la fornisce


def _check_credentials() -> None:
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise RuntimeError(
            "You must set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in "
            "core/config.py (free credentials from developer.spotify.com/dashboard)"
        )


def _get_client() -> spotipy.Spotify:
    _check_credentials()
    auth_manager = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=_SCOPE,
        cache_path=SPOTIFY_TOKEN_CACHE_PATH,
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def get_liked_songs() -> List[LikedTrack]:
    """
    Scarica l'elenco completo dei "Liked Songs" dell'account collegato,
    gestendo la paginazione (l'API di Spotify ne restituisce al
    massimo 50 per richiesta). La prima chiamata può aprire il browser
    per il login/consenso, se non c'è ancora un token valido in cache.
    """
    client = _get_client()

    liked: List[LikedTrack] = []
    offset = 0
    limit = 50
    while True:
        page = client.current_user_saved_tracks(limit=limit, offset=offset)
        items = page.get("items", [])
        if not items:
            break

        for item in items:
            track = item.get("track") or {}
            if not track:
                continue
            artists = track.get("artists") or []
            artist_name = artists[0]["name"] if artists else "Unknown Artist"
            album_node = track.get("album") or {}
            liked.append(
                LikedTrack(
                    title=track.get("name", "Unknown Title"),
                    artist=artist_name,
                    album=album_node.get("name", ""),
                )
            )

        offset += limit
        if len(items) < limit:
            break  # ultima pagina raggiunta

    return liked

"""
config.py
---------
Configurazione centrale dell'applicazione: percorsi delle cartelle usate
dal player, chiavi API dei servizi esterni e costanti varie.

Tutte le altre parti del programma importano da qui, così le impostazioni
si cambiano in un solo punto.
"""

import os
import sys


def _app_base_dir() -> str:
    """
    Ritorna la cartella base dell'app.
    Quando l'app è impacchettata con PyInstaller (--onefile), i file vanno
    scritti accanto all'eseguibile e non nella cartella temporanea di
    estrazione (sys._MEIPASS), altrimenti si perderebbero ad ogni avvio.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR = _app_base_dir()

# Cartella "Music" di default di Windows (funziona anche su altri OS
# perché usa comunque la home utente).
WINDOWS_MUSIC_FOLDER = os.path.join(os.path.expanduser("~"), "Music")

# Dove vengono salvati i brani scaricati dai consigli, separati come
# richiesto: album interi vs singoli.
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
DOWNLOADS_ALBUMS_DIR = os.path.join(DOWNLOADS_DIR, "albums")
DOWNLOADS_SINGLES_DIR = os.path.join(DOWNLOADS_DIR, "singles")

# Anteprime temporanee (i primi ~30s di un brano suggerito, prima di
# scaricarlo per intero).
PREVIEW_CACHE_DIR = os.path.join(BASE_DIR, "preview_cache")

# Database SQLite che fa da cache della libreria musicale (evita di
# rileggere tutti i tag ID3 ad ogni avvio).
DATABASE_PATH = os.path.join(BASE_DIR, "library.db")

for _d in (DOWNLOADS_DIR, DOWNLOADS_ALBUMS_DIR, DOWNLOADS_SINGLES_DIR, PREVIEW_CACHE_DIR):
    os.makedirs(_d, exist_ok=True)

# ---------------------------------------------------------------------
# Chiavi API — da compilare con le proprie credenziali gratuite.
# Last.fm: https://www.last.fm/api/account/create  (gratuita, istantanea)
# ---------------------------------------------------------------------
LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY", "INSERT_YOUR_API_KEY_HERE")

# ---------------------------------------------------------------------
# Spotify — SOLO per leggere i "Liked Songs" dell'utente (sincronizzazione
# in sola lettura, scope "user-library-read"). L'audio non viene mai
# scaricato da Spotify: viene sempre cercato e scaricato su YouTube,
# esattamente come per la ricerca manuale.
#
# Per usarla:
#   1. Crea una app gratuita su https://developer.spotify.com/dashboard
#   2. Nelle impostazioni della app aggiungi come Redirect URI ESATTAMENTE
#      il valore di SPOTIFY_REDIRECT_URI qui sotto.
#   3. Copia Client ID e Client Secret e incollali sotto (o impostali
#      come variabili d'ambiente).
# Al primo utilizzo si aprirà il browser per il login/consenso; il
# token ottenuto viene poi salvato in cache, quindi non serve rifare
# il login ad ogni sincronizzazione.
# ---------------------------------------------------------------------
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "INSERT_YOUR_SPOTIFY_CLIENT_ID_HERE")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "INSERT_YOUR_SPOTIFY_CLIENT_SECRET_HERE")
SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
SPOTIFY_TOKEN_CACHE_PATH = os.path.join(BASE_DIR, ".spotify_token_cache")

# Durata (in secondi) della preview scaricata via yt-dlp prima del
# download completo.
PREVIEW_DURATION_SECONDS = 30

# Estensioni audio riconosciute durante la scansione della libreria.
SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".wav", ".ogg"}

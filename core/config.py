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
LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY", "INSERT_YOUR_API_HERE")

# Durata (in secondi) della preview scaricata via yt-dlp prima del
# download completo.
PREVIEW_DURATION_SECONDS = 30

# Estensioni audio riconosciute durante la scansione della libreria.
SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".wav", ".ogg"}

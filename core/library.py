"""
library.py
----------
Si occupa di scansionare la cartella "Music" di default di Windows
(o qualunque cartella scelta dall'utente), leggere i tag di ogni file
audio trovato e sincronizzare il risultato nel database SQLite.
"""

import os
from typing import Callable, Optional

from core import database
from core.config import SUPPORTED_EXTENSIONS, WINDOWS_MUSIC_FOLDER
from core.metadata import read_metadata


def find_audio_files(root_folder: str):
    for dirpath, _dirnames, filenames in os.walk(root_folder):
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                yield os.path.join(dirpath, name)


def scan_library(
    folder: str = WINDOWS_MUSIC_FOLDER,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> int:
    """
    Scansiona `folder` (di default la cartella Music di Windows) e
    aggiorna il database. Salta i file già in cache che non sono stati
    modificati (confronto tramite mtime), per velocizzare le scansioni
    successive su librerie grandi.

    `progress_callback(fatti, totale)` viene chiamato per aggiornare
    una eventuale progress bar nella GUI.

    Ritorna il numero di brani trovati.
    """
    database.init_db()

    if not os.path.isdir(folder):
        return 0

    all_paths = list(find_audio_files(folder))
    total = len(all_paths)

    for i, path in enumerate(all_paths, start=1):
        try:
            mtime = os.path.getmtime(path)
            cached_mtime = database.get_cached_mtime(path)
            if cached_mtime is None or cached_mtime != mtime:
                track = read_metadata(path)
                database.upsert_track(track, mtime)
        except Exception as exc:  # non blocca la scansione per un file corrotto
            print(f"[library] Impossibile leggere {path}: {exc}")

        if progress_callback:
            progress_callback(i, total)

    database.delete_missing(all_paths)
    return total

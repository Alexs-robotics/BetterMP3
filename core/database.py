"""
database.py
-----------
Piccolo layer SQLite che memorizza la libreria musicale già scansionata,
così l'app non deve rileggere tutti i tag ID3 ad ogni avvio (utile con
librerie grandi). Espone funzioni semplici: nessun ORM, query dirette.
"""

import os
import sqlite3
from typing import List, Optional

from core.config import DATABASE_PATH
from core.metadata import TrackMetadata


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tracks (
            path TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            album TEXT NOT NULL,
            track_number INTEGER NOT NULL,
            duration_seconds REAL NOT NULL,
            mtime REAL NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def upsert_track(track: TrackMetadata, mtime: float) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO tracks (path, title, artist, album, track_number, duration_seconds, mtime)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            title=excluded.title,
            artist=excluded.artist,
            album=excluded.album,
            track_number=excluded.track_number,
            duration_seconds=excluded.duration_seconds,
            mtime=excluded.mtime
        """,
        (track.path, track.title, track.artist, track.album,
         track.track_number, track.duration_seconds, mtime),
    )
    conn.commit()
    conn.close()


def update_track_number(path: str, new_number: int) -> None:
    conn = get_connection()
    conn.execute("UPDATE tracks SET track_number = ? WHERE path = ?", (new_number, path))
    conn.commit()
    conn.close()


def get_cached_mtime(path: str) -> Optional[float]:
    conn = get_connection()
    row = conn.execute("SELECT mtime FROM tracks WHERE path = ?", (path,)).fetchone()
    conn.close()
    return row["mtime"] if row else None


def delete_missing(existing_paths: List[str]) -> None:
    """Rimuove dal DB i brani i cui file non esistono più su disco."""
    conn = get_connection()
    if existing_paths:
        placeholders = ",".join("?" for _ in existing_paths)
        conn.execute(f"DELETE FROM tracks WHERE path NOT IN ({placeholders})", existing_paths)
    else:
        conn.execute("DELETE FROM tracks")
    conn.commit()
    conn.close()


def clear_all_tracks() -> None:
    """
    Svuota completamente la cache della libreria (tutte le righe della
    tabella tracks). Utile per forzare una rilettura totale dei tag da
    disco, ad esempio dopo un aggiornamento della logica di lettura dei
    metadati, ignorando il controllo sulla data di modifica dei file.
    """
    conn = get_connection()
    conn.execute("DELETE FROM tracks")
    conn.commit()
    conn.close()


def all_tracks() -> List[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tracks ORDER BY path, track_number, title"
    ).fetchall()
    conn.close()
    return rows


def albums_grouped() -> dict:
    """
    Ritorna un dizionario {cartella: [righe traccia ordinate per track_number]}
    pronto da passare alla GUI per la vista "album interi".

    NOTA: il raggruppamento è fatto in base alla CARTELLA in cui si trova
    il file (os.path.dirname del path), non in base al tag ID3 "album".
    Questo perché il tag album può essere incoerente/mancante tra i file,
    mentre la cartella riflette sempre l'organizzazione reale che l'utente
    ha dato ai suoi file — ed è coerente con la modifica manuale del
    numero di traccia, che deve riordinare i brani realmente presenti
    in quella cartella.

    La chiave del dizionario è il percorso completo della cartella (unico
    per costruzione, a differenza del nome-cartella che potrebbe
    ripetersi in punti diversi del disco).
    """
    rows = all_tracks()
    grouped: dict = {}
    for row in rows:
        folder = os.path.dirname(row["path"])
        grouped.setdefault(folder, []).append(row)
    for folder in grouped:
        grouped[folder].sort(key=lambda r: (r["track_number"], r["title"]))
    return grouped


def folder_display_name(folder_path: str) -> str:
    """Nome leggibile da mostrare in lista per una cartella (solo l'ultimo componente)."""
    return os.path.basename(os.path.normpath(folder_path)) or folder_path

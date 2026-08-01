"""
net_errors.py
-------------
Piccola utility condivisa per riconoscere se un'eccezione di rete (da
`requests`, usata da lastfm_service, o da `yt-dlp`/urllib, usata da
youtube_service) è dovuta all'assenza di connessione a Internet, così
la GUI può mostrare un messaggio breve ("No Internet") invece dello
stack di errore completo.
"""


def is_no_internet_error(exc: Exception) -> bool:
    text = str(exc).lower()
    indicators = (
        "nameresolutionerror",
        "failed to resolve",
        "getaddrinfo failed",
        "max retries exceeded",
        "connectionerror",
        "connection refused",
        "network is unreachable",
        "temporary failure in name resolution",
        "no address associated with hostname",
    )
    return any(indicator in text for indicator in indicators)

# MP3 Player — Desktop Windows

App desktop nativa (non webapp) per Windows, scritta in Python con GUI
Qt (PySide6, tema scuro nero/viola), packagata come `.exe` tramite
PyInstaller.

## Funzionalità

- **Libreria automatica**: legge tutti i brani dalla cartella `Music`
  di default di Windows (o da una cartella a scelta).
- **Raggruppamento per cartella**: i brani vengono organizzati in base
  alla cartella fisica in cui si trovano sul disco (non in base al tag
  ID3 "album", che può essere incoerente/mancante). Ogni cartella viene
  trattata come un "album" nella vista principale.
- **Riproduzione per cartella/album**: seleziona una cartella e
  riproducila per intero, ordinata secondo il numero di traccia.
- **Modifica del numero di traccia**: cambia l'ordine "#" di una
  canzone dentro la sua cartella, scrivendo direttamente il tag ID3
  del file (persistente, resta anche aprendo il file con altri player).
- **Consigli musicali**: per il brano selezionato, l'app suggerisce
  brani simili tramite **Last.fm** (vedi sotto sul perché non
  Spotify), permette di ascoltarne un'**anteprima di 30 secondi** da
  YouTube e, se piace, di **scaricare il brano completo** in
  `downloads/albums/<nome album>/` o `downloads/singles/`. La
  riproduzione della libreria si mette in pausa automaticamente
  quando parte una preview, per evitare sovrapposizioni audio.
- **Controlli di riproduzione avanzati**: play/pausa, brano
  precedente/successivo, velocità regolabile (0.75x–2x), barra di
  avanzamento trascinabile per saltare a un punto preciso del brano,
  controllo volume.
- **Tema scuro nero/viola** applicato a tutta l'interfaccia.

## Perché Last.fm e non Spotify?

Il progetto era pensato per usare l'endpoint "Recommendations" di
Spotify, ma **Spotify lo ha disattivato per tutte le nuove app dal 27
novembre 2024** (insieme ad Audio Features e Related Artists), senza
possibilità di riattivazione. Last.fm offre API equivalenti
(`track.getSimilar`, `artist.getSimilar`), gratuite e tuttora attive.

## Installazione (sviluppo)

1. Installa **Python 3.12** (consigliata: versioni recentissime come
   la 3.14 possono dare problemi di compatibilità con PySide6/PyInstaller).
   Scaricalo da [python.org/downloads](https://www.python.org/downloads/),
   spuntando "Add python.exe to PATH" durante l'installazione. Evita la
   versione dal Microsoft Store: usa percorsi molto lunghi ed è più
   soggetta a errori di installazione dei pacchetti su Windows.
2. Installa [VLC media player](https://www.videolan.org/vlc/) (64 bit,
   deve corrispondere all'architettura di Python — quasi certamente
   64 bit) — serve per le DLL `libvlc` usate dal motore di riproduzione.
3. Installa **ffmpeg** e assicurati che `ffmpeg.exe` sia nel PATH di
   sistema (serve a yt-dlp per convertire/tagliare l'audio):
   ```
   winget install ffmpeg
   ```
   poi riavvia il terminale e verifica con `ffmpeg -version`.
4. Se il tuo sistema Windows non ha i percorsi lunghi abilitati e
   incontri errori di installazione dei pacchetti, esegui in
   PowerShell come amministratore:
   ```powershell
   New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
   ```
   e riavvia il PC.
5. Nella cartella del progetto:
   ```
   pip install -r requirements.txt
   ```
6. Crea un'API key gratuita su https://www.last.fm/api/account/create
   e impostala in `core/config.py` (variabile `LASTFM_API_KEY`) oppure
   come variabile d'ambiente `LASTFM_API_KEY`.
7. Avvia l'app:
   ```
   python main.py
   ```

## Creare l'eseguibile .exe

Esegui `build_exe.bat` (da Prompt dei comandi Windows, dopo aver
completato l'installazione sopra). Lo script include automaticamente
le DLL di VLC nell'eseguibile. Il risultato sarà in `dist\MP3Player.exe`.

Se VLC è installato in un percorso diverso da quello di default,
modifica i percorsi dentro `build_exe.bat` di conseguenza.

**Importante**: se modifichi il codice sorgente (`.py`) mentre stai
testando, non serve rigenerare l'exe — basta rilanciare
`python main.py`. Rigenera l'exe solo quando vuoi il pacchetto finale
da usare o distribuire.

## Struttura del progetto

```
mp3_player/
├── main.py                        # entry point, applica il tema
├── requirements.txt
├── build_exe.bat                  # genera l'eseguibile .exe
├── core/
│   ├── config.py                  # percorsi e chiavi API
│   ├── database.py                # cache SQLite della libreria (raggruppa per cartella)
│   ├── library.py                 # scansione cartella Music
│   ├── metadata.py                # lettura/scrittura tag ID3 (incl. track number)
│   └── player.py                  # motore di riproduzione (python-vlc)
├── services/
│   ├── lastfm_service.py          # brani simili via Last.fm
│   └── youtube_service.py         # ricerca + preview + download via yt-dlp
└── gui/
    ├── theme.py                   # stylesheet Qt nero/viola
    ├── main_window.py             # finestra principale, collega tutto
    ├── album_view.py              # lista cartelle/brani + modifica ordine
    ├── player_controls.py         # play/pausa/skip/velocità/seek
    ├── track_editor_dialog.py     # dialog modifica numero traccia
    └── recommendations_panel.py   # pannello consigli + preview + download
```

## Risoluzione problemi comuni

- **"No module named pyinstaller" nonostante `pip list` lo mostri**:
  di solito è un disallineamento tra più installazioni di Python.
  Verifica con `where python` e `pip show pyinstaller` (campo
  `Location`) che puntino alla stessa cartella; se serve, reinstalla
  con `pip uninstall pyinstaller -y && pip install pyinstaller --no-cache-dir`.
- **`%1 is not a valid Win32 application` all'avvio dell'exe**:
  architettura di VLC diversa da quella di Python (32 vs 64 bit).
  Reinstalla VLC nella versione 64 bit.
- **`ffmpeg is not installed`**: vedi punto 3 sopra.
- **Titoli/numeri traccia ancora sbagliati dopo un aggiornamento**:
  clicca il pulsante "Rilettura completa (ignora cache)" nell'app —
  altrimenti la cache salta i file non modificati su disco e continua
  a mostrare i vecchi valori.

## Nota legale importante

La funzione di download da YouTube va usata solo per contenuti che hai
il diritto di scaricare (materiale royalty-free, tuoi caricamenti,
brani per cui la legge locale lo consente, ecc.). Scaricare musica
protetta da copyright senza autorizzazione può violare i Termini di
Servizio di YouTube e le leggi sul diritto d'autore applicabili nella
tua giurisdizione.

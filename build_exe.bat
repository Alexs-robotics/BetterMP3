@echo off
REM ============================================================
REM build_exe.bat
REM Genera l'eseguibile Windows (.exe) dell'MP3 Player.
REM Esegui questo script da un Prompt dei comandi di Windows,
REM dentro la cartella del progetto, DOPO aver installato le
REM dipendenze con: pip install -r requirements.txt
REM
REM Prerequisiti:
REM   - VLC media player installato (per le DLL di libvlc), oppure
REM     copia manualmente libvlc.dll, libvlccore.dll e la cartella
REM     "plugins" di VLC nella cartella di questo progetto prima
REM     di lanciare lo script.
REM   - ffmpeg.exe raggiungibile nel PATH (richiesto da yt-dlp per
REM     estrarre/convertire l'audio in mp3).
REM ============================================================

REM Rimuove eventuali artefatti di build precedenti (cartelle build/dist e
REM il file .spec generato). Senza questo passaggio, PyInstaller a volte
REM riusa la cache di una build precedente e l'exe risultante non riflette
REM le modifiche più recenti al codice, anche se la build sembra riuscita.
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MP3Player.spec del /q MP3Player.spec

pyinstaller --noconfirm --clean --windowed --onefile ^
    --name "MP3Player" ^
    --add-binary "C:\Program Files\VideoLAN\VLC\libvlc.dll;." ^
    --add-binary "C:\Program Files\VideoLAN\VLC\libvlccore.dll;." ^
    --add-data "C:\Program Files\VideoLAN\VLC\plugins;plugins" ^
    main.py

echo.
echo Eseguibile creato in dist\MP3Player.exe
pause
